
import pytest
import asyncio
from cognitive.brain.state.write_ahead_log import wal_manager
from core.redis import InMemoryCache, get_redis

@pytest.mark.asyncio
async def test_wal_operations():
    # 1. Ensure clean state with Mock Backend
    wal_manager.redis = InMemoryCache()
    wal_manager._redis_initialized = True
    
    session_id = "test_wal_session"
    
    # 2. Log events
    msg_id1 = await wal_manager.log_event(session_id, 1, "USER_INPUT", {"msg": "Hello"})
    assert msg_id1 != "0-0"
    
    msg_id2 = await wal_manager.log_event(session_id, 1, "NPC_REPLY", {"msg": "Hi"})
    assert msg_id2 != "0-0"
    
    # 3. Read events
    events = await wal_manager.get_events(session_id)
    assert len(events) == 2
    assert events[0]["type"] == "USER_INPUT"
    assert events[0]["payload"]["msg"] == "Hello"
    assert events[1]["type"] == "NPC_REPLY"
    assert events[1]["payload"]["msg"] == "Hi"
    
    # 4. Clear events
    await wal_manager.clear_events(session_id)
    events_after = await wal_manager.get_events(session_id)
    # InMemoryCache delete removes the key, so xrange returns []
    assert len(events_after) == 0

if __name__ == "__main__":
    asyncio.run(test_wal_operations())
