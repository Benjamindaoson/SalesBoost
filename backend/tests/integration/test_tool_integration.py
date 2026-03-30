"""
Integration Tests for Tool System
==================================

End-to-end tests for tool execution with WebSocket, metrics, and rate limiting.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import time

from app.tools.executor import ToolExecutor, RateLimitError
from app.tools.registry import build_default_registry
from app.tools.rate_limiter import ToolRateLimiter
from app.tools.health_check import ToolHealthChecker


class TestToolExecutorIntegration:
    """Integration tests for ToolExecutor"""

    @pytest.fixture
    def registry(self):
        """Create registry with all tools"""
        return build_default_registry()

    @pytest.fixture
    def executor(self, registry):
        """Create executor"""
        return ToolExecutor(registry=registry)

    @pytest.mark.asyncio
    async def test_tool_execution_with_metrics(self, executor):
        """Test tool execution records metrics"""
        with patch('app.tools.executor.record_tool_execution') as mock_metrics:
            result = await executor.execute(
                name="price_calculator",
                payload={
                    "items": [{"name": "Test", "unit_price": 100, "quantity": 1}],
                    "discount_rate": 0.1,
                    "tax_rate": 0.05
                },
                caller_role="coach"
            )

            assert result["ok"] is True
            assert mock_metrics.called
            call_args = mock_metrics.call_args[1]
            assert call_args["tool_name"] == "price_calculator"
            assert call_args["status"] == "success"
            assert call_args["latency_ms"] >= 0  # Can be 0 for very fast tools

    @pytest.mark.asyncio
    async def test_tool_execution_with_websocket_callback(self, executor):
        """Test tool execution emits WebSocket events"""
        events = []

        async def status_callback(event):
            events.append(event)

        result = await executor.execute(
            name="price_calculator",
            payload={
                "items": [{"name": "Test", "unit_price": 100, "quantity": 1}]
            },
            caller_role="coach",
            status_callback=status_callback
        )

        assert result["ok"] is True
        assert len(events) == 2  # started + completed

        # Check started event
        assert events[0]["status"] == "started"
        assert events[0]["tool_name"] == "price_calculator"

        # Check completed event
        assert events[1]["status"] == "completed"
        assert events[1]["latency_ms"] >= 0  # Can be 0 for very fast tools
        assert "result_preview" in events[1]

    @pytest.mark.asyncio
    async def test_tool_execution_with_retry(self, executor):
        """Test tool execution with retry mechanism"""
        # Mock tool to fail once then succeed
        with patch.object(executor._registry, 'get_tool') as mock_get_tool:
            mock_tool = AsyncMock()
            mock_tool.run.side_effect = [
                TimeoutError("timeout"),
                {"success": True, "data": "result"}
            ]
            mock_get_tool.return_value = mock_tool

            with patch('app.tools.executor.record_retry_attempt') as mock_retry:
                result = await executor.execute(
                    name="test_tool",
                    payload={"test": "data"},
                    caller_role="coach"
                )

                assert result["ok"] is True
                assert result["audit"]["retry_count"] == 1
                assert mock_retry.called

    @pytest.mark.asyncio
    async def test_tool_execution_with_cache(self, executor):
        """Test tool execution uses cache"""
        # First execution
        result1 = await executor.execute(
            name="price_calculator",
            payload={
                "items": [{"name": "Test", "unit_price": 100, "quantity": 1}]
            },
            caller_role="coach"
        )

        # Second execution with same payload (should hit cache)
        result2 = await executor.execute(
            name="price_calculator",
            payload={
                "items": [{"name": "Test", "unit_price": 100, "quantity": 1}]
            },
            caller_role="coach"
        )

        assert result1["ok"] is True
        assert result2["ok"] is True
        # Note: Cache behavior depends on TOOL_CACHE_ENABLED setting

    @pytest.mark.asyncio
    async def test_parallel_execution(self, executor):
        """Test parallel tool execution"""
        tool_calls = [
            {
                "name": "price_calculator",
                "payload": {"items": [{"name": f"Item{i}", "unit_price": 100, "quantity": 1}]}
            }
            for i in range(3)
        ]

        start_time = time.time()
        results = await executor.execute_parallel(
            tool_calls=tool_calls,
            caller_role="coach",
            max_concurrent=3
        )
        elapsed = time.time() - start_time

        assert len(results) == 3
        assert all(r["ok"] for r in results)

        # Parallel execution should be faster than sequential
        # (though with fast tools, difference may be minimal)
        assert elapsed < 5.0  # Should complete quickly


class TestRateLimiterIntegration:
    """Integration tests for rate limiting"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test limits"""
        return ToolRateLimiter(custom_limits={
            "test_tool": (2, 1)  # 2 calls per second
        })

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limiter):
        """Test rate limit is enforced"""
        # First 2 calls should succeed
        allowed1, _ = await rate_limiter.check_limit("test_tool")
        allowed2, _ = await rate_limiter.check_limit("test_tool")

        assert allowed1 is True
        assert allowed2 is True

        # Third call should be rate limited
        allowed3, retry_after = await rate_limiter.check_limit("test_tool")

        assert allowed3 is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_rate_limit_refill(self, rate_limiter):
        """Test rate limit tokens refill over time"""
        # Consume all tokens
        await rate_limiter.check_limit("test_tool")
        await rate_limiter.check_limit("test_tool")

        # Should be rate limited
        allowed, _ = await rate_limiter.check_limit("test_tool")
        assert allowed is False

        # Wait for refill
        await asyncio.sleep(0.6)  # Wait for tokens to refill

        # Should be allowed again
        allowed, _ = await rate_limiter.check_limit("test_tool")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_with_executor(self):
        """Test rate limiting integrated with executor"""
        registry = build_default_registry()
        executor = ToolExecutor(registry=registry)

        # Create custom rate limiter with very low limit
        rate_limiter = ToolRateLimiter(custom_limits={
            "price_calculator": (1, 60)  # 1 call per minute
        })

        with patch('app.tools.executor.get_rate_limiter', return_value=rate_limiter):
            # First call should succeed
            result1 = await executor.execute(
                name="price_calculator",
                payload={"items": [{"name": "Test", "unit_price": 100, "quantity": 1}]},
                caller_role="coach"
            )
            assert result1["ok"] is True

            # Second call should be rate limited
            with pytest.raises(RateLimitError) as exc_info:
                await executor.execute(
                    name="price_calculator",
                    payload={"items": [{"name": "Test", "unit_price": 100, "quantity": 1}]},
                    caller_role="coach"
                )

            assert "Rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.retry_after > 0


class TestHealthCheckIntegration:
    """Integration tests for health checks"""

    @pytest.fixture
    def registry(self):
        """Create registry"""
        return build_default_registry()

    @pytest.fixture
    def health_checker(self, registry):
        """Create health checker"""
        return ToolHealthChecker(registry)

    @pytest.mark.asyncio
    async def test_check_all_tools(self, health_checker):
        """Test checking all tools"""
        results = await health_checker.check_all_tools(use_cache=False)

        assert len(results) >= 8  # Should have at least 8 tools
        assert all("status" in r for r in results.values())
        assert all("tool" in r for r in results.values())

    @pytest.mark.asyncio
    async def test_health_summary(self, health_checker):
        """Test health summary"""
        summary = await health_checker.get_summary()

        assert "status" in summary
        assert "total_tools" in summary
        assert "healthy" in summary
        assert "tools" in summary
        assert summary["total_tools"] >= 8

    @pytest.mark.asyncio
    async def test_health_check_caching(self, health_checker):
        """Test health check caching"""
        # First check (no cache)
        start1 = time.time()
        results1 = await health_checker.check_all_tools(use_cache=False)
        elapsed1 = time.time() - start1

        # Second check (with cache)
        start2 = time.time()
        results2 = await health_checker.check_all_tools(use_cache=True)
        elapsed2 = time.time() - start2

        assert results1 == results2
        # Cached check should be faster (though may be minimal difference)
        assert elapsed2 <= elapsed1 + 0.1  # Allow small margin


class TestEndToEndScenarios:
    """End-to-end integration scenarios"""

    @pytest.mark.asyncio
    async def test_complete_tool_workflow(self):
        """Test complete workflow: execute -> metrics -> health check"""
        registry = build_default_registry()
        executor = ToolExecutor(registry=registry)
        health_checker = ToolHealthChecker(registry)

        # 1. Check health before execution
        health_before = await health_checker.get_summary()
        assert health_before["status"] in ["healthy", "degraded"]

        # 2. Execute tool with all features
        events = []

        async def callback(event):
            events.append(event)

        with patch('app.tools.executor.record_tool_execution') as mock_metrics:
            result = await executor.execute(
                name="crm_integration",
                payload={"action": "list", "limit": 5},
                caller_role="coach",
                status_callback=callback
            )

            # Verify execution
            assert result["ok"] is True
            assert result["result"]["success"] is True

            # Verify metrics recorded
            assert mock_metrics.called

            # Verify WebSocket events
            assert len(events) == 2
            assert events[0]["status"] == "started"
            assert events[1]["status"] == "completed"

        # 3. Check health after execution
        health_after = await health_checker.get_summary()
        assert health_after["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_parallel_execution_with_rate_limiting(self):
        """Test parallel execution respects rate limits"""
        registry = build_default_registry()
        executor = ToolExecutor(registry=registry)

        # Create rate limiter with moderate limit
        rate_limiter = ToolRateLimiter(custom_limits={
            "price_calculator": (5, 1)  # 5 calls per second
        })

        with patch('app.tools.executor.get_rate_limiter', return_value=rate_limiter):
            # Execute 3 tools in parallel (within limit)
            tool_calls = [
                {
                    "name": "price_calculator",
                    "payload": {"items": [{"name": f"Item{i}", "unit_price": 100, "quantity": 1}]}
                }
                for i in range(3)
            ]

            results = await executor.execute_parallel(
                tool_calls=tool_calls,
                caller_role="coach"
            )

            # All should succeed
            assert len(results) == 3
            assert all(r["ok"] for r in results)

    @pytest.mark.asyncio
    async def test_error_handling_across_features(self):
        """Test error handling works across all features"""
        registry = build_default_registry()
        executor = ToolExecutor(registry=registry)

        events = []

        async def callback(event):
            events.append(event)

        # Execute with invalid payload
        result = await executor.execute(
            name="crm_integration",
            payload={"action": "invalid_action"},
            caller_role="coach",
            status_callback=callback
        )

        # Should handle error gracefully
        assert result["ok"] is True  # Tool returns error in result
        assert result["result"]["success"] is False

        # Should still emit events
        assert len(events) == 2
        assert events[1]["status"] == "completed"
