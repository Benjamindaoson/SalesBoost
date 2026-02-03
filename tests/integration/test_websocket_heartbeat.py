"""
Integration tests for WebSocket heartbeat and session suspension.
Tests bidirectional ping/pong, timeout detection, and state snapshot creation.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.infra.websocket.heartbeat_manager import HeartbeatManager, HeartbeatConfig


@pytest.mark.asyncio
async def test_heartbeat_monitoring_start_stop():
    """Test starting and stopping heartbeat monitoring."""
    manager = HeartbeatManager()
    websocket = Mock()
    websocket.send_json = AsyncMock()
    
    session_id = "test_session_123"
    
    # Start monitoring
    await manager.start_monitoring(session_id, websocket)
    
    # Verify session is being monitored
    health = manager.get_session_health(session_id)
    assert health is not None
    assert health.session_id == session_id
    assert health.missed_pongs == 0
    assert not health.is_suspended
    
    # Stop monitoring
    await manager.stop_monitoring(session_id)
    
    # Verify session is no longer monitored
    health = manager.get_session_health(session_id)
    assert health is None


@pytest.mark.asyncio
async def test_pong_response_recording():
    """Test recording pong responses."""
    manager = HeartbeatManager()
    websocket = Mock()
    websocket.send_json = AsyncMock()
    
    session_id = "test_session_123"
    
    await manager.start_monitoring(session_id, websocket)
    
    # Record pong
    await manager.record_pong(session_id)
    
    # Verify pong was recorded
    health = manager.get_session_health(session_id)
    assert health.missed_pongs == 0
    
    await manager.stop_monitoring(session_id)


@pytest.mark.asyncio
async def test_heartbeat_timeout_detection():
    """Test detection of heartbeat timeout."""
    config = HeartbeatConfig(
        ping_interval=0.1,  # 100ms
        pong_timeout=0.05,  # 50ms
        max_missed_pongs=2
    )
    manager = HeartbeatManager(config)
    
    websocket = Mock()
    websocket.send_json = AsyncMock()
    
    session_id = "test_session_123"
    suspension_called = asyncio.Event()
    suspension_reason = None
    
    async def on_suspend(sid, reason):
        nonlocal suspension_reason
        suspension_reason = reason
        suspension_called.set()
    
    # Start monitoring
    await manager.start_monitoring(session_id, websocket, on_suspend)
    
    # Wait for suspension (should happen after 2 missed pongs)
    try:
        await asyncio.wait_for(suspension_called.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Suspension callback was not called within timeout")
    
    # Verify suspension occurred
    assert suspension_reason is not None
    assert "missed pongs" in suspension_reason.lower()


@pytest.mark.asyncio
async def test_ping_send_failure_triggers_suspension():
    """Test that ping send failure triggers suspension."""
    config = HeartbeatConfig(ping_interval=0.1)
    manager = HeartbeatManager(config)
    
    websocket = Mock()
    websocket.send_json = AsyncMock(side_effect=Exception("Connection lost"))
    
    session_id = "test_session_123"
    suspension_called = asyncio.Event()
    
    async def on_suspend(sid, reason):
        suspension_called.set()
    
    await manager.start_monitoring(session_id, websocket, on_suspend)
    
    # Wait for suspension
    try:
        await asyncio.wait_for(suspension_called.wait(), timeout=0.5)
    except asyncio.TimeoutError:
        pytest.fail("Suspension callback was not called after ping failure")


@pytest.mark.asyncio
async def test_multiple_sessions_independent_monitoring():
    """Test that multiple sessions are monitored independently."""
    manager = HeartbeatManager()
    
    websocket1 = Mock()
    websocket1.send_json = AsyncMock()
    websocket2 = Mock()
    websocket2.send_json = AsyncMock()
    
    session1 = "session_1"
    session2 = "session_2"
    
    # Start monitoring both sessions
    await manager.start_monitoring(session1, websocket1)
    await manager.start_monitoring(session2, websocket2)
    
    # Verify both are monitored
    assert manager.get_session_health(session1) is not None
    assert manager.get_session_health(session2) is not None
    
    # Record pong for session1 only
    await manager.record_pong(session1)
    
    # Verify independent state
    health1 = manager.get_session_health(session1)
    health2 = manager.get_session_health(session2)
    
    assert health1.missed_pongs == 0
    # session2 hasn't received pong yet, but hasn't timed out either
    
    # Cleanup
    await manager.stop_monitoring(session1)
    await manager.stop_monitoring(session2)


@pytest.mark.asyncio
async def test_heartbeat_with_regular_pongs():
    """Test that regular pongs prevent suspension."""
    config = HeartbeatConfig(
        ping_interval=0.1,
        pong_timeout=0.05,
        max_missed_pongs=3
    )
    manager = HeartbeatManager(config)
    
    websocket = Mock()
    websocket.send_json = AsyncMock()
    
    session_id = "test_session_123"
    suspension_called = False
    
    async def on_suspend(sid, reason):
        nonlocal suspension_called
        suspension_called = True
    
    await manager.start_monitoring(session_id, websocket, on_suspend)
    
    # Send pongs regularly
    for _ in range(5):
        await asyncio.sleep(0.08)  # Slightly less than ping_interval
        await manager.record_pong(session_id)
    
    # Verify no suspension occurred
    assert not suspension_called
    health = manager.get_session_health(session_id)
    assert health is not None
    assert not health.is_suspended
    
    await manager.stop_monitoring(session_id)


@pytest.mark.asyncio
async def test_session_health_status():
    """Test session health status tracking."""
    manager = HeartbeatManager()
    websocket = Mock()
    websocket.send_json = AsyncMock()
    
    session_id = "test_session_123"
    
    # Before monitoring
    assert manager.get_session_health(session_id) is None
    
    # Start monitoring
    await manager.start_monitoring(session_id, websocket)
    
    health = manager.get_session_health(session_id)
    assert health.session_id == session_id
    assert health.last_ping_sent > 0
    assert health.last_pong_received > 0
    assert health.missed_pongs == 0
    assert not health.is_suspended
    assert health.suspension_reason is None
    
    await manager.stop_monitoring(session_id)
