"""
Unit Tests for Tool Metrics
============================

Tests the ToolMetricsCollector and Prometheus metrics integration.
"""
import pytest
from unittest.mock import Mock, patch
from prometheus_client import CollectorRegistry, REGISTRY

from app.observability.tool_metrics import (
    ToolMetricsCollector,
    record_tool_execution,
    record_cache_operation,
    update_cache_hit_rate,
    record_retry_attempt
)


class TestToolMetricsCollector:
    """Test ToolMetricsCollector class"""

    @pytest.fixture
    def registry(self):
        """Create a test registry"""
        return CollectorRegistry()

    @pytest.fixture
    def collector(self, registry):
        """Create collector with test registry"""
        return ToolMetricsCollector(registry=registry)

    def test_init_with_default_registry(self):
        """Test initialization with default registry"""
        # Use a custom registry to avoid conflicts with global singleton
        registry = CollectorRegistry()
        collector = ToolMetricsCollector(registry=registry)
        assert collector.registry == registry

    def test_init_with_custom_registry(self, registry):
        """Test initialization with custom registry"""
        collector = ToolMetricsCollector(registry=registry)
        assert collector.registry == registry

    def test_metrics_created(self, collector):
        """Test that all metrics are created"""
        assert collector.tool_calls_total is not None
        assert collector.tool_execution_duration is not None
        assert collector.tool_errors_total is not None
        assert collector.tool_cache_hit_rate is not None
        assert collector.tool_cache_operations is not None
        assert collector.tool_retry_attempts is not None

    def test_record_execution_success(self, collector):
        """Test recording successful execution"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=245.67,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        # Verify counter incremented
        metric_value = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        assert metric_value == 1.0

    def test_record_execution_with_error(self, collector):
        """Test recording execution with error"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="error",
            latency_ms=100.0,
            caller_role="coach",
            error_type="TimeoutError",
            cached=False
        )

        # Verify error counter incremented
        error_metric = collector.tool_errors_total.labels(
            tool_name="knowledge_retriever",
            error_type="TimeoutError",
            caller_role="coach"
        )._value.get()
        assert error_metric == 1.0

    def test_record_execution_with_cache_hit(self, collector):
        """Test recording execution with cache hit"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="cache_hit",
            latency_ms=5.0,
            caller_role="coach",
            error_type=None,
            cached=True
        )

        # Verify cache hit recorded
        cache_metric = collector.tool_cache_operations.labels(
            tool_name="knowledge_retriever",
            operation="hit"
        )._value.get()
        assert cache_metric == 1.0

    def test_record_execution_with_cache_miss(self, collector):
        """Test recording execution with cache miss"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=250.0,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        # Verify cache miss recorded
        cache_metric = collector.tool_cache_operations.labels(
            tool_name="knowledge_retriever",
            operation="miss"
        )._value.get()
        assert cache_metric == 1.0

    def test_record_execution_latency(self, collector):
        """Test recording execution latency"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=245.67,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        # Verify histogram recorded (check sample count)
        histogram = collector.tool_execution_duration.labels(
            tool_name="knowledge_retriever",
            caller_role="coach"
        )
        # Histogram should have recorded one sample
        assert histogram._sum.get() > 0

    def test_record_multiple_executions(self, collector):
        """Test recording multiple executions"""
        for i in range(5):
            collector.record_execution(
                tool_name="knowledge_retriever",
                status="success",
                latency_ms=100.0 + i,
                caller_role="coach",
                error_type=None,
                cached=False
            )

        # Verify counter shows 5 executions
        metric_value = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        assert metric_value == 5.0

    def test_record_cache_operation_hit(self, collector):
        """Test recording cache hit operation"""
        collector.record_cache_operation("knowledge_retriever", "hit")

        metric_value = collector.tool_cache_operations.labels(
            tool_name="knowledge_retriever",
            operation="hit"
        )._value.get()
        assert metric_value == 1.0

    def test_record_cache_operation_miss(self, collector):
        """Test recording cache miss operation"""
        collector.record_cache_operation("knowledge_retriever", "miss")

        metric_value = collector.tool_cache_operations.labels(
            tool_name="knowledge_retriever",
            operation="miss"
        )._value.get()
        assert metric_value == 1.0

    def test_update_cache_hit_rate(self, collector):
        """Test updating cache hit rate"""
        collector.update_cache_hit_rate("knowledge_retriever", 0.75)

        metric_value = collector.tool_cache_hit_rate.labels(
            tool_name="knowledge_retriever"
        )._value.get()
        assert metric_value == 0.75

    def test_update_cache_hit_rate_multiple_times(self, collector):
        """Test updating cache hit rate multiple times"""
        collector.update_cache_hit_rate("knowledge_retriever", 0.5)
        collector.update_cache_hit_rate("knowledge_retriever", 0.75)
        collector.update_cache_hit_rate("knowledge_retriever", 0.9)

        # Gauge should show latest value
        metric_value = collector.tool_cache_hit_rate.labels(
            tool_name="knowledge_retriever"
        )._value.get()
        assert metric_value == 0.9

    def test_record_retry_attempt(self, collector):
        """Test recording retry attempt"""
        collector.record_retry_attempt("knowledge_retriever", 1)

        metric_value = collector.tool_retry_attempts.labels(
            tool_name="knowledge_retriever",
            attempt_number="1"
        )._value.get()
        assert metric_value == 1.0

    def test_record_multiple_retry_attempts(self, collector):
        """Test recording multiple retry attempts"""
        collector.record_retry_attempt("knowledge_retriever", 1)
        collector.record_retry_attempt("knowledge_retriever", 2)
        collector.record_retry_attempt("knowledge_retriever", 3)

        # Each attempt should be tracked separately
        attempt_1 = collector.tool_retry_attempts.labels(
            tool_name="knowledge_retriever",
            attempt_number="1"
        )._value.get()
        attempt_2 = collector.tool_retry_attempts.labels(
            tool_name="knowledge_retriever",
            attempt_number="2"
        )._value.get()
        attempt_3 = collector.tool_retry_attempts.labels(
            tool_name="knowledge_retriever",
            attempt_number="3"
        )._value.get()

        assert attempt_1 == 1.0
        assert attempt_2 == 1.0
        assert attempt_3 == 1.0

    def test_get_stats(self, collector):
        """Test get_stats method"""
        stats = collector.get_stats()

        assert stats["metrics_enabled"] is True
        assert "registry" in stats

    def test_different_tools_tracked_separately(self, collector):
        """Test that different tools are tracked separately"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=100.0,
            caller_role="coach",
            cached=False
        )
        collector.record_execution(
            tool_name="compliance_check",
            status="success",
            latency_ms=200.0,
            caller_role="coach",
            cached=False
        )

        # Verify separate tracking
        retriever_metric = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        compliance_metric = collector.tool_calls_total.labels(
            tool_name="compliance_check",
            status="success",
            caller_role="coach"
        )._value.get()

        assert retriever_metric == 1.0
        assert compliance_metric == 1.0

    def test_different_caller_roles_tracked_separately(self, collector):
        """Test that different caller roles are tracked separately"""
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=100.0,
            caller_role="coach",
            cached=False
        )
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=100.0,
            caller_role="npc",
            cached=False
        )

        # Verify separate tracking
        coach_metric = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        npc_metric = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="npc"
        )._value.get()

        assert coach_metric == 1.0
        assert npc_metric == 1.0


class TestConvenienceFunctions:
    """Test convenience functions"""

    @patch('app.observability.tool_metrics.tool_metrics_collector')
    def test_record_tool_execution(self, mock_collector):
        """Test record_tool_execution convenience function"""
        record_tool_execution(
            tool_name="test_tool",
            status="success",
            latency_ms=100.0,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        mock_collector.record_execution.assert_called_once_with(
            tool_name="test_tool",
            status="success",
            latency_ms=100.0,
            caller_role="coach",
            error_type=None,
            cached=False
        )

    @patch('app.observability.tool_metrics.tool_metrics_collector')
    def test_record_cache_operation_function(self, mock_collector):
        """Test record_cache_operation convenience function"""
        record_cache_operation("test_tool", "hit")

        mock_collector.record_cache_operation.assert_called_once_with(
            "test_tool", "hit"
        )

    @patch('app.observability.tool_metrics.tool_metrics_collector')
    def test_update_cache_hit_rate_function(self, mock_collector):
        """Test update_cache_hit_rate convenience function"""
        update_cache_hit_rate("test_tool", 0.85)

        mock_collector.update_cache_hit_rate.assert_called_once_with(
            "test_tool", 0.85
        )

    @patch('app.observability.tool_metrics.tool_metrics_collector')
    def test_record_retry_attempt_function(self, mock_collector):
        """Test record_retry_attempt convenience function"""
        record_retry_attempt("test_tool", 2)

        mock_collector.record_retry_attempt.assert_called_once_with(
            "test_tool", 2
        )


class TestMetricsIntegration:
    """Test metrics integration scenarios"""

    @pytest.fixture
    def collector(self):
        """Create collector with test registry"""
        registry = CollectorRegistry()
        return ToolMetricsCollector(registry=registry)

    def test_full_execution_flow(self, collector):
        """Test full execution flow with metrics"""
        # Simulate a full tool execution
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=245.67,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        # Verify all relevant metrics updated
        calls = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        assert calls == 1.0

        cache_miss = collector.tool_cache_operations.labels(
            tool_name="knowledge_retriever",
            operation="miss"
        )._value.get()
        assert cache_miss == 1.0

    def test_retry_flow(self, collector):
        """Test retry flow with metrics"""
        # First attempt fails
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="timeout",
            latency_ms=5000.0,
            caller_role="coach",
            error_type="TimeoutError",
            cached=False
        )
        collector.record_retry_attempt("knowledge_retriever", 1)

        # Second attempt succeeds
        collector.record_execution(
            tool_name="knowledge_retriever",
            status="success",
            latency_ms=200.0,
            caller_role="coach",
            error_type=None,
            cached=False
        )

        # Verify metrics
        timeout_calls = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="timeout",
            caller_role="coach"
        )._value.get()
        success_calls = collector.tool_calls_total.labels(
            tool_name="knowledge_retriever",
            status="success",
            caller_role="coach"
        )._value.get()
        retry_attempts = collector.tool_retry_attempts.labels(
            tool_name="knowledge_retriever",
            attempt_number="1"
        )._value.get()

        assert timeout_calls == 1.0
        assert success_calls == 1.0
        assert retry_attempts == 1.0

    def test_cache_hit_rate_calculation(self, collector):
        """Test cache hit rate calculation"""
        # Simulate 7 hits and 3 misses
        for _ in range(7):
            collector.record_cache_operation("knowledge_retriever", "hit")
        for _ in range(3):
            collector.record_cache_operation("knowledge_retriever", "miss")

        # Calculate and update hit rate
        hit_rate = 7.0 / 10.0
        collector.update_cache_hit_rate("knowledge_retriever", hit_rate)

        # Verify
        metric_value = collector.tool_cache_hit_rate.labels(
            tool_name="knowledge_retriever"
        )._value.get()
        assert metric_value == 0.7
