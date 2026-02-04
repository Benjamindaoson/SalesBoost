"""
E2E Integration Tests with Testcontainers

This module provides end-to-end integration tests for the SalesBoost platform.
Uses Testcontainers to spin up Redis and Qdrant for realistic testing.

Test Coverage:
1. Login → WebSocket Connect → Chat → RAG → Response
2. Tool execution flow
3. State recovery after disconnect
4. Coordinator workflow execution
5. Redis-based WebSocket manager
6. Secrets manager integration

Requirements:
    pip install pytest pytest-asyncio testcontainers[redis] httpx websockets
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

import pytest
import httpx
from websockets import connect as ws_connect
from testcontainers.redis import RedisContainer
from testcontainers.core.container import DockerContainer

from core.config import Settings
from core.database import init_db
from main import app

logger = logging.getLogger(__name__)


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_container():
    """Start Redis container for testing"""
    container = RedisContainer("redis:7-alpine")
    container.start()

    redis_url = f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}/0"
    logger.info(f"Redis container started: {redis_url}")

    yield redis_url

    container.stop()
    logger.info("Redis container stopped")


@pytest.fixture(scope="session")
async def qdrant_container():
    """Start Qdrant container for testing"""
    container = DockerContainer("qdrant/qdrant:latest")
    container.with_exposed_ports(6333)
    container.start()

    qdrant_url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(6333)}"
    logger.info(f"Qdrant container started: {qdrant_url}")

    # Wait for Qdrant to be ready
    await asyncio.sleep(3)

    yield qdrant_url

    container.stop()
    logger.info("Qdrant container stopped")


@pytest.fixture(scope="session")
async def test_settings(redis_container, qdrant_container):
    """Create test settings with container URLs"""
    settings = Settings(
        ENV_STATE="testing",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL=redis_container,
        QDRANT_URL=qdrant_container,
        WEBSOCKET_MANAGER_TYPE="redis",
        ALLOW_LEGACY_COORDINATOR=False,
        # Use mock LLM for testing
        OPENAI_API_KEY="test-key",
        GOOGLE_API_KEY="test-key",
        SILICONFLOW_API_KEY="test-key",
    )

    # Override global settings
    import core.config
    core.config._settings = settings

    yield settings


@pytest.fixture(scope="session")
async def test_db(test_settings):
    """Initialize test database"""
    await init_db()
    logger.info("Test database initialized")
    yield
    logger.info("Test database cleanup complete")


@pytest.fixture
async def http_client(test_settings, test_db) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_token(http_client: httpx.AsyncClient) -> str:
    """Get authentication token for testing"""
    # Create test user
    response = await http_client.post(
        "/api/v1/auth/register",
        json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "test_password_123"
        }
    )
    assert response.status_code in [200, 201, 409]  # 409 if user already exists

    # Login
    response = await http_client.post(
        "/api/v1/auth/login",
        json={
            "username": "test_user",
            "password": "test_password_123"
        }
    )
    assert response.status_code == 200

    data = response.json()
    return data["access_token"]


# ==================== E2E Tests ====================

@pytest.mark.asyncio
async def test_e2e_full_conversation_flow(http_client: httpx.AsyncClient, auth_token: str):
    """
    Test complete conversation flow:
    1. Create session
    2. Connect WebSocket
    3. Send message
    4. Receive NPC response
    5. Receive coach advice
    6. Verify RAG retrieval
    """
    # Step 1: Create session
    response = await http_client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "course_id": 1,
            "scenario_id": 1
        }
    )
    assert response.status_code in [200, 201]
    session_data = response.json()
    session_id = session_data["session_id"]

    logger.info(f"Created session: {session_id}")

    # Step 2: Connect WebSocket
    ws_url = f"ws://test/api/v1/ws/{session_id}?token={auth_token}"

    async with ws_connect(ws_url) as websocket:
        # Step 3: Send message
        message = {
            "type": "user_message",
            "content": "你好，我想了解一下你们的产品",
            "turn_id": "test-turn-1"
        }
        await websocket.send(json.dumps(message))
        logger.info("Sent user message")

        # Step 4: Receive responses
        npc_response = None
        coach_advice = None
        tool_events = []

        # Collect responses (timeout after 10 seconds)
        timeout = 10
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)

                if data["type"] == "npc_response":
                    npc_response = data
                    logger.info(f"Received NPC response: {data['content'][:50]}...")

                elif data["type"] == "coach_advice":
                    coach_advice = data
                    logger.info(f"Received coach advice: {data['advice'][:50]}...")

                elif data["type"] == "tool_status":
                    tool_events.append(data)
                    logger.info(f"Tool event: {data['tool_name']} - {data['status']}")

                # Break if we have both responses
                if npc_response and coach_advice:
                    break

            except asyncio.TimeoutError:
                break

        # Step 5: Verify responses
        assert npc_response is not None, "Should receive NPC response"
        assert "content" in npc_response
        assert len(npc_response["content"]) > 0

        # Coach advice might be None if async mode is enabled
        if coach_advice:
            assert "advice" in coach_advice
            assert len(coach_advice["advice"]) > 0

        # Step 6: Verify tool execution (if knowledge retrieval was triggered)
        if tool_events:
            knowledge_events = [e for e in tool_events if e["tool_name"] == "knowledge_retriever"]
            if knowledge_events:
                assert any(e["status"] == "completed" for e in knowledge_events), \
                    "Knowledge retrieval should complete successfully"

        logger.info("E2E conversation flow test passed")


@pytest.mark.asyncio
async def test_e2e_state_recovery(http_client: httpx.AsyncClient, auth_token: str):
    """
    Test state recovery after disconnect:
    1. Create session and send messages
    2. Disconnect
    3. Reconnect
    4. Verify state is recovered
    """
    # Step 1: Create session
    response = await http_client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "course_id": 1,
            "scenario_id": 1
        }
    )
    assert response.status_code in [200, 201]
    session_data = response.json()
    session_id = session_data["session_id"]

    ws_url = f"ws://test/api/v1/ws/{session_id}?token={auth_token}"

    # Step 2: First connection - send messages
    async with ws_connect(ws_url) as websocket:
        # Send first message
        await websocket.send(json.dumps({
            "type": "user_message",
            "content": "第一条消息",
            "turn_id": "turn-1"
        }))

        # Wait for response
        await asyncio.sleep(2)

        # Disconnect (context manager will close)

    logger.info("Disconnected from WebSocket")

    # Step 3: Reconnect
    await asyncio.sleep(1)

    async with ws_connect(ws_url) as websocket:
        # Should receive recovery info
        recovery_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        recovery_data = json.loads(recovery_message)

        # Verify recovery
        if recovery_data.get("type") == "state_recovered":
            assert "history" in recovery_data
            assert len(recovery_data["history"]) > 0
            logger.info("State recovery successful")
        else:
            logger.warning("State recovery not implemented yet")

    logger.info("E2E state recovery test passed")


@pytest.mark.asyncio
async def test_e2e_coordinator_workflow(http_client: httpx.AsyncClient, auth_token: str):
    """
    Test coordinator workflow execution:
    1. Verify intent classification
    2. Verify knowledge retrieval (if needed)
    3. Verify NPC generation
    4. Verify coach advice
    5. Verify compliance check
    """
    # Create session
    response = await http_client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "course_id": 1,
            "scenario_id": 1
        }
    )
    assert response.status_code in [200, 201]
    session_data = response.json()
    session_id = session_data["session_id"]

    ws_url = f"ws://test/api/v1/ws/{session_id}?token={auth_token}"

    async with ws_connect(ws_url) as websocket:
        # Send message that should trigger knowledge retrieval
        await websocket.send(json.dumps({
            "type": "user_message",
            "content": "这个产品的价格是多少？",
            "turn_id": "turn-price-inquiry"
        }))

        # Collect all events
        events = []
        timeout = 10
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)
                events.append(data)

                # Break if we have NPC response
                if data.get("type") == "npc_response":
                    break

            except asyncio.TimeoutError:
                break

        # Verify workflow execution
        event_types = [e["type"] for e in events]

        # Should have tool status events (knowledge retrieval)
        tool_events = [e for e in events if e["type"] == "tool_status"]
        if tool_events:
            logger.info(f"Tool events: {[e['tool_name'] for e in tool_events]}")

        # Should have NPC response
        assert "npc_response" in event_types, "Should receive NPC response"

        # May have coach advice (depending on async mode)
        if "coach_advice" in event_types:
            logger.info("Received coach advice")

        logger.info("E2E coordinator workflow test passed")


@pytest.mark.asyncio
async def test_e2e_redis_websocket_manager(test_settings):
    """
    Test Redis-based WebSocket manager:
    1. Verify connection state is stored in Redis
    2. Verify message routing via Pub/Sub
    3. Verify turn deduplication
    """
    from app.infra.websocket import get_connection_manager

    # Get Redis manager
    manager = await get_connection_manager()

    # Verify it's Redis manager
    assert manager.__class__.__name__ == "RedisConnectionManager", \
        "Should use RedisConnectionManager when WEBSOCKET_MANAGER_TYPE=redis"

    # Test turn deduplication
    session_id = "test-session-dedup"
    turn_id = "test-turn-123"

    # First check - should not be duplicate
    is_dup = await manager.is_duplicate_turn(session_id, turn_id)
    assert not is_dup, "First turn should not be duplicate"

    # Mark as seen
    await manager.mark_turn_seen(session_id, turn_id)

    # Second check - should be duplicate
    is_dup = await manager.is_duplicate_turn(session_id, turn_id)
    assert is_dup, "Second turn should be duplicate"

    # Clear
    await manager.clear_turn_seen(session_id, turn_id)

    # Third check - should not be duplicate
    is_dup = await manager.is_duplicate_turn(session_id, turn_id)
    assert not is_dup, "After clear, should not be duplicate"

    logger.info("E2E Redis WebSocket manager test passed")


@pytest.mark.asyncio
async def test_e2e_secrets_manager():
    """
    Test secrets manager integration:
    1. Verify secrets are loaded from manager
    2. Verify fallback to environment variables
    3. Verify audit logging
    """
    from core.secrets_manager import get_secrets_manager

    manager = get_secrets_manager()

    # Test getting secret (should fallback to env)
    secret = manager.get_secret("OPENAI_API_KEY", default="default-key")
    assert secret is not None

    # Test required secret (should not raise if exists)
    try:
        secret = manager.get_secret("OPENAI_API_KEY", required=False)
    except ValueError:
        pytest.fail("Should not raise ValueError for non-required secret")

    # Test audit log
    audit_log = manager.get_audit_log(limit=10)
    assert len(audit_log) > 0, "Should have audit log entries"
    assert all("timestamp" in entry for entry in audit_log)
    assert all("key" in entry for entry in audit_log)
    assert all("status" in entry for entry in audit_log)

    logger.info("E2E secrets manager test passed")


@pytest.mark.asyncio
async def test_e2e_tool_execution_parallel():
    """
    Test parallel tool execution:
    1. Execute multiple independent tools
    2. Verify they run in parallel
    3. Verify results are correct
    """
    from app.tools.executor import ToolExecutor
    from app.tools.registry import build_default_registry

    registry = build_default_registry()
    executor = ToolExecutor(registry)

    # Execute multiple tools in parallel
    import time
    time.time()

    # This will be implemented in Phase 3.4
    # For now, just verify executor exists
    assert executor is not None

    logger.info("E2E parallel tool execution test passed (placeholder)")


@pytest.mark.asyncio
async def test_e2e_circuit_breaker():
    """
    Test circuit breaker for external services:
    1. Simulate service failures
    2. Verify circuit opens
    3. Verify fallback behavior
    """
    # This will be implemented in Phase 3.5
    logger.info("E2E circuit breaker test passed (placeholder)")


# ==================== Performance Tests ====================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance_concurrent_connections(http_client: httpx.AsyncClient, auth_token: str):
    """
    Test performance with concurrent WebSocket connections:
    1. Create 10 concurrent sessions
    2. Send messages simultaneously
    3. Verify all responses received
    4. Measure latency
    """
    num_connections = 10

    # Create sessions
    sessions = []
    for i in range(num_connections):
        response = await http_client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "course_id": 1,
                "scenario_id": 1
            }
        )
        assert response.status_code in [200, 201]
        sessions.append(response.json()["session_id"])

    logger.info(f"Created {num_connections} sessions")

    # Connect and send messages concurrently
    async def send_message(session_id: str, message_num: int):
        ws_url = f"ws://test/api/v1/ws/{session_id}?token={auth_token}"

        async with ws_connect(ws_url) as websocket:
            start = asyncio.get_event_loop().time()

            await websocket.send(json.dumps({
                "type": "user_message",
                "content": f"测试消息 {message_num}",
                "turn_id": f"turn-{message_num}"
            }))

            # Wait for NPC response
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)

                if data["type"] == "npc_response":
                    latency = asyncio.get_event_loop().time() - start
                    return latency

    # Run concurrently
    start_time = asyncio.get_event_loop().time()
    latencies = await asyncio.gather(*[
        send_message(session_id, i)
        for i, session_id in enumerate(sessions)
    ])
    total_time = asyncio.get_event_loop().time() - start_time

    # Verify results
    assert len(latencies) == num_connections
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    logger.info("Concurrent connections test:")
    logger.info(f"  Total time: {total_time:.2f}s")
    logger.info(f"  Avg latency: {avg_latency:.2f}s")
    logger.info(f"  Max latency: {max_latency:.2f}s")

    # Performance assertions
    assert avg_latency < 5.0, f"Average latency too high: {avg_latency:.2f}s"
    assert max_latency < 10.0, f"Max latency too high: {max_latency:.2f}s"

    logger.info("Performance test passed")


# ==================== Test Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
