"""Sales Reasoning Chain — core reasoning logic."""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import structlog

from salesagent.core.constants import SaleStage
from salesagent.reasoning.schemas import CONSERVATIVE_REASONING, ReasoningOutput
from salesagent.utils.exceptions import ReasoningSchemaError

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from salesagent.llm.gateway import ModelGateway

log = structlog.get_logger()

_CACHE_PREFIX = "reasoning_cache:"


class SalesReasoningChain:
    """
    The central differentiator: before generating any response, run deep
    strategic analysis. Output is a structured JSON (ReasoningOutput) that
    guides all downstream nodes.

    Hot-path cache: if a semantically similar query was recently reasoned about
    (embedding similarity > threshold), return cached result instantly.
    """

    def __init__(self, gateway: ModelGateway, redis: Redis | None = None) -> None:
        self.gateway = gateway
        self.redis = redis

    async def run(
        self,
        messages: list[dict[str, str]],
        fsm_stage: SaleStage,
        customer_profile: dict[str, Any] | None = None,
        session_id: str = "",
        use_lite: bool = False,
    ) -> ReasoningOutput:
        """
        Run the reasoning chain.

        1. Check embedding cache (if Redis available)
        2. Build prompt from current conversation + stage context
        3. Call LLM (reasoning model)
        4. Validate output against ReasoningOutput schema
        5. On parse failure → return CONSERVATIVE_REASONING
        6. Cache result
        """
        from salesagent.core.settings import settings

        user_message = messages[-1]["content"] if messages else ""

        # ── Cache lookup ────────────────────────────────────────────────────
        cache_key = await self._get_cache_key(user_message, fsm_stage)
        if self.redis and settings.reasoning_cache_enabled:
            cached = await self._load_from_cache(cache_key)
            if cached:
                log.debug("Reasoning cache hit", session_id=session_id)
                return cached

        # ── Build prompt ─────────────────────────────────────────────────────
        from salesagent.reasoning.prompts import REASONING_SYSTEM_PROMPT, REASONING_USER_TEMPLATE

        conversation_history = "\n".join(
            f"[{m['role'].upper()}]: {m['content']}"
            for m in messages[:-1][-10:]  # last 10 turns for context window
        )

        system_prompt = REASONING_SYSTEM_PROMPT.format(
            fsm_stage=fsm_stage.value,
            customer_profile=json.dumps(customer_profile or {}, ensure_ascii=False),
        )
        user_prompt = REASONING_USER_TEMPLATE.format(
            conversation_history=conversation_history,
            user_message=user_message,
        )

        # ── LLM call ─────────────────────────────────────────────────────────
        raw_output = await self.gateway.complete(
            task="reasoning",
            system=system_prompt,
            user=user_prompt,
            session_id=session_id,
            response_format="json",
            use_lite=use_lite,
        )

        # ── Parse & validate ─────────────────────────────────────────────────
        reasoning_output = await self._parse_output(raw_output, session_id)

        # ── Cache result ─────────────────────────────────────────────────────
        if self.redis and settings.reasoning_cache_enabled:
            await self._save_to_cache(cache_key, reasoning_output, settings.reasoning_cache_ttl_seconds)

        return reasoning_output

    async def _parse_output(self, raw: str, session_id: str) -> ReasoningOutput:
        try:
            # Strip markdown code fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(raw)
            return ReasoningOutput(**data)
        except Exception as exc:
            log.warning(
                "Reasoning schema validation failed — using conservative fallback",
                session_id=session_id,
                error=str(exc),
            )
            return CONSERVATIVE_REASONING

    async def _get_cache_key(self, message: str, stage: SaleStage) -> str:
        """Simple hash-based cache key (embedding-based would be production approach)."""
        content = f"{stage.value}:{message}"
        return _CACHE_PREFIX + hashlib.sha256(content.encode()).hexdigest()

    async def _load_from_cache(self, key: str) -> ReasoningOutput | None:
        try:
            raw = await self.redis.get(key)
            if raw:
                return ReasoningOutput.model_validate_json(raw)
        except Exception:
            pass
        return None

    async def _save_to_cache(self, key: str, output: ReasoningOutput, ttl: int) -> None:
        try:
            await self.redis.setex(key, ttl, output.model_dump_json())
        except Exception:
            pass
