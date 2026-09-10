"""Shared FastAPI dependencies with circuit breaker protection."""
from __future__ import annotations

from typing import AsyncGenerator
import structlog

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import redis.asyncio as aioredis

from salesagent.core.settings import settings
from salesagent.utils.circuit_breaker import get_circuit_breaker
from salesagent.observability.metrics import redis_fallback_active

log = structlog.get_logger()

# ── Database engine & session factory ────────────────────────────────────────

_engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

# ── Redis client with fallback ───────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None
_redis_fallback: "InMemoryCache | None" = None
_redis_fallback_active = False


class InMemoryCache:
    """Simple in-memory cache fallback for Redis."""

    def __init__(self):
        self._store: dict[str, str] = {}
        log.warning("Using in-memory cache fallback (Redis unavailable)")

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def keys(self, pattern: str = "*") -> list[str]:
        if pattern == "*":
            return list(self._store.keys())
        prefix = pattern.rstrip("*")
        return [k for k in self._store.keys() if k.startswith(prefix)]

    async def aclose(self) -> None:
        pass


async def get_redis() -> aioredis.Redis | InMemoryCache:
    """Get Redis client with circuit breaker protection and in-memory fallback."""
    global _redis_client, _redis_fallback, _redis_fallback_active

    # Return existing client if available
    if _redis_client is not None and not _redis_fallback_active:
        return _redis_client

    if _redis_fallback_active and _redis_fallback is not None:
        return _redis_fallback

    circuit = get_circuit_breaker(
        name="redis",
        failure_threshold=3,
        recovery_timeout=30.0,
    )

    async def _connect_redis():
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        return client

    try:
        _redis_client = await circuit.call(_connect_redis)
        if _redis_fallback_active:
            log.info("Redis connection restored")
            _redis_fallback_active = False
            _redis_fallback = None
            redis_fallback_active.set(0)
        return _redis_client
    except Exception as e:
        log.warning("Redis connection failed, using in-memory fallback", error=str(e))
        _redis_fallback_active = True
        redis_fallback_active.set(1)
        if _redis_fallback is None:
            _redis_fallback = InMemoryCache()
        return _redis_fallback


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def close_db_engine():
    """Close database engine."""
    await _engine.dispose()


async def close_redis():
    """Close Redis client."""
    global _redis_client, _redis_fallback
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    _redis_fallback = None
    _redis_fallback_active = False
