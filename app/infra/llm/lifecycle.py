"""Model lifecycle evaluation and anomaly detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.infra.llm.registry import ModelMetadata


@dataclass
class AnomalyReport:
    severity: str
    reason: str
    drop: float


def compute_effective_score(
    meta: ModelMetadata,
    intent_weight: float,
    success_rate: float,
) -> float:
    """Compute business-aligned effective score."""
    return round(meta.quality_score * intent_weight * success_rate, 3)


def detect_anomalies(history: List[float], min_drop: float = 2.0) -> Dict[str, str]:
    """Detect sudden drops in model score history."""
    if len(history) < 3:
        return {"severity": "NONE", "reason": "insufficient_history", "drop": "0.0"}
    peak = max(history[:-1])
    latest = history[-1]
    drop = round(peak - latest, 3)
    if drop >= min_drop:
        return {"severity": "HIGH", "reason": "score_drop", "drop": str(drop)}
    if drop >= min_drop * 0.5:
        return {"severity": "MEDIUM", "reason": "score_soft_drop", "drop": str(drop)}
    return {"severity": "NONE", "reason": "stable", "drop": str(drop)}


def evaluate_lifecycle(
    models: Dict[str, ModelMetadata],
    primary_key: Optional[str],
    effective_scores: Dict[str, float],
    promote_ratio: float = 1.15,
    min_calls: int = 200,
    min_success_rate: float = 0.9,
    quarantine_success_rate: float = 0.7,
) -> Dict[str, str]:
    """
    Evaluate lifecycle decisions.

    Returns mapping: model_key -> action
    Actions: KEEP, PROMOTE_CANDIDATE, PROMOTE_PRIMARY, DEMOTE_ACTIVE, QUARANTINE
    """
    decisions: Dict[str, str] = {}
    primary_score = effective_scores.get(primary_key or "", 0.0)

    for key, meta in models.items():
        score = effective_scores.get(key, 0.0)
        action = "KEEP"

        if meta.success_rate < quarantine_success_rate:
            decisions[key] = "QUARANTINE"
            continue

        if meta.status == "SHADOW":
            if score >= primary_score * promote_ratio and meta.total_calls >= min_calls and meta.success_rate >= min_success_rate:
                action = "PROMOTE_CANDIDATE"
        elif meta.status == "CANDIDATE":
            if score >= primary_score * promote_ratio and meta.total_calls >= min_calls * 2 and meta.success_rate >= min_success_rate:
                action = "PROMOTE_PRIMARY"
        elif meta.status == "PRIMARY":
            if primary_score > 0 and score < primary_score * 0.85:
                action = "DEMOTE_ACTIVE"

        decisions[key] = action

    promoted_primary = [k for k, a in decisions.items() if a == "PROMOTE_PRIMARY"]
    if promoted_primary and primary_key and primary_key in decisions:
        decisions[primary_key] = "DEMOTE_ACTIVE"

    return decisions
