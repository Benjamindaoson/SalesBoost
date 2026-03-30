import pytest


@pytest.mark.asyncio
async def test_lifecycle_job_publishes_audit(monkeypatch):
    from app.engine.coordinator.lifecycle_job import LifecycleJob
    from app.infra.llm.registry import ModelMetadata

    published = []

    class DummyBus:
        async def publish(self, event_type, payload):
            published.append((event_type, payload))

    class DummyRegistry:
        def __init__(self):
            self._models = {
                "p/m": ModelMetadata(
                    provider="p",
                    model_name="m",
                    input_cost_per_1k=0.001,
                    output_cost_per_1k=0.002,
                    quality_score=8.5,
                    success_rate=0.95,
                    total_calls=500,
                )
            }

        def list_models(self):
            return list(self._models.values())

        def get_primary_key(self):
            return None

        async def get_success_rate(self, provider, model_name):
            return 0.95

        def get_intent_weight(self, provider, model_name):
            return 1.2

        async def apply_lifecycle_actions(self, actions, primary_key):
            self._last_actions = actions

        async def set_lifecycle_action(self, key, action):
            self._last_action = action

        async def set_anomaly(self, key, anomaly):
            self._last_anomaly = anomaly

    def _fake_evaluate(models, primary_key, effective_scores, **kwargs):
        return {"p/m": "PROMOTE_CANDIDATE"}

    def _fake_anomaly(history, min_drop=2.0):
        return {"severity": "HIGH", "reason": "score_drop", "drop": "2.5"}

    monkeypatch.setattr("app.engine.coordinator.lifecycle_job.bus", DummyBus())
    monkeypatch.setattr("app.engine.coordinator.lifecycle_job.evaluate_lifecycle", _fake_evaluate)
    monkeypatch.setattr("app.engine.coordinator.lifecycle_job.detect_anomalies", _fake_anomaly)

    job = LifecycleJob(registry=DummyRegistry())
    await job.run_once()

    assert published
    assert any(p[1].details.get("action") == "PROMOTE_CANDIDATE" for p in published)
