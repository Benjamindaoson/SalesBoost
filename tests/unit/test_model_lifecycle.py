import pytest

from app.infra.llm.registry import ModelMetadata


def _make_meta(provider="p", model="m", quality=8.0, success=0.95, calls=300):
    return ModelMetadata(
        provider=provider,
        model_name=model,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        quality_score=quality,
        success_rate=success,
        total_calls=calls,
    )


def test_effective_score_computation():
    from app.infra.llm.lifecycle import compute_effective_score

    meta = _make_meta(quality=8.0, success=0.9, calls=500)
    score = compute_effective_score(meta, intent_weight=1.2, success_rate=0.9)
    assert round(score, 3) == round(8.0 * 1.2 * 0.9, 3)


def test_promote_shadow_to_candidate():
    from app.infra.llm.lifecycle import evaluate_lifecycle

    meta = _make_meta(provider="p", model="shadow", quality=8.5, success=0.95, calls=400)
    meta.status = "SHADOW"

    decisions = evaluate_lifecycle(
        {"p/shadow": meta},
        primary_key="p/primary",
        effective_scores={"p/shadow": 7.5, "p/primary": 6.0},
    )

    assert decisions["p/shadow"] == "PROMOTE_CANDIDATE"


def test_promote_candidate_to_primary():
    from app.infra.llm.lifecycle import evaluate_lifecycle

    candidate = _make_meta(provider="p", model="candidate", quality=9.0, success=0.96, calls=800)
    candidate.status = "CANDIDATE"
    primary = _make_meta(provider="p", model="primary", quality=7.0, success=0.9, calls=1000)
    primary.status = "PRIMARY"

    decisions = evaluate_lifecycle(
        {"p/candidate": candidate, "p/primary": primary},
        primary_key="p/primary",
        effective_scores={"p/candidate": 8.2, "p/primary": 6.5},
    )

    assert decisions["p/candidate"] == "PROMOTE_PRIMARY"
    assert decisions["p/primary"] == "DEMOTE_ACTIVE"


def test_auto_quarantine_on_low_success():
    from app.infra.llm.lifecycle import evaluate_lifecycle

    meta = _make_meta(provider="p", model="bad", quality=6.0, success=0.5, calls=500)
    meta.status = "ACTIVE"

    decisions = evaluate_lifecycle(
        {"p/bad": meta},
        primary_key="p/primary",
        effective_scores={"p/bad": 2.0},
    )

    assert decisions["p/bad"] == "QUARANTINE"


def test_anomaly_detection_drop():
    from app.infra.llm.lifecycle import detect_anomalies

    history = [9.5, 9.2, 8.9, 6.0, 5.5]
    anomalies = detect_anomalies(history, min_drop=2.0)
    assert anomalies["severity"] == "HIGH"
