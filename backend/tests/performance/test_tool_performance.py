"""
Performance Tests for Tool System
==================================

Benchmark tests for tool execution performance, caching, and parallel execution.
"""
import pytest
import asyncio
import time
from statistics import mean, median

from app.tools.executor import ToolExecutor
from app.tools.registry import build_default_registry
from app.tools.tool_cache import ToolCache


class TestToolExecutionPerformance:
    """Performance tests for tool execution"""

    @pytest.fixture
    def registry(self):
        """Create registry"""
        return build_default_registry()

    @pytest.fixture
    def executor(self, registry):
        """Create executor"""
        return ToolExecutor(registry=registry)

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_single_tool_latency(self, executor):
        """Test single tool execution latency"""
        latencies = []

        for _ in range(10):
            start = time.time()
            result = await executor.execute(
                name="price_calculator",
                payload={"items": [{"name": "Test", "unit_price": 100, "quantity": 1}]},
                caller_role="coach"
            )
            latency = (time.time() - start) * 1000  # Convert to ms

            assert result["ok"] is True
            latencies.append(latency)

        avg_latency = mean(latencies)
        p50_latency = median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print("\nSingle Tool Execution Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P50: {p50_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")

        # Performance assertions
        assert avg_latency < 100, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 200, f"P95 latency too high: {p95_latency:.2f}ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_parallel_execution_performance(self, executor):
        """Test parallel execution performance vs sequential"""
        tool_calls = [
            {
                "name": "price_calculator",
                "payload": {"items": [{"name": f"Item{i}", "unit_price": 100, "quantity": 1}]}
            }
            for i in range(5)
        ]

        # Sequential execution
        start_seq = time.time()
        for call in tool_calls:
            await executor.execute(
                name=call["name"],
                payload=call["payload"],
                caller_role="coach"
            )
        sequential_time = time.time() - start_seq

        # Parallel execution
        start_par = time.time()
        await executor.execute_parallel(
            tool_calls=tool_calls,
            caller_role="coach",
            max_concurrent=5
        )
        parallel_time = time.time() - start_par

        # Avoid division by zero for very fast execution
        if parallel_time > 0:
            speedup = sequential_time / parallel_time
        else:
            speedup = 1.0

        print("\nParallel Execution Performance:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Parallel: {parallel_time:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")

        # Parallel should be faster (or at least not slower)
        # Allow for very fast execution where timing is imprecise
        if sequential_time > 0.01:  # Only check if execution took meaningful time
            assert parallel_time <= sequential_time * 1.2  # Allow 20% margin

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_performance(self, executor):
        """Test cache hit performance"""
        payload = {"items": [{"name": "Test", "unit_price": 100, "quantity": 1}]}

        # First execution (cache miss)
        start_miss = time.time()
        result1 = await executor.execute(
            name="price_calculator",
            payload=payload,
            caller_role="coach"
        )
        miss_time = (time.time() - start_miss) * 1000

        # Second execution (cache hit)
        start_hit = time.time()
        result2 = await executor.execute(
            name="price_calculator",
            payload=payload,
            caller_role="coach"
        )
        hit_time = (time.time() - start_hit) * 1000

        print("\nCache Performance:")
        print(f"  Cache Miss: {miss_time:.2f}ms")
        print(f"  Cache Hit: {hit_time:.2f}ms")
        if hit_time > 0:
            print(f"  Speedup: {miss_time / hit_time:.2f}x")
        else:
            print("  Speedup: N/A (hit time too fast to measure)")

        assert result1["ok"] is True
        assert result2["ok"] is True

        # Cache hit should be faster (if caching is enabled)
        # Note: Depends on TOOL_CACHE_ENABLED setting

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_load(self, executor):
        """Test performance under concurrent load"""
        # Temporarily disable rate limiting for this test
        from app.tools.rate_limiter import get_rate_limiter
        rate_limiter = get_rate_limiter()
        rate_limiter.reset()  # Reset all rate limiters

        # Use a tool with higher rate limit or disable rate limiting
        from core.config import get_settings
        settings = get_settings()
        original_enabled = settings.TOOL_RATE_LIMIT_ENABLED
        settings.TOOL_RATE_LIMIT_ENABLED = False  # Temporarily disable

        try:
            num_concurrent = 20
            num_iterations = 5

            async def execute_batch():
                """Execute a batch of tool calls"""
                tasks = []
                for _ in range(num_iterations):
                    task = executor.execute(
                        name="price_calculator",
                        payload={"items": [{"name": "Test", "unit_price": 100, "quantity": 1}]},
                        caller_role="coach"
                    )
                    tasks.append(task)
                return await asyncio.gather(*tasks, return_exceptions=True)

            # Execute concurrent batches
            start = time.time()
            batch_tasks = [execute_batch() for _ in range(num_concurrent)]
            all_results = await asyncio.gather(*batch_tasks)
            total_time = time.time() - start

            # Flatten results
            results = [r for batch in all_results for r in batch]
            total_calls = num_concurrent * num_iterations

            success_count = sum(1 for r in results if isinstance(r, dict) and r.get("ok"))
            throughput = total_calls / total_time

            print("\nConcurrent Load Test:")
            print(f"  Total Calls: {total_calls}")
            print(f"  Successful: {success_count}")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.2f} calls/sec")

            # Performance assertions
            assert success_count >= total_calls * 0.95  # 95% success rate
            assert throughput > 10  # At least 10 calls/sec
        finally:
            # Restore original setting
            settings.TOOL_RATE_LIMIT_ENABLED = original_enabled


class TestCachePerformance:
    """Performance tests for caching"""

    @pytest.fixture
    def cache(self):
        """Create cache"""
        return ToolCache()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_lookup_performance(self, cache):
        """Test cache lookup performance"""
        # Populate cache
        for i in range(100):
            await cache.set(
                "test_tool",
                {"query": f"test query {i}"},
                {"result": f"result {i}"}
            )

        # Measure lookup performance
        latencies = []
        for i in range(100):
            start = time.time()
            await cache.get("test_tool", {"query": f"test query {i}"})
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[95]

        print("\nCache Lookup Performance:")
        print(f"  Average: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")

        # Cache lookups should be very fast
        assert avg_latency < 1.0, f"Cache lookup too slow: {avg_latency:.3f}ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_statistics_performance(self, cache):
        """Test cache statistics calculation performance"""
        # Populate cache with many entries
        for i in range(1000):
            await cache.set(
                f"tool_{i % 10}",
                {"query": f"query {i}"},
                {"result": f"result {i}"}
            )

        # Measure statistics calculation
        start = time.time()
        stats = cache.get_statistics()
        stats_time = (time.time() - start) * 1000

        print("\nCache Statistics Performance:")
        print(f"  Calculation Time: {stats_time:.2f}ms")
        print(f"  Cache Size: {stats['size']}")

        # Statistics should be fast even with large cache
        assert stats_time < 10.0, f"Statistics calculation too slow: {stats_time:.2f}ms"


class TestRateLimiterPerformance:
    """Performance tests for rate limiter"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_rate_limit_check_performance(self):
        """Test rate limit check performance"""
        from app.tools.rate_limiter import ToolRateLimiter

        rate_limiter = ToolRateLimiter()

        # Measure check performance
        latencies = []
        for _ in range(1000):
            start = time.time()
            await rate_limiter.check_limit("test_tool")
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[950]

        print("\nRate Limit Check Performance:")
        print(f"  Average: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")

        # Rate limit checks should be very fast
        assert avg_latency < 0.5, f"Rate limit check too slow: {avg_latency:.3f}ms"


class TestMemoryUsage:
    """Memory usage tests"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_memory_usage(self):
        """Test cache memory usage with many entries"""
        import sys

        cache = ToolCache()

        # Measure memory before
        initial_size = sys.getsizeof(cache._entries)

        # Add many entries
        for i in range(1000):
            await cache.set(
                "test_tool",
                {"query": f"query {i}"},
                {"result": f"result {i}" * 10}  # Larger result
            )

        # Measure memory after
        final_size = sys.getsizeof(cache._entries)
        memory_per_entry = (final_size - initial_size) / 1000

        print("\nCache Memory Usage:")
        print(f"  Initial: {initial_size / 1024:.2f} KB")
        print(f"  Final: {final_size / 1024:.2f} KB")
        print(f"  Per Entry: {memory_per_entry:.2f} bytes")

        # Memory usage should be reasonable
        assert memory_per_entry < 1000, f"Memory per entry too high: {memory_per_entry:.2f} bytes"


# Pytest configuration for performance tests
def pytest_configure(config):
    """Register performance marker"""
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
