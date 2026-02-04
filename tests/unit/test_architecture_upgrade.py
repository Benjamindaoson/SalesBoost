import pytest
import asyncio
from app.infra.events.bus import bus, MemoryEventBus
from app.infra.events.schemas import EventType, KnowledgeEventPayload, EvaluationEventPayload
from app.services.knowledge_sync import sync_chroma, sync_bm25
from app.services.consistency_checker import check_consistency, handle_retry

# Use MemoryEventBus for unit tests to avoid needing real Redis
bus.__class__ = MemoryEventBus
# Re-init to clear subscribers
bus.__init__()

@pytest.mark.asyncio
async def test_hybrid_search_sync():
    # Register subscribers manually since we re-inited bus
    bus.subscribe(EventType.KNOWLEDGE_UPDATED)(sync_chroma)
    bus.subscribe(EventType.KNOWLEDGE_UPDATED)(sync_bm25)
    
    payload = KnowledgeEventPayload(
        event_id="evt1",
        document_id="doc1",
        content_hash="hash1",
        content="Important sales data"
    )
    
    # We can't easily assert internal state of services here without mocking, 
    # but we can ensure no exceptions are raised and flow works.
    await bus.publish(EventType.KNOWLEDGE_UPDATED, payload)
    
    # If we reached here, both subscribers ran.

@pytest.mark.asyncio
async def test_consistency_retry_flow():
    # Register subscribers
    bus.subscribe(EventType.EVALUATION_COMPLETED)(check_consistency)
    bus.subscribe(EventType.RETRY_EVALUATION)(handle_retry)
    
    # 1. Publish inconsistent evaluation
    bad_payload = EvaluationEventPayload(
        event_id="eval1",
        evaluation_id="eval_obj_1",
        target_content="speech",
        score=9.0,
        comments="This was bad performance."
    )
    
    # We need to capture the retry event to verify it happened.
    # We can add a spy subscriber.
    retry_events = []
    @bus.subscribe(EventType.RETRY_EVALUATION)
    async def spy_retry(payload):
        retry_events.append(payload)

    completed_events = []
    @bus.subscribe(EventType.EVALUATION_COMPLETED)
    async def spy_completed(payload):
        completed_events.append(payload)

    await bus.publish(EventType.EVALUATION_COMPLETED, bad_payload)
    
    # Allow async tasks to propagate
    await asyncio.sleep(0.5)
    
    # Check if retry was triggered
    assert len(retry_events) > 0
    assert retry_events[0].retry_count == 1
    assert "inconsistent" in retry_events[0].correction_prompt.lower() or "align" in retry_events[0].correction_prompt.lower()
    
    # The retry handler should have published a NEW completion event
    # Initial one + corrected one = 2
    assert len(completed_events) >= 2
    
    # Verify the last one is corrected
    last_event = completed_events[-1]
    if isinstance(last_event, dict):
         # If using Redis it might be dict, but we are using MemoryBus so it's object usually, 
         # BUT the bus implementation wraps payload? No, memory bus passes object.
         # However, handle_retry creates a copy and modifies it.
         pass
    
    assert last_event.score < 8.0 # Should be corrected to 4.0
