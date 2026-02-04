from typing import List, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from app.infra.llm.registry import model_registry
from app.infra.llm.lifecycle import compute_effective_score, detect_anomalies
from app.infra.llm.fast_intent import fast_intent_classifier
from app.infra.cache.redis_client import redis_client

router = APIRouter()

class ScorePoint(BaseModel):
    timestamp: float
    score: float

class ModelTrend(BaseModel):
    provider: str
    model_name: str
    current_score: float
    effective_score: float
    intent_weight: float
    success_rate: float
    lifecycle_action: str
    anomaly_severity: str
    anomaly_reason: str
    negative_streak: int
    total_calls: int
    status: str # "ACTIVE" or "QUARANTINED"
    history: List[ScorePoint]

class EvolutionResponse(BaseModel):
    trends: List[ModelTrend]
    intent_distribution: Dict[str, int]
    lifecycle_rules: Dict[str, float]
    anomaly_rules: Dict[str, float]

@router.get("/evolution-trends", response_model=EvolutionResponse)
async def get_evolution_trends():
    """
    Get 24h score trends and evolution metrics for all models.
    """
    models = model_registry.list_models()
    trends = []

    effective_scores: Dict[str, float] = {}
    for m in models:
        intent_weight = model_registry.get_intent_weight(m.provider, m.model_name)
        success_rate = await model_registry.get_success_rate(m.provider, m.model_name)
        effective_scores[f"{m.provider}/{m.model_name}"] = compute_effective_score(
            m, intent_weight=intent_weight, success_rate=success_rate
        )

    for m in models:
        # Determine Status
        status = "ACTIVE"
        if m.negative_feedback_streak >= 5:
            status = "QUARANTINED"
        
        # Fetch History from Redis
        history = []
        try:
            redis_key = f"salesboost:model:history:{m.provider}/{m.model_name}"
            # Get last 100 entries for trend
            raw_history = await redis_client.lrange(redis_key, -100, -1)
            if raw_history:
                for item in raw_history:
                    try:
                        ts, score = item.split(":")
                        history.append(ScorePoint(timestamp=float(ts), score=float(score)))
                    except ValueError:
                        continue
        except Exception:
            # If Redis fails or history missing, return empty history
            pass

        intent_weight = model_registry.get_intent_weight(m.provider, m.model_name)
        success_rate = await model_registry.get_success_rate(m.provider, m.model_name)
        effective_score = effective_scores.get(f"{m.provider}/{m.model_name}", 0.0)
        anomaly = model_registry.get_anomaly(f"{m.provider}/{m.model_name}")
        if anomaly.get("severity") in {None, "NONE"} and history:
            anomaly = detect_anomalies([p.score for p in history], min_drop=2.0)

        trends.append(ModelTrend(
            provider=m.provider,
            model_name=m.model_name,
            current_score=m.quality_score,
            effective_score=effective_score,
            intent_weight=intent_weight,
            success_rate=success_rate,
            lifecycle_action=model_registry.get_lifecycle_action(f"{m.provider}/{m.model_name}"),
            anomaly_severity=anomaly.get("severity", "NONE"),
            anomaly_reason=anomaly.get("reason", "stable"),
            negative_streak=m.negative_feedback_streak,
            total_calls=m.total_calls,
            status=m.status or status,
            history=history
        ))

    return EvolutionResponse(
        trends=trends,
        intent_distribution=fast_intent_classifier.get_stats(),
        lifecycle_rules={
            "promote_ratio": 1.15,
            "min_calls": 200,
            "min_success_rate": 0.9,
            "quarantine_success_rate": 0.7,
        },
        anomaly_rules={"min_drop": 2.0},
    )
