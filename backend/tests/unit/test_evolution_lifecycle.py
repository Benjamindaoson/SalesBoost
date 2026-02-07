import pytest

from app.infra.llm.registry import ModelMetadata


class _DummyRedis:
    async def lrange(self, key: str, start: int, end: int):
        if "history" in key:
            return ["1:9.5", "2:9.2", "3:6.8"]
        if "success" in key:
            return ["1"] * 8 + ["0"] * 2
        return []

    async def hset(self, key: str, mapping):
        return True


@pytest.mark.asyncio
async def test_evolution_trends_contains_lifecycle_fields(monkeypatch):
    from app.api.endpoints import evolution
    from app.infra.llm import registry
    old_models = dict(registry.model_registry._models)
    old_intents = dict(registry.model_registry._intent_counts)

    meta = ModelMetadata(
        provider="p",
        model_name="m",
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        quality_score=8.0,
        success_rate=0.9,
        total_calls=500,
    )
    meta.status = "ACTIVE"

    try:
        registry.model_registry._models = {"p/m": meta}
        registry.model_registry._intent_counts = {"p/m": {"LOGIC": 10}}

        dummy = _DummyRedis()
        monkeypatch.setattr(evolution, "redis_client", dummy)
        monkeypatch.setattr(registry, "redis_client", dummy)

        resp = await evolution.get_evolution_trends()
        assert resp.trends[0].effective_score > 0
        assert resp.trends[0].intent_weight >= 1.0
        assert resp.trends[0].success_rate > 0
        assert resp.trends[0].lifecycle_action in {"KEEP", "PROMOTE_CANDIDATE", "PROMOTE_PRIMARY", "DEMOTE_ACTIVE", "QUARANTINE"}
        assert resp.trends[0].anomaly_severity in {"NONE", "MEDIUM", "HIGH"}
        assert resp.lifecycle_rules["promote_ratio"] >= 1.0
        assert resp.anomaly_rules["min_drop"] >= 1.0
    finally:
        registry.model_registry._models = old_models
        registry.model_registry._intent_counts = old_intents


def test_registry_primary_selection():
    from app.infra.llm.registry import ModelRegistry

    reg = ModelRegistry()
    # Ensure there is a primary selected
    primary = reg.get_primary_key()
    assert primary is not None
