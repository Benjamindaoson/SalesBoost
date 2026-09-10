"""Pytest configuration and shared fixtures."""
from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from salesagent.main import app, get_db, get_redis
from salesagent.auth.dependencies import get_current_user
from salesagent.models.db_models import Base


# ── Test Database ────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "postgresql+asyncpg://salesagent:salesagent_secret@localhost:5432/salesagent_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="session")
async def db_schema() -> AsyncGenerator[None, None]:
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        pytest.skip(f"Postgres test database unavailable: {exc}")

    yield

    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_session(db_schema: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_schema: None) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client with test DB override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    async def override_get_current_user() -> dict:
        return {"sub": "test-admin", "user_id": "test-admin", "role": "admin"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Event Loop ───────────────────────────────────────────────────────────────
