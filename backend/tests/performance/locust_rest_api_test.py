"""
Locust Load Testing for SalesBoost REST API

Usage:
    locust -f tests/performance/locust_rest_api_test.py --host=http://localhost:8000 -u 50 -r 5 --run-time 120s --html=reports/rest_api_test.html

Requirements:
    pip install locust
"""

import json
import time
from locust import HttpUser, task, between, events


class SalesBoostAPIUser(HttpUser):
    """Simulated user for REST API load testing"""

    wait_time = between(1, 3)

    def on_start(self):
        """Setup - create session"""
        self.session_id = f"test_session_{time.time()}"
        self.headers = {
            "Content-Type": "application/json",
        }

    @task(3)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_metrics(self):
        """Get Prometheus metrics"""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def knowledge_retrieval(self):
        """Test knowledge retrieval (if endpoint exists)"""
        payload = {
            "query": "如何处理价格异议？",
            "top_k": 5
        }
        with self.client.post(
            "/api/v1/knowledge/search",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:  # 404 is ok if endpoint doesn't exist
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary after test"""
    print("\n" + "=" * 80)
    print("REST API Load Test Summary")
    print("=" * 80)

    stats = environment.stats
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Avg Response Time: {stats.total.avg_response_time:.0f} ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("=" * 80)
