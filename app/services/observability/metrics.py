"""
Lightweight metrics recorder for LLM calls.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {}
        self._total_cost: float = 0.0
        self._total_calls: int = 0

    def record_llm_call(
        self,
        agent_type: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        key = f"{provider}/{model}/{status}"
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            self._total_calls += 1
            self._total_cost += cost_usd
        logger.info(
            "[METRIC] llm_call agent=%s provider=%s model=%s status=%s latency=%.0fms tokens=%s cost=$%.4f",
            agent_type,
            provider,
            model,
            status,
            latency_ms,
            prompt_tokens + completion_tokens,
            cost_usd,
        )

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return {
                "total_calls": float(self._total_calls),
                "total_cost": float(self._total_cost),
                "by_provider_model": dict(self._counters),
            }


_registry = MetricsRegistry()


def record_llm_call(
    agent_type: str,
    provider: str,
    model: str,
    status: str,
    latency_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    _registry.record_llm_call(
        agent_type=agent_type,
        provider=provider,
        model=model,
        status=status,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )

