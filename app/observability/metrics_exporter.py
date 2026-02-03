"""
Performance Metrics Exporter
Exports performance monitoring data to files and stdout for observability
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.observability.performance_monitor import performance_monitor
from app.config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Exports performance metrics to files and logs

    Outputs:
        - logs/metrics.jsonl: Time-series metrics in JSON Lines format
        - stdout: Summary statistics (if enabled)
    """

    def __init__(self, export_dir: str = "logs"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True, parents=True)
        self.metrics_file = self.export_dir / "metrics.jsonl"
        self._running = False
        self._task = None

    def export_snapshot(self) -> Dict[str, Any]:
        """
        Export current metrics snapshot

        Returns:
            Dictionary with timestamp and all component metrics
        """
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }

        all_stats = performance_monitor.get_all_stats()

        for component_key, stats in all_stats.items():
            if stats:  # Only include if has data
                snapshot["components"][component_key] = {
                    "count": stats.get("count", 0),
                    "success_rate": stats.get("success_rate", 0.0),
                    "latency": {
                        "mean": stats["latency"]["mean"],
                        "median": stats["latency"]["median"],
                        "p95": stats["latency"]["p95"],
                        "p99": stats["latency"]["p99"],
                        "min": stats["latency"]["min"],
                        "max": stats["latency"]["max"],
                    }
                }

        return snapshot

    def write_to_file(self, snapshot: Dict[str, Any]) -> None:
        """Write snapshot to JSONL file"""
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    def log_summary(self, snapshot: Dict[str, Any]) -> None:
        """Log human-readable summary to stdout"""
        components = snapshot.get("components", {})

        if not components:
            logger.info("[Metrics] No data collected yet")
            return

        logger.info("=" * 60)
        logger.info("[Metrics Summary] %s", snapshot["timestamp"])
        logger.info("=" * 60)

        for component_key, stats in components.items():
            logger.info("\n📊 %s:", component_key)
            logger.info("  Requests: %d", stats["count"])
            logger.info("  Success Rate: %.1f%%", stats["success_rate"] * 100)
            logger.info("  Latency (ms):")
            logger.info("    Mean: %.1f", stats["latency"]["mean"])
            logger.info("    P95: %.1f", stats["latency"]["p95"])
            logger.info("    P99: %.1f", stats["latency"]["p99"])
            logger.info("    Range: %.1f - %.1f",
                       stats["latency"]["min"],
                       stats["latency"]["max"])

        logger.info("=" * 60)

    async def export_loop(self) -> None:
        """Background task that exports metrics periodically"""
        interval = FeatureFlags.metrics_export_interval()
        logger.info("[MetricsExporter] Started (export every %ds)", interval)

        while self._running:
            try:
                snapshot = self.export_snapshot()

                # Write to file
                self.write_to_file(snapshot)

                # Log summary
                self.log_summary(snapshot)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error("[MetricsExporter] Export failed: %s", e)
                await asyncio.sleep(interval)

    def start(self) -> None:
        """Start the background export task"""
        if not FeatureFlags.performance_monitoring_enabled():
            logger.info("[MetricsExporter] Disabled by feature flag")
            return

        if self._running:
            logger.warning("[MetricsExporter] Already running")
            return

        self._running = True
        self._task = asyncio.create_task(self.export_loop())
        logger.info("[MetricsExporter] Started")

    def stop(self) -> None:
        """Stop the background export task"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()

        logger.info("[MetricsExporter] Stopped")

    def export_now(self) -> Dict[str, Any]:
        """Force immediate export and return snapshot"""
        snapshot = self.export_snapshot()
        self.write_to_file(snapshot)
        self.log_summary(snapshot)
        return snapshot


# Global singleton instance
metrics_exporter = MetricsExporter()


# Convenience functions for application startup/shutdown
def start_metrics_export():
    """Start metrics export background task (call on app startup)"""
    metrics_exporter.start()


def stop_metrics_export():
    """Stop metrics export background task (call on app shutdown)"""
    metrics_exporter.stop()


def export_metrics_now() -> Dict[str, Any]:
    """Force immediate metrics export"""
    return metrics_exporter.export_now()
