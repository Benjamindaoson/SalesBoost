"""
Performance Benchmark Tests

Measures system performance under various conditions.
"""

import pytest
import asyncio
import time
from statistics import mean, median, stdev

from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def benchmark_client():
    """Create benchmark client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.asyncio
    async def test_health_check_latency(self, benchmark_client):
        """Benchmark health check endpoint."""
        latencies = []

        for _ in range(100):
            start = time.time()
            response = await benchmark_client.get("/api/v1/health")
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            assert response.status_code == 200

        print("\nHealth Check Latency:")
        print(f"  Mean: {mean(latencies):.2f}ms")
        print(f"  Median: {median(latencies):.2f}ms")
        print(f"  Std Dev: {stdev(latencies):.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")
        print(f"  P95: {sorted(latencies)[94]:.2f}ms")
        print(f"  P99: {sorted(latencies)[98]:.2f}ms")

        assert mean(latencies) < 50  # Average < 50ms
        assert sorted(latencies)[94] < 100  # P95 < 100ms

    @pytest.mark.asyncio
    async def test_rag_retrieval_latency(self, benchmark_client):
        """Benchmark RAG retrieval."""
        latencies = []

        queries = [
            "信用卡积分规则",
            "如何申请信用卡",
            "信用卡年费",
            "信用卡额度",
            "信用卡还款",
        ]

        for query in queries * 20:  # 100 requests
            start = time.time()
            response = await benchmark_client.post(
                "/api/v1/rag/retrieve",
                json={"query": query, "top_k": 5}
            )
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            assert response.status_code == 200

        print("\nRAG Retrieval Latency:")
        print(f"  Mean: {mean(latencies):.2f}ms")
        print(f"  Median: {median(latencies):.2f}ms")
        print(f"  P95: {sorted(latencies)[94]:.2f}ms")
        print(f"  P99: {sorted(latencies)[98]:.2f}ms")

        assert mean(latencies) < 200  # Average < 200ms
        assert sorted(latencies)[94] < 500  # P95 < 500ms

    @pytest.mark.asyncio
    async def test_concurrent_load(self, benchmark_client):
        """Test system under concurrent load."""
        async def make_request():
            start = time.time()
            response = await benchmark_client.get("/api/v1/health")
            latency = (time.time() - start) * 1000
            return response.status_code, latency

        # Test with increasing concurrency
        for concurrency in [10, 50, 100]:
            tasks = [make_request() for _ in range(concurrency)]

            start = time.time()
            results = await asyncio.gather(*tasks)
            total_time = (time.time() - start) * 1000

            status_codes = [r[0] for r in results]
            latencies = [r[1] for r in results]

            success_rate = sum(1 for s in status_codes if s == 200) / len(status_codes)
            throughput = concurrency / (total_time / 1000)

            print(f"\nConcurrent Load (n={concurrency}):")
            print(f"  Success Rate: {success_rate * 100:.1f}%")
            print(f"  Throughput: {throughput:.1f} req/s")
            print(f"  Mean Latency: {mean(latencies):.2f}ms")
            print(f"  P95 Latency: {sorted(latencies)[int(concurrency * 0.95)]:.2f}ms")

            assert success_rate >= 0.95  # 95% success rate

    @pytest.mark.asyncio
    async def test_memory_usage(self, benchmark_client):
        """Test memory usage under load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Make many requests
        for _ in range(1000):
            await benchmark_client.get("/api/v1/health")

        # Check memory after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory

        print("\nMemory Usage:")
        print(f"  Baseline: {baseline_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase


class TestLoadTesting:
    """Load testing scenarios."""

    @pytest.mark.asyncio
    async def test_sustained_load(self, benchmark_client):
        """Test system under sustained load."""
        duration = 10  # seconds
        request_rate = 10  # requests per second

        start_time = time.time()
        request_count = 0
        errors = 0
        latencies = []

        while time.time() - start_time < duration:
            batch_start = time.time()

            # Send batch of requests
            tasks = []
            for _ in range(request_rate):
                async def make_request():
                    req_start = time.time()
                    try:
                        response = await benchmark_client.get("/api/v1/health")
                        latency = (time.time() - req_start) * 1000
                        return response.status_code, latency
                    except Exception:
                        return 500, 0

                tasks.append(make_request())

            results = await asyncio.gather(*tasks)

            for status, latency in results:
                request_count += 1
                if status != 200:
                    errors += 1
                else:
                    latencies.append(latency)

            # Wait for next second
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

        error_rate = errors / request_count
        avg_latency = mean(latencies) if latencies else 0

        print("\nSustained Load Test:")
        print(f"  Duration: {duration}s")
        print(f"  Total Requests: {request_count}")
        print(f"  Error Rate: {error_rate * 100:.2f}%")
        print(f"  Avg Latency: {avg_latency:.2f}ms")
        print(f"  Throughput: {request_count / duration:.1f} req/s")

        assert error_rate < 0.01  # Less than 1% errors
        assert avg_latency < 100  # Average latency < 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
