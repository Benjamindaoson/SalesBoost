"""Performance metrics collector."""
from __future__ import annotations

import math
import time
from collections import deque
from threading import Lock
from typing import Deque, Dict, List, Optional


class PerformanceMetricsCollector:
    def __init__(self, history_size: int = 1000) -> None:
        self._lock = Lock()
        self._start_time = time.time()
        self._counters: Dict[str, int] = {
            "turns_total": 0,
            "errors_total": 0,
            "audit_blocks_total": 0,
            "refusals_total": 0,
        }
        self._latencies_ms: Deque[float] = deque(maxlen=history_size)

    async def initialize(self) -> None:
        return None

    def record_turn(self, latency_ms: Optional[float] = None) -> None:
        with self._lock:
            self._counters["turns_total"] += 1
            if latency_ms is not None:
                self._latencies_ms.append(latency_ms)

    def record_error(self) -> None:
        with self._lock:
            self._counters["errors_total"] += 1

    def record_audit_block(self) -> None:
        with self._lock:
            self._counters["audit_blocks_total"] += 1
            self._counters["refusals_total"] += 1

    def record_refusal(self) -> None:
        with self._lock:
            self._counters["refusals_total"] += 1

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            turns = self._counters["turns_total"]
            errors = self._counters["errors_total"]
            refusals = self._counters["refusals_total"]
            audit_blocks = self._counters["audit_blocks_total"]
            latencies = list(self._latencies_ms)

        refusal_rate = (refusals / turns) if turns else 0.0
        error_rate = (errors / turns) if turns else 0.0

        return {
            "uptime_seconds": max(0.0, time.time() - self._start_time),
            "turns_total": float(turns),
            "errors_total": float(errors),
            "audit_blocks_total": float(audit_blocks),
            "refusal_rate": refusal_rate,
            "error_rate": error_rate,
            "latency_p50_ms": _percentile(latencies, 0.50),
            "latency_p95_ms": _percentile(latencies, 0.95),
        }

    def render_prometheus(self) -> List[str]:
        metrics = self.snapshot()
        return [
            "# HELP salesboost_turns_total Total turns processed",
            "# TYPE salesboost_turns_total counter",
            f"salesboost_turns_total {int(metrics['turns_total'])}",
            "# HELP salesboost_errors_total Total errors",
            "# TYPE salesboost_errors_total counter",
            f"salesboost_errors_total {int(metrics['errors_total'])}",
            "# HELP salesboost_audit_blocks_total Total audit blocks",
            "# TYPE salesboost_audit_blocks_total counter",
            f"salesboost_audit_blocks_total {int(metrics['audit_blocks_total'])}",
            "# HELP salesboost_refusal_rate Refusal rate",
            "# TYPE salesboost_refusal_rate gauge",
            f"salesboost_refusal_rate {metrics['refusal_rate']}",
            "# HELP salesboost_error_rate Error rate",
            "# TYPE salesboost_error_rate gauge",
            f"salesboost_error_rate {metrics['error_rate']}",
            "# HELP salesboost_latency_p50_ms P50 latency in ms",
            "# TYPE salesboost_latency_p50_ms gauge",
            f"salesboost_latency_p50_ms {metrics['latency_p50_ms']}",
            "# HELP salesboost_latency_p95_ms P95 latency in ms",
            "# TYPE salesboost_latency_p95_ms gauge",
            f"salesboost_latency_p95_ms {metrics['latency_p95_ms']}",
            "# HELP salesboost_uptime_seconds Uptime in seconds",
            "# TYPE salesboost_uptime_seconds gauge",
            f"salesboost_uptime_seconds {metrics['uptime_seconds']}",
        ]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    if pct <= 0:
        return values_sorted[0]
    if pct >= 1:
        return values_sorted[-1]
    idx = max(0, min(len(values_sorted) - 1, int(math.ceil(pct * len(values_sorted))) - 1))
    return values_sorted[idx]


performance_metrics_collector = PerformanceMetricsCollector()
