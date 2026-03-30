#!/usr/bin/env python3
"""
Production Monitoring Script
Monitor SalesBoost system health and performance

Features:
- Health check monitoring
- Performance metrics tracking
- Alert notifications
- Log analysis

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import time
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ProductionMonitor:
    """Production monitoring for SalesBoost"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.metrics_history = []
        self.alert_threshold = {
            "response_time_ms": 1000,  # Alert if >1s
            "error_rate": 0.05,  # Alert if >5%
            "memory_mb": 1000  # Alert if >1GB
        }

    def check_health(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            response = requests.get(
                f"{self.base_url}/health/live",
                timeout=5
            )

            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/metrics",
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status code: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def test_semantic_search(self) -> Dict[str, Any]:
        """Test semantic search functionality"""
        try:
            test_query = "价格异议"

            response = requests.post(
                f"{self.base_url}/api/knowledge/search",
                json={"query": test_query, "top_k": 3},
                timeout=10
            )

            return {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "results_count": len(response.json().get("results", [])) if response.status_code == 200 else 0,
                "timestamp": datetime.now().isoformat()
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def check_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """Check for alert conditions"""
        alerts = []

        # Check response time
        if "response_time_ms" in metrics:
            if metrics["response_time_ms"] > self.alert_threshold["response_time_ms"]:
                alerts.append(
                    f"⚠️ High response time: {metrics['response_time_ms']:.0f}ms "
                    f"(threshold: {self.alert_threshold['response_time_ms']}ms)"
                )

        # Check memory usage
        if "memory_mb" in metrics:
            if metrics["memory_mb"] > self.alert_threshold["memory_mb"]:
                alerts.append(
                    f"⚠️ High memory usage: {metrics['memory_mb']:.0f}MB "
                    f"(threshold: {self.alert_threshold['memory_mb']}MB)"
                )

        return alerts

    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run one monitoring cycle"""
        print(f"\n{'='*70}")
        print(f"Monitoring Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        results = {}

        # 1. Health check
        print("\n[1/3] Health Check...")
        health = self.check_health()
        results["health"] = health

        if health["status"] == "healthy":
            print(f"  ✓ Status: {health['status']}")
            print(f"  ✓ Response time: {health['response_time_ms']:.0f}ms")
        else:
            print(f"  ✗ Status: {health['status']}")
            if "error" in health:
                print(f"  ✗ Error: {health['error']}")

        # 2. System metrics
        print("\n[2/3] System Metrics...")
        metrics = self.get_metrics()
        results["metrics"] = metrics

        if "error" not in metrics:
            print("  ✓ Metrics retrieved")
            if "total_requests" in metrics:
                print(f"  ✓ Total requests: {metrics['total_requests']}")
            if "avg_response_time_ms" in metrics:
                print(f"  ✓ Avg response time: {metrics['avg_response_time_ms']:.0f}ms")
        else:
            print(f"  ✗ Error: {metrics['error']}")

        # 3. Semantic search test
        print("\n[3/3] Semantic Search Test...")
        search_test = self.test_semantic_search()
        results["search_test"] = search_test

        if search_test["status"] == "success":
            print(f"  ✓ Status: {search_test['status']}")
            print(f"  ✓ Response time: {search_test['response_time_ms']:.0f}ms")
            print(f"  ✓ Results: {search_test['results_count']}")
        else:
            print(f"  ✗ Status: {search_test['status']}")
            if "error" in search_test:
                print(f"  ✗ Error: {search_test['error']}")

        # Check for alerts
        alerts = self.check_alerts({**health, **metrics, **search_test})
        results["alerts"] = alerts

        if alerts:
            print(f"\n{'='*70}")
            print("ALERTS")
            print(f"{'='*70}")
            for alert in alerts:
                print(f"  {alert}")

        # Save to history
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "results": results
        })

        # Keep only last 100 entries
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

        return results

    def save_report(self, output_file: str = "storage/monitoring/report.json"):
        """Save monitoring report"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "generated_at": datetime.now().isoformat(),
            "base_url": self.base_url,
            "metrics_history": self.metrics_history,
            "summary": {
                "total_cycles": len(self.metrics_history),
                "healthy_cycles": sum(
                    1 for m in self.metrics_history
                    if m["results"]["health"]["status"] == "healthy"
                ),
                "total_alerts": sum(
                    len(m["results"]["alerts"])
                    for m in self.metrics_history
                )
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Report saved to: {output_path}")


def main():
    """Main monitoring loop"""
    import argparse

    parser = argparse.ArgumentParser(description="SalesBoost Production Monitor")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the application"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="Number of monitoring cycles (0 = infinite)"
    )

    args = parser.parse_args()

    monitor = ProductionMonitor(base_url=args.url)

    print("="*70)
    print("SalesBoost Production Monitor")
    print("="*70)
    print(f"Base URL: {args.url}")
    print(f"Interval: {args.interval}s")
    print(f"Cycles: {'Infinite' if args.cycles == 0 else args.cycles}")
    print("="*70)
    print("\nPress Ctrl+C to stop monitoring\n")

    cycle_count = 0

    try:
        while True:
            # Run monitoring cycle
            monitor.run_monitoring_cycle()

            cycle_count += 1

            # Save report
            if cycle_count % 10 == 0:  # Save every 10 cycles
                monitor.save_report()

            # Check if we should stop
            if args.cycles > 0 and cycle_count >= args.cycles:
                break

            # Wait for next cycle
            if args.cycles == 0 or cycle_count < args.cycles:
                print(f"\nNext check in {args.interval}s...")
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

    finally:
        # Save final report
        monitor.save_report()
        print("\n[OK] Monitoring complete")


if __name__ == "__main__":
    main()
