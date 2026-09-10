"""Integration tests for chat flow."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_chat_stream_new_session(client: AsyncClient):
    """Test chat streaming with a new session."""
    response = await client.post(
        "/chat/stream",
        json={
            "message": "你好，我想了解一下你们的产品",
            "session_id": None,
            "customer_id": "test_customer_001",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "X-Session-ID" in response.headers


@pytest.mark.asyncio
async def test_chat_stream_existing_session(client: AsyncClient):
    """Test chat streaming with an existing session."""
    # First message to create session
    response1 = await client.post(
        "/chat/stream",
        json={
            "message": "你好",
            "session_id": None,
            "customer_id": "test_customer_002",
        },
    )
    session_id = response1.headers.get("X-Session-ID")
    assert session_id is not None

    # Second message in same session
    response2 = await client.post(
        "/chat/stream",
        json={
            "message": "价格是多少？",
            "session_id": session_id,
            "customer_id": "test_customer_002",
        },
    )
    assert response2.status_code == 200
    assert response2.headers.get("X-Session-ID") == session_id


@pytest.mark.asyncio
async def test_session_creation(client: AsyncClient):
    """Test session creation endpoint."""
    response = await client.post(
        "/sessions",
        json={
            "customer_id": "test_customer_003",
            "metadata": {"source": "web", "campaign": "test"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "active"
    assert data["current_stage"] == "ICEBREAK"


@pytest.mark.asyncio
async def test_session_retrieval(client: AsyncClient):
    """Test retrieving session details."""
    # Create session
    create_response = await client.post(
        "/sessions",
        json={"customer_id": "test_customer_004"},
    )
    session_id = create_response.json()["session_id"]

    # Retrieve session
    get_response = await client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == session_id
    assert data["customer_id"] == "test_customer_004"
