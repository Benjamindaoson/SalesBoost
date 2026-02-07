"""
Locust Load Testing for SalesBoost WebSocket API

Usage:
    # Test with 10 users
    locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 10 -r 2 --run-time 60s --html=reports/load_test_10users.html

    # Test with 50 users
    locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 50 -r 5 --run-time 120s --html=reports/load_test_50users.html

    # Test with 100 users
    locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 100 -r 10 --run-time 180s --html=reports/load_test_100users.html

Requirements:
    pip install locust websocket-client
"""

import json
import time
import uuid
from locust import User, task, between, events
from websocket import create_connection, WebSocketTimeoutException


class WebSocketClient:
    """WebSocket client wrapper for Locust"""

    def __init__(self, host):
        self.host = host.replace("http://", "ws://").replace("https://", "wss://")
        self.ws = None
        self.session_id = str(uuid.uuid4())

    def connect(self):
        """Connect to WebSocket"""
        try:
            ws_url = f"{self.host}/ws/chat?session_id={self.session_id}"
            self.ws = create_connection(ws_url, timeout=10)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send_message(self, message: str):
        """Send message and measure response time"""
        if not self.ws:
            return None, "Not connected"

        start_time = time.time()
        request_meta = {
            "request_type": "websocket",
            "name": "send_message",
            "start_time": start_time,
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }

        try:
            # Send message
            payload = {
                "type": "user_message",
                "content": message,
                "session_id": self.session_id,
            }
            self.ws.send(json.dumps(payload))

            # Wait for response
            response = self.ws.recv()
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            request_meta["response_length"] = len(response)
            request_meta["response_time"] = response_time

            # Fire success event
            events.request.fire(**request_meta)

            return json.loads(response), None

        except WebSocketTimeoutException as e:
            request_meta["exception"] = e
            events.request.fire(**request_meta)
            return None, "Timeout"

        except Exception as e:
            request_meta["exception"] = e
            events.request.fire(**request_meta)
            return None, str(e)

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


class SalesBoostUser(User):
    """Simulated user for load testing"""

    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts"""
        self.client = WebSocketClient(self.host)
        connected = self.client.connect()
        if not connected:
            raise Exception("Failed to connect to WebSocket")

    def on_stop(self):
        """Called when a simulated user stops"""
        self.client.close()

    @task(3)
    def send_greeting(self):
        """Send greeting message (30% of traffic)"""
        messages = [
            "你好，我想了解一下你们的产品",
            "Hello, I'm interested in your service",
            "嗨，能介绍一下吗？",
        ]
        import random
        message = random.choice(messages)
        self.client.send_message(message)

    @task(2)
    def send_product_inquiry(self):
        """Send product inquiry (20% of traffic)"""
        messages = [
            "这个产品有什么功能？",
            "能详细介绍一下产品特性吗？",
            "What are the key features?",
        ]
        import random
        message = random.choice(messages)
        self.client.send_message(message)

    @task(2)
    def send_price_inquiry(self):
        """Send price inquiry (20% of traffic)"""
        messages = [
            "价格是多少？",
            "How much does it cost?",
            "有什么优惠吗？",
        ]
        import random
        message = random.choice(messages)
        self.client.send_message(message)

    @task(2)
    def send_objection(self):
        """Send objection (20% of traffic)"""
        messages = [
            "太贵了，能便宜点吗？",
            "我觉得竞品更好",
            "我需要考虑一下",
        ]
        import random
        message = random.choice(messages)
        self.client.send_message(message)

    @task(1)
    def send_closing_signal(self):
        """Send closing signal (10% of traffic)"""
        messages = [
            "好的，我想购买",
            "怎么下单？",
            "可以签合同了",
        ]
        import random
        message = random.choice(messages)
        self.client.send_message(message)


# Custom stats for WebSocket
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics"""
    print("=" * 80)
    print("SalesBoost WebSocket Load Test")
    print("=" * 80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary after test"""
    print("\n" + "=" * 80)
    print("Load Test Summary")
    print("=" * 80)

    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    avg_response_time = stats.total.avg_response_time
    min_response_time = stats.total.min_response_time
    max_response_time = stats.total.max_response_time

    # Calculate percentiles
    response_times = stats.total.response_times
    if response_times:
        sorted_times = sorted(response_times.items())
        total_count = sum(count for _, count in sorted_times)

        def get_percentile(p):
            target = total_count * p / 100
            cumulative = 0
            for time_ms, count in sorted_times:
                cumulative += count
                if cumulative >= target:
                    return time_ms
            return sorted_times[-1][0] if sorted_times else 0

        p50 = get_percentile(50)
        p95 = get_percentile(95)
        p99 = get_percentile(99)
    else:
        p50 = p95 = p99 = 0

    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures} ({total_failures/max(total_requests, 1)*100:.1f}%)")
    print(f"Avg Response Time: {avg_response_time:.0f} ms")
    print(f"Min Response Time: {min_response_time:.0f} ms")
    print(f"Max Response Time: {max_response_time:.0f} ms")
    print(f"P50 (Median): {p50:.0f} ms")
    print(f"P95: {p95:.0f} ms")
    print(f"P99: {p99:.0f} ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("=" * 80)

    # Save results to JSON
    results = {
        "total_requests": total_requests,
        "total_failures": total_failures,
        "failure_rate": total_failures / max(total_requests, 1) * 100,
        "avg_response_time_ms": avg_response_time,
        "min_response_time_ms": min_response_time,
        "max_response_time_ms": max_response_time,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "requests_per_second": stats.total.total_rps,
    }

    import os
    os.makedirs("tests/performance/reports", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    with open(f"tests/performance/reports/load_test_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: tests/performance/reports/load_test_{timestamp}.json")
