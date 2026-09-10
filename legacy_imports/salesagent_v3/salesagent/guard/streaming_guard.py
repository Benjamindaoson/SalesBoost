"""Streaming Guard — sentence-level compliance interceptor."""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, AsyncGenerator

import structlog

from salesagent.core.constants import REDIS_STREAM_GUARD_EVENTS, GuardRiskType
from salesagent.guard.rules import check_sentence
from salesagent.observability.metrics import guard_checks_total, guard_rewrites_total

log = structlog.get_logger()

# Sentence boundary pattern (CN + EN punctuation)
_SENTENCE_END = re.compile(r"[。！？!?\n]")


class StreamingGuard:
    """
    Wraps the response token stream and intercepts at sentence boundaries.
    On violation:
    1. Truncates the violating sentence
    2. Calls lightweight rewriter to produce a safe replacement
    3. Seamlessly splices it into the stream
    4. Logs guard event to Redis Streams

    The user perceives no discontinuity.
    """

    def __init__(self, gateway: Any, redis: Any | None = None) -> None:
        self.gateway = gateway
        self.redis = redis

    async def wrap_stream(
        self,
        token_stream: AsyncGenerator[str, None],
        session_id: str,
        turn_index: int,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Wrap a raw token stream and yield guard-processed events.
        Event types: {"type": "token", "data": "<chunk>"}
                     {"type": "guard_event", "data": {...}}
        """
        buffer = ""

        async for token in token_stream:
            buffer += token

            # Check for sentence boundary in buffered content
            while _SENTENCE_END.search(buffer):
                match = _SENTENCE_END.search(buffer)
                sentence = buffer[: match.end()]
                buffer = buffer[match.end():]

                # ── Semantic Alignment Check (Sales Values) ─────────────────
                from salesagent.guard.rules import get_semantic_violation
                violation_data = await get_semantic_violation(sentence, self.gateway)

                if violation_data.get("violation_type"):
                    v_type = violation_data["violation_type"]
                    severity = violation_data.get("severity", 0.5)

                    # Track metrics
                    guard_checks_total.labels(risk_type=str(v_type), severity=f"{severity:.1f}").inc()
                    guard_rewrites_total.inc()

                    # Truncate and rewrite
                    rewritten = await self._rewrite(sentence, v_type, session_id, severity)
                    guard_event = {
                        "session_id": session_id,
                        "turn_index": turn_index,
                        "risk_type": str(v_type),
                        "severity": severity,
                        "explanation": violation_data.get("explanation"),
                        "original": sentence,
                        "rewritten": rewritten,
                        "timestamp": time.time(),
                    }
                    await self._log_guard_event(guard_event)
                    yield {"type": "guard_event", "data": guard_event}
                    yield {"type": "token", "data": rewritten}
                else:
                    guard_checks_total.labels(risk_type="none", severity="0.0").inc()
                    yield {"type": "token", "data": sentence}

        # Flush remaining buffer
        if buffer.strip():
            from salesagent.guard.rules import get_risk_severity
            violation, severity = get_risk_severity(buffer)
            if violation:
                rewritten = await self._rewrite(buffer, violation, session_id, severity)
                yield {"type": "guard_event", "data": {"risk_type": violation.value, "severity": severity}}
                yield {"type": "token", "data": rewritten}
            else:
                yield {"type": "token", "data": buffer}

    async def _rewrite(
        self, sentence: str, risk_type: GuardRiskType, session_id: str, severity: float = 0.5
    ) -> str:
        from salesagent.guard.rewriter import GuardRewriter
        rewriter = GuardRewriter(gateway=self.gateway)
        return await rewriter.rewrite(sentence, risk_type, session_id, severity)

    async def _log_guard_event(self, event: dict[str, Any]) -> None:
        if self.redis:
            try:
                import json
                await self.redis.xadd(
                    REDIS_STREAM_GUARD_EVENTS,
                    {"event": json.dumps(event)},
                    maxlen=10_000,
                    approximate=True,
                )
            except Exception as exc:
                log.warning("Failed to log guard event to Redis", error=str(exc))
