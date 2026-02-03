from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List

from core.config import get_settings
from app.infra.cache.redis_client import redis_client
from app.infra.events.bus import bus
from app.infra.events.schemas import AuditEventPayload, EventType
from app.infra.llm.lifecycle import compute_effective_score, detect_anomalies, evaluate_lifecycle
from app.infra.llm.registry import ModelMetadata, model_registry

logger = logging.getLogger(__name__)


class LifecycleJob:
    """Periodic lifecycle evaluator for model promotion/eviction/anomaly reporting."""

    def __init__(
        self,
        registry=model_registry,
        interval_seconds: float | None = None,
        anomaly_min_drop: float | None = None,
    ) -> None:
        settings = get_settings()
        self._registry = registry
        self._interval = interval_seconds if interval_seconds is not None else settings.LIFECYCLE_JOB_INTERVAL_SECONDS
        self._anomaly_min_drop = (
            anomaly_min_drop if anomaly_min_drop is not None else settings.LIFECYCLE_ANOMALY_MIN_DROP
        )
        self._running = False

    async def run_forever(self) -> None:
        """Run lifecycle evaluation in a periodic loop."""
        self._running = True
        while self._running:
            try:
                await self.run_once()
            except Exception as exc:
                logger.error("LifecycleJob run failed: %s", exc)
            await asyncio.sleep(self._interval)

    async def stop(self) -> None:
        """Stop the periodic lifecycle loop."""
        self._running = False

    async def run_once(self) -> None:
        """Evaluate lifecycle decisions once and publish audit events."""
        models = self._registry.list_models()
        if not models:
            return

        effective_scores: Dict[str, float] = {}
        for meta in models:
            key = f"{meta.provider}/{meta.model_name}"
            intent_weight = self._registry.get_intent_weight(meta.provider, meta.model_name)
            success_rate = await self._registry.get_success_rate(meta.provider, meta.model_name)
            effective_scores[key] = compute_effective_score(meta, intent_weight, success_rate)

        primary_key = self._registry.get_primary_key()
        actions = evaluate_lifecycle(
            {f"{m.provider}/{m.model_name}": m for m in models},
            primary_key=primary_key,
            effective_scores=effective_scores,
        )
        await self._registry.apply_lifecycle_actions(actions, primary_key)

        for key, action in actions.items():
            await self._registry.set_lifecycle_action(key, action)

        for meta in models:
            key = f"{meta.provider}/{meta.model_name}"
            history = await self._load_history(meta)
            anomaly = detect_anomalies(history, min_drop=self._anomaly_min_drop)
            await self._registry.set_anomaly(key, anomaly)

            action = actions.get(key, "KEEP")
            if action != "KEEP" or anomaly.get("severity") not in {"NONE", None}:
                await self._publish_audit(meta, action, effective_scores.get(key, 0.0), anomaly, primary_key)

    async def _load_history(self, meta: ModelMetadata) -> List[float]:
        """Load recent score history for a model from Redis."""
        history: List[float] = []
        try:
            redis_key = f"salesboost:model:history:{meta.provider}/{meta.model_name}"
            raw_history = await redis_client.lrange(redis_key, -100, -1)
            if raw_history:
                for item in raw_history:
                    try:
                        ts, score = item.split(":")
                        history.append(float(score))
                    except ValueError:
                        continue
        except Exception:
            return history
        return history

    async def _publish_audit(
        self,
        meta: ModelMetadata,
        action: str,
        effective_score: float,
        anomaly: Dict[str, str],
        primary_key: str | None,
    ) -> None:
        """Publish lifecycle actions/anomalies to the audit bus."""
        severity = "medium"
        if action == "QUARANTINE" or anomaly.get("severity") == "HIGH":
            severity = "high"

        payload = AuditEventPayload(
            event_id=str(uuid.uuid4()),
            session_id=None,
            user_id="system",
            tenant_id=None,
            reason="model_lifecycle",
            severity=severity,
            details={
                "model_key": f"{meta.provider}/{meta.model_name}",
                "action": action,
                "effective_score": effective_score,
                "anomaly": anomaly,
                "primary_key": primary_key,
            },
        )
        await bus.publish(EventType.MODEL_LIFECYCLE_DECISION, payload)
