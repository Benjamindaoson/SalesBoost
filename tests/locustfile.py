"""
Locust Load Testing Script for SalesBoost Coordinator
======================================================

Tests coordinator performance under various load conditions.

Usage:
    # Basic test
    locust -f locustfile.py --host=http://localhost:8000

    # Headless mode
    locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --headless

    # With web UI
    locust -f locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0 --web-port=8089
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


class CoordinatorUser(HttpUser):
    """
    Simulates a user interacting with the SalesBoost coordinator.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts."""
        self.session_id = f"load_test_{self.environment.runner.user_count}_{int(time.time())}"
        self.turn_number = 0

        # Authenticate (if required)
        # self.client.post("/api/v1/auth/token", data={
        #     "username": "test_user",
        #     "password": "test_password"
        # })

    @task(5)
    def send_chat_message(self):
        """
        Send a chat message through WebSocket endpoint.
        Weight: 5 (most common action)
        """
        self.turn_number += 1

        messages = [
            "你好，我想了解一下你们的产品",
            "这个产品的价格是多少？",
            "有什么优惠活动吗？",
            "我需要更多的技术细节",
            "可以给我发一份报价单吗？",
            "你们的售后服务怎么样？",
            "交货期是多久？",
            "支持哪些支付方式？"
        ]

        payload = {
            "session_id": self.session_id,
            "message": random.choice(messages),
            "user_id": f"user_{self.environment.runner.user_count}",
            "turn_number": self.turn_number
        }

        with self.client.post(
            "/ws/chat",
            json=payload,
            catch_response=True,
            name="/ws/chat [coordinator]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # Authentication required
                response.failure("Authentication required")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def submit_feedback(self):
        """
        Submit user feedback.
        Weight: 2 (less common than chat)
        """
        if self.turn_number == 0:
            # Can't submit feedback without a conversation
            raise RescheduleTask()

        payload = {
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "rating": random.randint(3, 5),  # Mostly positive feedback
            "comment": random.choice([
                "Very helpful!",
                "Good response",
                "Could be better",
                "Excellent service",
                None  # Sometimes no comment
            ])
        }

        with self.client.post(
            "/api/v1/feedback/submit",
            json=payload,
            catch_response=True,
            name="/api/v1/feedback/submit"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication required")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def check_health(self):
        """
        Check system health.
        Weight: 1 (occasional monitoring)
        """
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["healthy", "degraded"]:
                    response.success()
                else:
                    response.failure(f"Unhealthy status: {data.get('status')}")
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def get_metrics(self):
        """
        Fetch Prometheus metrics.
        Weight: 1 (monitoring)
        """
        with self.client.get(
            "/metrics",
            catch_response=True,
            name="/metrics"
        ) as response:
            if response.status_code == 200:
                # Check if coordinator metrics are present
                if "coordinator_" in response.text:
                    response.success()
                else:
                    response.failure("Coordinator metrics not found")
            else:
                response.failure(f"Metrics fetch failed: {response.status_code}")


class SpikeTestUser(HttpUser):
    """
    User for spike testing - sends bursts of requests.
    """

    wait_time = between(0.1, 0.5)  # Very short wait time

    def on_start(self):
        self.session_id = f"spike_test_{int(time.time())}"

    @task
    def rapid_fire_messages(self):
        """Send rapid-fire messages to test spike handling."""
        for i in range(5):  # Send 5 messages in quick succession
            self.client.post("/ws/chat", json={
                "session_id": self.session_id,
                "message": f"Spike test message {i}",
                "user_id": f"spike_user_{self.environment.runner.user_count}"
            })


# Custom events for detailed metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("\n" + "="*60)
    print("  LOAD TEST STARTING")
    print("="*60)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("\n" + "="*60)
    print("  LOAD TEST COMPLETE")
    print("="*60)

    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"P95 response time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 response time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
    print("="*60 + "\n")


# Test scenarios
class BaselineLoadTest(CoordinatorUser):
    """
    Baseline load test: 100 users, steady load.
    """
    wait_time = between(2, 5)


class SoakTest(CoordinatorUser):
    """
    Soak test: 50 users, long duration (24h).
    """
    wait_time = between(5, 10)


if __name__ == "__main__":
    print("""
    Locust Load Testing Script for SalesBoost Coordinator
    ======================================================

    Available test scenarios:

    1. Baseline Load Test (100 users, 5 minutes):
       locust -f locustfile.py --host=http://localhost:8000 \\
              --users 100 --spawn-rate 10 --run-time 5m --headless

    2. Spike Test (0→500 users in 10s):
       locust -f locustfile.py --host=http://localhost:8000 \\
              --users 500 --spawn-rate 50 --run-time 2m --headless \\
              --user-classes SpikeTestUser

    3. Soak Test (50 users, 24 hours):
       locust -f locustfile.py --host=http://localhost:8000 \\
              --users 50 --spawn-rate 5 --run-time 24h --headless \\
              --user-classes SoakTest

    4. Interactive Web UI:
       locust -f locustfile.py --host=http://localhost:8000
       # Then open http://localhost:8089

    Monitoring during test:
    - Watch Grafana dashboards
    - Monitor Redis queue length: redis-cli llen celery
    - Check Celery worker logs
    - Monitor system resources (CPU, memory, connections)
    """)
