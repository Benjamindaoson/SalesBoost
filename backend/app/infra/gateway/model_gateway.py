import time
import logging
import json
import random
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from ...infra.gateway.schemas import ModelCall, RoutingContext, ModelConfig
from ...infra.llm.router import router
from ...infra.llm.adapters import AdapterFactory
from ...infra.llm.registry import model_registry
from ...infra.llm.fast_intent import fast_intent_classifier
from ...infra.llm.shadow import record_shadow_result
from ...infra.streaming.utf8_buffer import StreamingErrorRecovery
from ...infra.guardrails.streaming_guard import streaming_guard
from ...core.config import get_settings

logger = logging.getLogger(__name__)


def _make_limiter(max_calls: int):
    """Create concurrency limiter: Redis when enabled, else asyncio.Semaphore."""
    try:
        settings = get_settings()
        if getattr(settings, "LLM_USE_REDIS_SEMAPHORE", False):
            from .redis_semaphore import ConcurrencyLimiter
            return ConcurrencyLimiter(limit=max_calls, use_redis=True)
    except Exception as e:
        logger.debug("Redis limiter disabled: %s", e)
    return _LocalLimiter(max_calls)


class _LocalLimiter:
    """Fallback: asyncio.Semaphore for single-process."""

    def __init__(self, limit: int):
        self._sem = asyncio.Semaphore(limit)

    @asynccontextmanager
    async def acquire(self):
        async with self._sem:
            yield


class ModelGateway:
    """
    Unified Gateway for LLM Calls.
    Handles routing, retries, and cost tracking using SmartRouter and Adapters.
    Uses Redis distributed semaphore when LLM_USE_REDIS_SEMAPHORE=true for horizontal scaling.
    """
    
    def __init__(self, budget_manager=None, max_concurrent_calls: int = 10):
        self.budget_manager = budget_manager
        self._limiter = _make_limiter(max_concurrent_calls)
        self.shadow_semaphore = asyncio.Semaphore(max(1, max_concurrent_calls // 2))

    async def call(self, call: ModelCall, context: RoutingContext) -> str:
        """
        Execute an LLM call with routing and safety.
        """
        async with self._limiter.acquire():
            # 1. Use Router to select the best model
            selected_config = call.config
            if not selected_config:
                selected_config = router.select_model(context, prompt=call.prompt)

            intent_result = fast_intent_classifier.classify(call.prompt)
            intent_category = intent_result.category.value
                
            # Shadow Mode Check (Async Mirroring)
            shadow_config = router.select_shadow_model(context, selected_config)
            if shadow_config:
                logger.info(f"👻 Shadow Mode Triggered: Mirroring to {shadow_config.provider}/{shadow_config.model_name}")
                asyncio.create_task(self._call_shadow(call, shadow_config, selected_config))
            
            adapter = AdapterFactory.get_adapter(selected_config.provider)
            if not adapter:
                logger.error(f"No adapter found for provider {selected_config.provider}. Fallback to mock.")
                return await self._call_mock(call, context)

            logger.info(f"Routing to {selected_config.provider}/{selected_config.model_name}")
            start_time = time.time()

            try:
                # Prepare messages
                messages = []
                system_prompt = call.system_prompt
                tools_schema = call.tools
                tool_mode = (call.tool_mode or "").lower()
                if tools_schema and tool_mode in {"", "prompt", "auto"}:
                    system_prompt = self._inject_tools_prompt(system_prompt, tools_schema)
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": call.prompt})

                # Execute Call
                content = await adapter.chat(
                    messages,
                    selected_config,
                    tools=tools_schema if tools_schema and tool_mode in {"function_calling", "auto"} else None,
                    tool_choice=call.tool_choice,
                )
                
                # Update Metrics
                latency_ms = (time.time() - start_time) * 1000
                await model_registry.update_metrics(
                    selected_config.provider,
                    selected_config.model_name,
                    latency_ms,
                    True,
                    intent_category=intent_category,
                )
                
                # Track Cost (tiktoken when available, else len/4 fallback)
                if self.budget_manager:
                    est_tokens = self._count_tokens(
                        prompt=call.prompt or "",
                        content=content,
                        model=selected_config.model_name,
                        system_prompt=system_prompt,
                    )
                    meta = model_registry.get_model(selected_config.provider, selected_config.model_name)
                    cost = 0.0
                    if meta:
                        cost = (est_tokens / 1000.0) * getattr(meta, "output_cost_per_1k", 0.0)
                    await self.budget_manager.track_cost(context.session_id, cost)

                return content

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                await model_registry.update_metrics(
                    selected_config.provider,
                    selected_config.model_name,
                    latency_ms,
                    False,
                    intent_category=intent_category,
                )
                
                logger.error(f"Model call failed: {e}. Fallback to Mock.")
                return await self._call_mock(call, context)

    async def _call_shadow(self, call: ModelCall, config: ModelConfig, primary: ModelConfig):
        """
        Execute a shadow call for testing/comparison.
        Swallows exceptions to avoid affecting main flow.
        """
        try:
            async with self.shadow_semaphore:
                adapter = AdapterFactory.get_adapter(config.provider)
                if not adapter:
                    return

                messages = []
                if call.system_prompt:
                    messages.append({"role": "system", "content": call.system_prompt})
                messages.append({"role": "user", "content": call.prompt})

                start_time = time.time()
                content = await asyncio.wait_for(adapter.chat(messages, config), timeout=10.0)
                latency = (time.time() - start_time) * 1000
                logger.info(f"[Shadow] Call Completed: {config.provider}/{config.model_name} | Latency: {latency:.2f}ms")

                await record_shadow_result(
                    config.provider,
                    config.model_name,
                    {
                        "primary": f"{primary.provider}/{primary.model_name}",
                        "latency_ms": round(latency, 2),
                        "output_len": len(content),
                        "prompt_len": len(call.prompt or ""),
                    },
                )
        except Exception as e:
            logger.warning(f"[Shadow] Call Failed: {e}")

    async def stream_call(self, call: ModelCall, context: RoutingContext) -> AsyncGenerator[str, None]:
        """
        Execute a streaming LLM call with concurrency control.
        """
        async with self._limiter.acquire():
            error_recovery = StreamingErrorRecovery(max_retries=3, base_delay=1.0)
            
            # Route
            selected_config = call.config or router.select_model(context, prompt=call.prompt)
            adapter = AdapterFactory.get_adapter(selected_config.provider)
            
            if not adapter:
                 async for chunk in self._stream_mock(call, context):
                    yield chunk
                 return

            logger.info(f"Streaming via {selected_config.provider}/{selected_config.model_name}")

            while True:
                try:
                    messages = []
                    system_prompt = call.system_prompt
                    tools_schema = call.tools
                    tool_mode = (call.tool_mode or "").lower()
                    if tools_schema and tool_mode in {"", "prompt", "auto"}:
                        system_prompt = self._inject_tools_prompt(system_prompt, tools_schema)
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": call.prompt})

                    async def audited_stream():
                        async for chunk in adapter.stream(
                            messages,
                            selected_config,
                            tools=tools_schema if tools_schema and tool_mode in {"function_calling", "auto"} else None,
                            tool_choice=call.tool_choice,
                        ):
                            yield chunk

                    async for chunk in streaming_guard.audit_stream(audited_stream()):
                        yield chunk
                    return

                except Exception as e:
                    logger.error(f"Streaming failed: {e}")
                    if error_recovery.should_retry(e):
                        delay = error_recovery.get_retry_delay()
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.warning("Max retries reached. Fallback to mock.")
                        break
            
            # Fallback
            async for chunk in self._stream_mock(call, context):
                yield chunk

    async def _call_mock(self, call: ModelCall, context: RoutingContext) -> str:
        if self.budget_manager:
            await self.budget_manager.track_cost(context.session_id, 0.001)
        
        if context.agent_type == "npc":
            responses = [
                 "That sounds interesting, but I'm worried about the cost.",
                 "Can you explain how this integrates with our existing systems?",
                 "I need to talk to my manager about this.",
                 "That's exactly what we strictly need right now."
            ]
            return json.dumps({
                "content": random.choice(responses),
                "mood": random.uniform(0.3, 0.9),
                "next_stage_hint": "Handle objection"
            })
            
        return "This is a mock response from ModelGateway."

    async def _stream_mock(self, call: ModelCall, context: RoutingContext) -> AsyncGenerator[str, None]:
        response = await self._call_mock(call, context)
        # Simulate typing
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.05)

    def _count_tokens(
        self,
        prompt: str,
        content: str,
        model: str,
        system_prompt: Optional[str] = None,
    ) -> int:
        """Count tokens using tiktoken when available, else len/4 fallback."""
        try:
            import tiktoken
            full_text = (system_prompt or "") + "\n" + (prompt or "") + (content or "")
            try:
                encoding = tiktoken.encoding_for_model(
                    "gpt-4" if "gpt" in (model or "").lower() else "gpt-3.5-turbo"
                )
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(full_text))
        except Exception:
            return int(len((prompt or "") + (content or "")) / 4)

    def _inject_tools_prompt(self, system_prompt: Optional[str], tools_schema: list) -> str:
        tools_json = json.dumps(tools_schema, ensure_ascii=True)
        instruction = (
            "Available tools (JSON Schema):\n"
            f"{tools_json}\n"
            "If you need to call a tool, respond with:\n"
            "Action: tool_name\n"
            "Action Input: {\"arg\": \"value\"}\n"
        )
        if system_prompt:
            return f"{system_prompt}\n\n{instruction}"
        return instruction
