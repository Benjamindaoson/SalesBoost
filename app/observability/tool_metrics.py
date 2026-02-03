"""
Tool Execution Metrics Collector
=================================

Provides comprehensive Prometheus metrics for tool execution monitoring.

Metrics:
- tool_calls_total: Counter for total tool executions
- tool_execution_duration_seconds: Histogram for execution latency
- tool_errors_total: Counter for tool errors by type
- tool_cache_hit_rate: Gauge for cache hit rate
- tool_cache_operations_total: Counter for cache operations

Usage:
    from app.observability.tool_metrics import tool_metrics_collector

    tool_metrics_collector.record_execution(
        tool_name="knowledge_retriever",
        status="success",
        latency_ms=245.67,
        caller_role="coach"
    )
"""

import logging
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)


class ToolMetricsCollector:
    """Collects and exposes Prometheus metrics for tool execution"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.

        Args:
            registry: Prometheus registry (defaults to global REGISTRY)
        """
        self.registry = registry or REGISTRY

        # Counter: Total tool calls by tool name, status, and caller role
        self.tool_calls_total = Counter(
            'tool_calls_total',
            'Total tool executions',
            labelnames=['tool_name', 'status', 'caller_role'],
            registry=self.registry
        )

        # Histogram: Tool execution latency distribution
        self.tool_execution_duration = Histogram(
            'tool_execution_duration_seconds',
            'Tool execution latency in seconds',
            labelnames=['tool_name', 'caller_role'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        # Counter: Tool errors by error type
        self.tool_errors_total = Counter(
            'tool_errors_total',
            'Tool execution errors',
            labelnames=['tool_name', 'error_type', 'caller_role'],
            registry=self.registry
        )

        # Gauge: Cache hit rate per tool
        self.tool_cache_hit_rate = Gauge(
            'tool_cache_hit_rate',
            'Tool cache hit rate (0.0-1.0)',
            labelnames=['tool_name'],
            registry=self.registry
        )

        # Counter: Cache operations (hits and misses)
        self.tool_cache_operations = Counter(
            'tool_cache_operations_total',
            'Cache operations (hit/miss)',
            labelnames=['tool_name', 'operation'],
            registry=self.registry
        )

        # Counter: Retry attempts
        self.tool_retry_attempts = Counter(
            'tool_retry_attempts_total',
            'Tool retry attempts',
            labelnames=['tool_name', 'attempt_number'],
            registry=self.registry
        )

        logger.info("ToolMetricsCollector initialized")

    def record_execution(
        self,
        tool_name: str,
        status: str,
        latency_ms: float,
        caller_role: str,
        error_type: Optional[str] = None,
        cached: bool = False
    ):
        """
        Record tool execution metrics.

        Args:
            tool_name: Name of the tool
            status: Execution status (success, error, timeout, etc.)
            latency_ms: Execution latency in milliseconds
            caller_role: Role of the caller (coach, npc, etc.)
            error_type: Type of error if status is error
            cached: Whether result was from cache
        """
        # Record total calls
        self.tool_calls_total.labels(
            tool_name=tool_name,
            status=status,
            caller_role=caller_role
        ).inc()

        # Record latency (convert ms to seconds)
        latency_seconds = latency_ms / 1000.0
        self.tool_execution_duration.labels(
            tool_name=tool_name,
            caller_role=caller_role
        ).observe(latency_seconds)

        # Record errors if applicable
        if error_type:
            self.tool_errors_total.labels(
                tool_name=tool_name,
                error_type=error_type,
                caller_role=caller_role
            ).inc()

        # Record cache operation
        if cached:
            self.record_cache_operation(tool_name, "hit")
        else:
            self.record_cache_operation(tool_name, "miss")

        logger.debug(
            f"Recorded metrics: tool={tool_name}, status={status}, "
            f"latency={latency_ms}ms, cached={cached}"
        )

    def record_cache_operation(self, tool_name: str, operation: str):
        """
        Record cache operation (hit or miss).

        Args:
            tool_name: Name of the tool
            operation: Operation type ("hit" or "miss")
        """
        self.tool_cache_operations.labels(
            tool_name=tool_name,
            operation=operation
        ).inc()

    def update_cache_hit_rate(self, tool_name: str, hit_rate: float):
        """
        Update cache hit rate gauge.

        Args:
            tool_name: Name of the tool
            hit_rate: Hit rate as a float between 0.0 and 1.0
        """
        self.tool_cache_hit_rate.labels(tool_name=tool_name).set(hit_rate)

    def record_retry_attempt(self, tool_name: str, attempt_number: int):
        """
        Record a retry attempt.

        Args:
            tool_name: Name of the tool
            attempt_number: Retry attempt number (1, 2, 3, etc.)
        """
        self.tool_retry_attempts.labels(
            tool_name=tool_name,
            attempt_number=str(attempt_number)
        ).inc()

    def get_stats(self) -> dict:
        """
        Get current metrics statistics.

        Returns:
            Dictionary with current metric values
        """
        return {
            "metrics_enabled": True,
            "registry": "prometheus_client.REGISTRY"
        }


# Global singleton instance
tool_metrics_collector = ToolMetricsCollector()


# Convenience functions for direct usage
def record_tool_execution(
    tool_name: str,
    status: str,
    latency_ms: float,
    caller_role: str,
    error_type: Optional[str] = None,
    cached: bool = False
):
    """Convenience function to record tool execution"""
    tool_metrics_collector.record_execution(
        tool_name=tool_name,
        status=status,
        latency_ms=latency_ms,
        caller_role=caller_role,
        error_type=error_type,
        cached=cached
    )


def record_cache_operation(tool_name: str, operation: str):
    """Convenience function to record cache operation"""
    tool_metrics_collector.record_cache_operation(tool_name, operation)


def update_cache_hit_rate(tool_name: str, hit_rate: float):
    """Convenience function to update cache hit rate"""
    tool_metrics_collector.update_cache_hit_rate(tool_name, hit_rate)


def record_retry_attempt(tool_name: str, attempt_number: int):
    """Convenience function to record retry attempt"""
    tool_metrics_collector.record_retry_attempt(tool_name, attempt_number)
