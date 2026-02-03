"""
A/B Testing Framework for Intent Classifiers and Coordinators
"""
import random
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import json

from app.engine.intent.production_classifier import ProductionIntentClassifier


@dataclass
class ABTestMetrics:
    """Metrics for A/B testing"""
    model_version: str
    session_id: str
    intent: str
    confidence: float
    latency_ms: float
    context_enhanced: bool


class ABTestManager:
    """
    A/B Testing Manager

    Supports:
    - Consistent hashing (same user always gets same variant)
    - Traffic split control
    - Metrics collection
    """

    def __init__(self, traffic_split: float = 0.1):
        """
        Args:
            traffic_split: Percentage of traffic for variant B (0-1)
        """
        self.traffic_split = traffic_split
        self.model_a = ProductionIntentClassifier("models/intent_classifier.bin")
        self.model_b = ProductionIntentClassifier("models/intent_classifier.bin")  # Could be different
        self.metrics_buffer = []

    def _assign_variant(self, session_id: str) -> str:
        """Consistent hashing for variant assignment"""
        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        return "B" if (hash_value % 100) < (self.traffic_split * 100) else "A"

    async def classify(
        self,
        message: str,
        context: Dict[str, Any],
        session_id: str
    ):
        """Classify with A/B testing"""
        import time

        variant = self._assign_variant(session_id)
        model = self.model_b if variant == "B" else self.model_a

        start = time.time()
        result = await model.classify(message, context)
        latency_ms = (time.time() - start) * 1000

        # Collect metrics
        self.metrics_buffer.append(ABTestMetrics(
            model_version=variant,
            session_id=session_id,
            intent=result.intent,
            confidence=result.confidence,
            latency_ms=latency_ms,
            context_enhanced=result.context_enhanced
        ))

        # Flush metrics periodically
        if len(self.metrics_buffer) >= 100:
            await self._flush_metrics()

        return result

    async def _flush_metrics(self):
        """Flush metrics to storage"""
        if not self.metrics_buffer:
            return

        # Save to file (or send to analytics service)
        with open("logs/ab_test_metrics.jsonl", "a") as f:
            for metric in self.metrics_buffer:
                f.write(json.dumps(asdict(metric)) + "\n")

        self.metrics_buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get current A/B test statistics"""
        if not self.metrics_buffer:
            return {}

        a_metrics = [m for m in self.metrics_buffer if m.model_version == "A"]
        b_metrics = [m for m in self.metrics_buffer if m.model_version == "B"]

        return {
            "variant_A": {
                "count": len(a_metrics),
                "avg_confidence": sum(m.confidence for m in a_metrics) / len(a_metrics) if a_metrics else 0,
                "avg_latency_ms": sum(m.latency_ms for m in a_metrics) / len(a_metrics) if a_metrics else 0
            },
            "variant_B": {
                "count": len(b_metrics),
                "avg_confidence": sum(m.confidence for m in b_metrics) / len(b_metrics) if b_metrics else 0,
                "avg_latency_ms": sum(m.latency_ms for m in b_metrics) / len(b_metrics) if b_metrics else 0
            }
        }
