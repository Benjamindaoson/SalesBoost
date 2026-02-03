"""
End-to-End Integration Tests

Tests the complete flow from user request to response.
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, UserRole, Course, Task, Session, SessionStatus
from app.config.unified import get_unified_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    settings = get_unified_settings()

    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield async_session

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(test_db):
    """Create test user."""
    async with test_db() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2",
            role=UserRole.STUDENT,
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def test_course(test_db):
    """Create test course."""
    async with test_db() as session:
        course = Course(
            title="Test Course",
            description="Test course description",
            category="sales",
            difficulty=1,
        )
        session.add(course)
        await session.commit()
        await session.refresh(course)
        return course


@pytest.fixture
async def test_task(test_db, test_course):
    """Create test task."""
    async with test_db() as session:
        task = Task(
            course_id=test_course.id,
            title="Test Task",
            description="Test task description",
            task_type="conversation",
            order=1,
            points=100,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


class TestE2EAuthentication:
    """Test authentication flow."""

    @pytest.mark.asyncio
    async def test_login_flow(self, test_client, test_user):
        """Test complete login flow."""
        # 1. Login
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "demo123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        token = data["access_token"]

        # 2. Access protected endpoint
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["role"] == "student"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client):
        """Test unauthorized access is blocked."""
        response = await test_client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestE2EConversation:
    """Test complete conversation flow."""

    @pytest.mark.asyncio
    async def test_conversation_flow(self, test_client, test_user, test_task):
        """Test complete conversation flow."""
        # 1. Start session
        response = await test_client.post(
            "/api/v1/sessions",
            json={
                "user_id": test_user.id,
                "task_id": test_task.id,
            }
        )
        assert response.status_code == 200
        session_data = response.json()
        session_id = session_data["id"]
        assert session_data["status"] == "active"

        # 2. Send first message (opening)
        response = await test_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={
                "role": "user",
                "content": "您好，我想了解一下贵公司的信用卡产品",
            }
        )
        assert response.status_code == 200
        message_data = response.json()
        assert message_data["role"] == "user"

        # 3. Get AI response
        response = await test_client.post(
            f"/api/v1/sessions/{session_id}/respond",
            json={
                "message": "您好，我想了解一下贵公司的信用卡产品",
            }
        )
        assert response.status_code == 200
        response_data = response.json()
        assert "content" in response_data
        assert "sales_state" in response_data

        # 4. Continue conversation (discovery)
        response = await test_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={
                "role": "user",
                "content": "我主要是想要一张有积分的卡",
            }
        )
        assert response.status_code == 200

        # 5. Get evaluation
        response = await test_client.get(
            f"/api/v1/sessions/{session_id}/evaluation"
        )
        assert response.status_code == 200
        eval_data = response.json()
        assert "overall_score" in eval_data
        assert "methodology_score" in eval_data

        # 6. Complete session
        response = await test_client.post(
            f"/api/v1/sessions/{session_id}/complete"
        )
        assert response.status_code == 200
        session_data = response.json()
        assert session_data["status"] == "completed"


class TestE2ERAG:
    """Test RAG retrieval flow."""

    @pytest.mark.asyncio
    async def test_rag_retrieval_flow(self, test_client):
        """Test complete RAG retrieval flow."""
        # 1. Retrieve documents
        response = await test_client.post(
            "/api/v1/rag/retrieve",
            json={
                "query": "信用卡积分规则",
                "top_k": 5,
                "search_mode": "hybrid",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 5

        # 2. Rerank results
        if data["results"]:
            response = await test_client.post(
                "/api/v1/rag/rerank",
                json={
                    "query": "信用卡积分规则",
                    "documents": [r["content"] for r in data["results"]],
                    "top_k": 3,
                }
            )
            assert response.status_code == 200
            rerank_data = response.json()
            assert "results" in rerank_data
            assert len(rerank_data["results"]) <= 3


class TestE2EVoice:
    """Test voice interaction flow."""

    @pytest.mark.asyncio
    async def test_tts_flow(self, test_client):
        """Test TTS flow."""
        response = await test_client.post(
            "/api/v1/voice/tts",
            json={
                "text": "您好，欢迎咨询我们的信用卡产品",
                "emotion": "friendly",
                "rate": 1.0,
                "pitch": 1.0,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "audio_base64" in data
        assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_stt_flow(self, test_client):
        """Test STT flow."""
        # Mock audio data
        audio_base64 = "SGVsbG8gV29ybGQ="  # "Hello World" in base64

        response = await test_client.post(
            "/api/v1/voice/stt",
            json={
                "audio_base64": audio_base64,
                "language": "zh",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "confidence" in data


class TestE2EPerformance:
    """Test performance benchmarks."""

    @pytest.mark.asyncio
    async def test_response_time(self, test_client):
        """Test API response time."""
        import time

        start = time.time()
        response = await test_client.get("/api/v1/health")
        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        assert latency < 100  # Should respond within 100ms

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client):
        """Test handling concurrent requests."""
        tasks = []
        for i in range(10):
            task = test_client.get("/api/v1/health")
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_rag_latency(self, test_client):
        """Test RAG retrieval latency."""
        import time

        start = time.time()
        response = await test_client.post(
            "/api/v1/rag/retrieve",
            json={
                "query": "信用卡",
                "top_k": 5,
            }
        )
        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        assert latency < 200  # Should retrieve within 200ms


class TestE2EDataIntegrity:
    """Test data integrity."""

    @pytest.mark.asyncio
    async def test_session_data_integrity(self, test_db, test_user, test_task):
        """Test session data is properly saved."""
        async with test_db() as session:
            # Create session
            training_session = Session(
                user_id=test_user.id,
                task_id=test_task.id,
                status=SessionStatus.ACTIVE,
                sales_state="opening",
                turns_count=0,
            )
            session.add(training_session)
            await session.commit()
            session_id = training_session.id

            # Retrieve session
            from sqlalchemy import select
            result = await session.execute(
                select(Session).where(Session.id == session_id)
            )
            retrieved_session = result.scalar_one()

            assert retrieved_session.user_id == test_user.id
            assert retrieved_session.task_id == test_task.id
            assert retrieved_session.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_cascade_delete(self, test_db, test_user, test_task):
        """Test cascade delete works."""
        async with test_db() as session:
            # Create session with messages
            training_session = Session(
                user_id=test_user.id,
                task_id=test_task.id,
                status=SessionStatus.ACTIVE,
            )
            session.add(training_session)
            await session.commit()

            from app.models import Message, MessageRole
            message = Message(
                session_id=training_session.id,
                role=MessageRole.USER,
                content="Test message",
            )
            session.add(message)
            await session.commit()

            session_id = training_session.id

            # Delete session
            await session.delete(training_session)
            await session.commit()

            # Check messages are also deleted
            from sqlalchemy import select
            result = await session.execute(
                select(Message).where(Message.session_id == session_id)
            )
            messages = result.scalars().all()

            assert len(messages) == 0


class TestE2EErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_input(self, test_client):
        """Test invalid input is rejected."""
        response = await test_client.post(
            "/api/v1/sessions",
            json={
                "user_id": "invalid",  # Should be integer
                "task_id": 1,
            }
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_not_found(self, test_client):
        """Test 404 for non-existent resources."""
        response = await test_client.get("/api/v1/sessions/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client):
        """Test rate limiting works."""
        # Send many requests
        responses = []
        for i in range(150):  # Exceed limit of 100
            response = await test_client.get("/api/v1/health")
            responses.append(response)

        # Some should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
