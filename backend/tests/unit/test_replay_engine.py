import json
import pytest

from core.redis import InMemoryCache


@pytest.fixture()
def redis_cache():
    return InMemoryCache()


@pytest.fixture()
def patch_redis(monkeypatch, redis_cache):
    async def _fake_get_redis():
        return redis_cache
    monkeypatch.setattr("core.redis.get_redis", _fake_get_redis)
    return redis_cache


def _event(session_id, turn_id, payload=None):
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "timestamp": 123.0 + turn_id,
        "state": payload or {"turn_id": turn_id, "stage": "OPENING"},
    }


@pytest.mark.asyncio
async def test_replay_from_snapshot_and_stream(patch_redis):
    from app.engine.context.replay_engine import ReplayEngine

    engine = ReplayEngine()
    await engine.save_snapshot("s1", {"turn_id": 2, "stage": "OPENING"})

    await patch_redis.xadd(
        "stream:sales_state",
        {"data": json.dumps(_event("s1", 3))},
    )
    await patch_redis.xadd(
        "stream:sales_state",
        {"data": json.dumps(_event("s1", 4, {"turn_id": 4, "stage": "NEEDS_DISCOVERY"}))},
    )

    state = await engine.replay("s1")
    assert state["turn_id"] == 4
    assert state["stage"] == "NEEDS_DISCOVERY"


@pytest.mark.asyncio
async def test_replay_idempotent_on_duplicate_turns(patch_redis):
    from app.engine.context.replay_engine import ReplayEngine

    engine = ReplayEngine()
    await engine.save_snapshot("s1", {"turn_id": 1, "stage": "OPENING"})

    event = _event("s1", 2, {"turn_id": 2, "stage": "PRODUCT_INTRO"})
    await patch_redis.xadd("stream:sales_state", {"data": json.dumps(event)})
    await patch_redis.xadd("stream:sales_state", {"data": json.dumps(event)})

    state = await engine.replay("s1")
    assert state["turn_id"] == 2
    assert state["stage"] == "PRODUCT_INTRO"


@pytest.mark.asyncio
async def test_replay_orders_out_of_order_events(patch_redis):
    from app.engine.context.replay_engine import ReplayEngine

    engine = ReplayEngine()
    await patch_redis.xadd(
        "stream:sales_state",
        {"data": json.dumps(_event("s1", 3, {"turn_id": 3, "stage": "PRODUCT_INTRO"}))},
    )
    await patch_redis.xadd(
        "stream:sales_state",
        {"data": json.dumps(_event("s1", 2, {"turn_id": 2, "stage": "NEEDS_DISCOVERY"}))},
    )

    state = await engine.replay("s1")
    assert state["turn_id"] == 3
    assert state["stage"] == "PRODUCT_INTRO"
