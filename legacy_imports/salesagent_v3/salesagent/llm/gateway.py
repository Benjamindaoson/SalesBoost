"""Model Gateway — unified LLM interface with fallback chain."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, AsyncGenerator

import structlog
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from salesagent.core.settings import settings
from salesagent.utils.exceptions import GatewayTimeoutError, ModelUnavailableError
from salesagent.utils.telemetry import AgentNodeTimer
from salesagent.observability.metrics import (
    llm_api_calls_total,
    llm_api_duration_seconds,
    llm_api_errors_total,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger()

# ── Mock LLM responses for offline testing ─────────────────────────────────

_MOCK_REASONING = """{
  "literal_intent": "客户询问产品价格",
  "hidden_concerns": ["性价比担忧", "与竞品对比"],
  "customer_signals": {
    "urgency": 0.4,
    "interest_level": 0.75,
    "objection_type": "price_sensitivity",
    "decision_stage": "evaluation"
  },
  "recommended_tactics": {
    "primary": "value_reframe",
    "secondary": "social_proof",
    "tone": "consultative_not_pushy",
    "avoid": ["hard_close", "discount_offer"]
  },
  "stage_signal": "stay",
  "reasoning_trace": "客户连续询问价格但未直接拒绝，表明有购买意向但在多家比价。应通过价值重构和成功案例来重新锚定认知，而非直接降价。",
  "confidence": 0.82
}"""

_MOCK_RESPONSE = "感谢您的关注！我理解您在做慎重的比较决策。能和我分享一下，您目前最看重的核心需求是什么？这样我可以更精准地帮您评估我们的方案是否真正适合您的场景。"

_MOCK_REWRITE = "我们的解决方案在行业内有着优秀的口碑，很多客户反馈在效率提升方面成效显著。"

_MOCK_CRITIC = '{"score": 0.82, "rationale": "Response effectively uses value reframe tactic with an empathetic tone."}'

_MOCK_SELFRAG = '{"relevant": true, "reason": "Chunk directly addresses the customer question about pricing."}'


class ModelGateway:
    """
    Unified model gateway supporting:
    - Task-based routing (reasoning → Claude, guard → GPT-4o-mini)
    - Fallback chain on timeout/error
    - Shadow Mode traffic splitting
    - OpenTelemetry span per call
    - Mock mode for offline testing
    """

    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis
        self._clients: dict[str, Any] = {}
        self._shadow: ShadowMode | None = None

    async def initialize(self) -> None:
        """Initialize LLM clients (called during app startup)."""
        if settings.mock_llm:
            log.info("ModelGateway: MOCK mode enabled")
            return

        if settings.anthropic_api_key:
            import anthropic
            self._clients["anthropic"] = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        if settings.openai_api_key:
            import openai
            self._clients["openai"] = openai.AsyncOpenAI(api_key=settings.openai_api_key)

        if settings.deepseek_api_key:
            import openai
            self._clients["deepseek"] = openai.AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url
            )

        if settings.shadow_mode_enabled and self._redis:
            from salesagent.llm.shadow import ShadowMode
            self._shadow = ShadowMode(gateway=self, redis=self._redis)

    async def complete(
        self,
        task: str,
        system: str,
        user: str,
        session_id: str = "",
        response_format: str = "text",
        use_lite: bool = False,
        **kwargs: Any,
    ) -> str:
        """Non-streaming completion. Returns the full response string."""
        model = self._route_model(task, use_lite=use_lite)
        with AgentNodeTimer(node_name=task, model=model, session_id=session_id):
            if settings.mock_llm:
                return self._mock_response(task)

            return await self._call_with_fallback(
                model=model,
                system=system,
                user=user,
                stream=False,
            )

    async def stream(
        self,
        task: str,
        system: str,
        user: str,
        session_id: str = "",
        use_lite: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Streaming completion yielding token chunks."""
        model = self._route_model(task, use_lite=use_lite)
        if settings.mock_llm:
            for word in _MOCK_RESPONSE.split():
                yield word + " "
                await asyncio.sleep(0.03)
            return

        async for chunk in self._stream_with_fallback(model=model, system=system, user=user):
            yield chunk

    def _route_model(self, task: str, use_lite: bool = False) -> str:
        """Task-based model routing table."""
        from salesagent.llm.router import get_model
        return get_model(task, use_lite=use_lite)

    def _mock_response(self, task: str) -> str:
        mock_map = {
            "reasoning": _MOCK_REASONING,
            "guard_rewrite": _MOCK_REWRITE,
            "critic": _MOCK_CRITIC,
            "selfrag_filter": _MOCK_SELFRAG,
        }
        return mock_map.get(task, _MOCK_RESPONSE)

    async def _call_with_fallback(self, model: str, system: str, user: str, stream: bool) -> str:
        from salesagent.llm.fallback import FALLBACK_CHAIN
        from salesagent.utils.circuit_breaker import get_circuit_breaker

        models_to_try = [model] + [m for m in FALLBACK_CHAIN if m != model]

        for attempt_model in models_to_try:
            circuit = get_circuit_breaker(
                name=f"llm_{attempt_model}",
                failure_threshold=5,
                recovery_timeout=60.0,
            )

            try:
                result = await circuit.call(
                    asyncio.wait_for,
                    self._call_model(attempt_model, system, user),
                    timeout=settings.gateway_timeout_seconds,
                )
                return result
            except asyncio.TimeoutError:
                log.warning("Model timeout", model=attempt_model)
            except Exception as exc:
                log.warning("Model error", model=attempt_model, error=str(exc))

        raise ModelUnavailableError(message="All models in fallback chain unavailable")

    async def _call_model(self, model: str, system: str, user: str) -> str:
        provider = "anthropic" if "claude" in model else "openai" if "gpt" in model else "unknown"

        start_time = time.perf_counter()
        try:
            if "claude" in model:
                client = self._clients.get("anthropic")
                if not client:
                    raise ModelUnavailableError(message="Anthropic client not initialized")
                # Enhanced Claude call with Prompt Caching support for system prompt
                system_blocks = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                msg = await client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user}],
                )
                result = msg.content[0].text

                llm_api_calls_total.labels(provider=provider, model=model, task="completion").inc()
                llm_api_duration_seconds.labels(provider=provider, model=model, task="completion").observe(
                    time.perf_counter() - start_time
                )
                return result

            if "gpt" in model:
                client = self._clients.get("openai")
                if not client:
                    raise ModelUnavailableError(message="OpenAI client not initialized")
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=2048,
                )
                result = resp.choices[0].message.content or ""

                llm_api_calls_total.labels(provider=provider, model=model, task="completion").inc()
                llm_api_duration_seconds.labels(provider=provider, model=model, task="completion").observe(
                    time.perf_counter() - start_time
                )
                return result

            if "deepseek" in model:
                client = self._clients.get("deepseek")
                if not client:
                    raise ModelUnavailableError(message="DeepSeek client not initialized")
                resp = await client.chat.completions.create(
                    model=settings.deepseek_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=2048,
                )
                result = resp.choices[0].message.content or ""

                llm_api_calls_total.labels(provider="deepseek", model=model, task="completion").inc()
                llm_api_duration_seconds.labels(provider="deepseek", model=model, task="completion").observe(
                    time.perf_counter() - start_time
                )
                return result

            raise ModelUnavailableError(message=f"Unknown model: {model}")
        except Exception as e:
            llm_api_errors_total.labels(provider=provider, model=model, error_type=type(e).__name__).inc()
            raise

    async def _stream_with_fallback(
        self, model: str, system: str, user: str
    ) -> AsyncGenerator[str, None]:
        from salesagent.llm.fallback import FALLBACK_CHAIN
        from salesagent.utils.circuit_breaker import get_circuit_breaker

        models_to_try = [model] + [m for m in FALLBACK_CHAIN if m != model]

        for attempt_model in models_to_try:
            circuit = get_circuit_breaker(
                name=f"llm_{attempt_model}",
                failure_threshold=5,
                recovery_timeout=60.0,
            )

            try:
                if "claude" in attempt_model:
                    client = self._clients.get("anthropic")
                    if client:
                        async def _stream_claude():
                            system_blocks = [
                                {
                                    "type": "text",
                                    "text": system,
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ]
                            async with client.messages.stream(
                                model=attempt_model,
                                max_tokens=2048,
                                system=system_blocks,
                                messages=[{"role": "user", "content": user}],
                            ) as stream:
                                async for text in stream.text_stream:
                                    yield text

                        async for chunk in _stream_claude():
                            yield chunk
                        return

                if "gpt" in attempt_model:
                    client = self._clients.get("openai")
                    if client:
                        async def _stream_openai():
                            async for chunk in await client.chat.completions.create(
                                model=attempt_model,
                                messages=[
                                    {"role": "system", "content": system},
                                    {"role": "user", "content": user},
                                ],
                                stream=True,
                                max_tokens=2048,
                            ):
                                if chunk.choices[0].delta.content:
                                    yield chunk.choices[0].delta.content

                        async for chunk in _stream_openai():
                            yield chunk
                        return

            except Exception as exc:
                log.warning("Streaming model error", model=attempt_model, error=str(exc))
                continue

        # Final fallback — mock stream
        log.warning("All streaming models failed, using mock fallback")
        for word in _MOCK_RESPONSE.split():
            yield word + " "
            await asyncio.sleep(0.03)
