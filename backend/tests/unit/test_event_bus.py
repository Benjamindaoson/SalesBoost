import pytest
import asyncio
from app.infra.events.bus import MemoryEventBus
from app.infra.events.schemas import EventBase

class MockPayload(EventBase):
    data: str
    event_id: str = "test-id"

@pytest.mark.asyncio
async def test_pub_sub():
    test_bus = MemoryEventBus()
    received = []

    @test_bus.subscribe("test_event")
    async def handler(payload):
        received.append(payload)

    payload = MockPayload(data="hello", session_id="sess1", user_id="user1")
    await test_bus.publish("test_event", payload)

    assert len(received) == 1
    assert received[0].data == "hello"

@pytest.mark.asyncio
async def test_request_response():
    test_bus = MemoryEventBus()
    
    @test_bus.subscribe("ping")
    async def pong_handler(payload):
        # Respond by publishing to the response topic logic inside request handles this?
        # No, the request method waits for a message on `response.event_type.event_id`.
        # So the handler needs to publish back to that topic?
        # Wait, let's check bus.py request implementation.
        # It subscribes to `response.event_type.event_id`.
        # So the handler MUST publish to that specific topic.
        # But how does the handler know the topic?
        # The payload usually carries the return address or ID.
        # My current request implementation generates `response_event_type = f"response.{event_type}.{event_id}"`.
        # So the handler implies knowledge of this convention or the payload must carry it.
        # Let's refine the handler to publish back.
        
        event_id = getattr(payload, 'event_id')
        response_topic = f"response.ping.{event_id}"
        await test_bus.publish(response_topic, "pong")

    payload = MockPayload(data="ping", session_id="sess1", user_id="user1")
    
    # We need to run the subscriber in background? No, publish triggers it.
    # But request method waits.
    # The handler is triggered by the publish inside request.
    
    response = await test_bus.request("ping", payload, timeout=1.0)
    assert response == "pong"

@pytest.mark.asyncio
async def test_concurrency():
    test_bus = MemoryEventBus()
    results = []

    @test_bus.subscribe("concurrent_event")
    async def slow_handler1(payload):
        await asyncio.sleep(0.1)
        results.append(1)

    @test_bus.subscribe("concurrent_event")
    async def fast_handler2(payload):
        results.append(2)

    payload = MockPayload(data="go", session_id="sess1", user_id="user1")
    await test_bus.publish("concurrent_event", payload)

    # Since we use asyncio.gather, order of completion isn't strictly guaranteed to be "fast then slow" 
    # in the list append if they are concurrent, but fast should likely finish first.
    # However, gather waits for ALL.
    assert len(results) == 2
    assert 1 in results
    assert 2 in results
