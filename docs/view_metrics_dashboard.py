"""
Simple Metrics Dashboard
Reads metrics.jsonl and displays real-time statistics
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List


def read_metrics(file_path: Path, hours: int = 24) -> List[Dict]:
    """Read metrics from JSONL file within time window"""
    if not file_path.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    metrics = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                timestamp = datetime.fromisoformat(entry["timestamp"])

                if timestamp >= cutoff:
                    metrics.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    return metrics


def compute_aggregates(metrics: List[Dict]) -> Dict:
    """Compute aggregate statistics across all snapshots"""
    if not metrics:
        return {}

    component_data = defaultdict(lambda: {
        "total_requests": 0,
        "total_successes": 0,
        "latencies": []
    })

    for snapshot in metrics:
        for component_key, stats in snapshot.get("components", {}).items():
            data = component_data[component_key]
            data["total_requests"] += stats["count"]
            data["total_successes"] += int(stats["count"] * stats["success_rate"])

            # Collect all latency percentiles for averaging
            data["latencies"].append({
                "mean": stats["latency"]["mean"],
                "p95": stats["latency"]["p95"],
                "p99": stats["latency"]["p99"]
            })

    # Compute averages
    aggregates = {}
    for component_key, data in component_data.items():
        num_snapshots = len(data["latencies"])

        avg_mean = sum(l["mean"] for l in data["latencies"]) / num_snapshots
        avg_p95 = sum(l["p95"] for l in data["latencies"]) / num_snapshots
        avg_p99 = sum(l["p99"] for l in data["latencies"]) / num_snapshots

        success_rate = (data["total_successes"] / data["total_requests"]
                       if data["total_requests"] > 0 else 0)

        aggregates[component_key] = {
            "total_requests": data["total_requests"],
            "success_rate": success_rate,
            "avg_latency_mean": avg_mean,
            "avg_latency_p95": avg_p95,
            "avg_latency_p99": avg_p99
        }

    return aggregates


def display_dashboard(aggregates: Dict, time_window: int) -> None:
    """Display dashboard in terminal"""
    print("\n" + "=" * 80)
    print(f"📊 SALESBOOST METRICS DASHBOARD (Last {time_window}h)")
    print("=" * 80)

    if not aggregates:
        print("\n⚠️  No metrics data available")
        print("   Make sure:")
        print("   1. Performance monitoring is enabled (PERFORMANCE_MONITORING=true)")
        print("   2. System has been running and collecting data")
        print("   3. Check logs/metrics.jsonl exists")
        return

    print()
    for component_key, stats in aggregates.items():
        print(f"📈 {component_key}")
        print(f"   Total Requests: {stats['total_requests']:,}")
        print(f"   Success Rate:   {stats['success_rate']*100:.1f}%")
        print("   Latency (avg):")
        print(f"     Mean: {stats['avg_latency_mean']:.1f}ms")
        print(f"     P95:  {stats['avg_latency_p95']:.1f}ms")
        print(f"     P99:  {stats['avg_latency_p99']:.1f}ms")

        # Health status indicator
        if stats['success_rate'] >= 0.95 and stats['avg_latency_p99'] < 200:
            status = "✅ Healthy"
        elif stats['success_rate'] >= 0.90 and stats['avg_latency_p99'] < 500:
            status = "⚠️  Warning"
        else:
            status = "❌ Critical"

        print(f"   Status: {status}")
        print()

    print("=" * 80)


def main():
    """Main dashboard function"""
    metrics_file = Path("logs/metrics.jsonl")
    time_window = 24  # hours

    print("\n🔄 Loading metrics...")
    metrics = read_metrics(metrics_file, hours=time_window)

    if not metrics:
        print(f"\n⚠️  No metrics file found at: {metrics_file}")
        print("   Run the application first to generate metrics.")
        sys.exit(1)

    print(f"✓ Loaded {len(metrics)} snapshots")

    aggregates = compute_aggregates(metrics)
    display_dashboard(aggregates, time_window)


if __name__ == "__main__":
    main()
