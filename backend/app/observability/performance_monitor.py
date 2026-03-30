"""
Performance Monitoring and Metrics Collection
"""
import time
from typing import Dict, Any
from collections import defaultdict, deque
from dataclasses import dataclass
import statistics


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    component: str
    operation: str
    latency_ms: float
    success: bool
    timestamp: float


class PerformanceMonitor:
    """
    Real-time performance monitoring

    Features:
    - Latency tracking (P50, P95, P99)
    - Success rate monitoring
    - Sliding window statistics
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))

    def record(
        self,
        component: str,
        operation: str,
        latency_ms: float,
        success: bool = True
    ):
        """Record a performance metric"""
        key = f"{component}.{operation}"
        self.metrics[key].append(PerformanceMetrics(
            component=component,
            operation=operation,
            latency_ms=latency_ms,
            success=success,
            timestamp=time.time()
        ))

    def get_stats(self, component: str, operation: str) -> Dict[str, Any]:
        """Get statistics for a component.operation"""
        key = f"{component}.{operation}"
        data = list(self.metrics[key])

        if not data:
            return {}

        latencies = [m.latency_ms for m in data]
        successes = [m.success for m in data]

        return {
            "count": len(data),
            "success_rate": sum(successes) / len(successes),
            "latency": {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": self._percentile(latencies, 0.95),
                "p99": self._percentile(latencies, 0.99),
                "max": max(latencies),
                "min": min(latencies)
            }
        }

    def _percentile(self, data: list, p: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get all statistics"""
        stats = {}
        for key in self.metrics.keys():
            component, operation = key.split(".", 1)
            stats[key] = self.get_stats(component, operation)
        return stats


# Global singleton
performance_monitor = PerformanceMonitor()
