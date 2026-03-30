"""
Redis-based Distributed Semaphore for ModelGateway

Enables horizontal scaling: multiple backend instances share a global
concurrency limit via Redis. Falls back to asyncio.Semaphore when Redis
is unavailable.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Redis key prefix for LLM concurrency
KEY_PREFIX = "salesboost:llm:semaphore"
LEASE_TTL = 60  # seconds - max hold time if process crashes


async def _get_redis():
    """Lazy get Redis client."""
    try:
        from ...core.redis import get_redis
        return await get_redis()
    except Exception as e:
        logger.debug("Redis unavailable for semaphore: %s", e)
        return None


class RedisDistributedSemaphore:
    """
    Distributed semaphore using Redis.
    Uses sorted set + lease tokens for fairness and crash recovery.
    """

    def __init__(self, key: str, limit: int, redis_url: Optional[str] = None):
        self.key = f"{KEY_PREFIX}:{key}"
        self.limit = limit
        self._redis_url = redis_url
        self._redis = None

    async def _ensure_redis(self):
        if self._redis is None:
            self._redis = await _get_redis()
        return self._redis

    @asynccontextmanager
    async def acquire(self):
        """Acquire a slot. Blocks until available or timeout. Raises if Redis unavailable."""
        redis = await self._ensure_redis()
        if not redis or not hasattr(redis, "zadd"):
            raise RuntimeError("Redis unavailable for distributed semaphore")

        acquired = False
        token = f"{time.time():.6f}:{id(self)}"
        try:
            for _ in range(600):  # 60s max wait
                now = time.time()
                await redis.zremrangebyscore(self.key, 0, now - LEASE_TTL)
                count = await redis.zcard(self.key)
                if count < self.limit:
                    await redis.zadd(self.key, {token: now})
                    await redis.expire(self.key, LEASE_TTL + 10)
                    acquired = True
                    break
                await asyncio.sleep(0.1)
            if not acquired:
                raise RuntimeError("Redis semaphore timeout")
            yield
        except RuntimeError:
            raise
        except Exception as e:
            logger.debug("Redis semaphore acquire failed: %s", e)
            raise
        finally:
            if acquired and redis:
                try:
                    await redis.zrem(self.key, token)
                except Exception:
                    pass


class ConcurrencyLimiter:
    """
    Unified limiter: Redis when available, else asyncio.Semaphore.
    """

    def __init__(self, limit: int = 10, use_redis: bool = True):
        self.limit = limit
        self._use_redis = use_redis
        self._redis_sem = RedisDistributedSemaphore("model_calls", limit)
        self._local_sem = asyncio.Semaphore(limit)
        self._redis_available: Optional[bool] = None

    async def check_redis_available(self) -> bool:
        """Probe Redis at startup. Logs clearly if cross-worker rate limiting is degraded."""
        try:
            async with self._redis_sem.acquire():
                pass
            self._redis_available = True
            logger.info("[ConcurrencyLimiter] Redis semaphore: OK")
            return True
        except Exception as e:
            self._redis_available = False
            logger.warning(
                "[ConcurrencyLimiter] Redis unavailable at startup — "
                "cross-worker LLM rate limiting is DISABLED. Error: %s", e
            )
            return False

    @asynccontextmanager
    async def acquire(self):
        if self._redis_available is False:
            async with self._local_sem:
                yield
            return

        if self._use_redis:
            try:
                async with self._redis_sem.acquire():
                    yield
                if self._redis_available is None:
                    self._redis_available = True
                return
            except Exception as e:
                logger.warning(
                    "[ConcurrencyLimiter] Redis semaphore failed — falling back to "
                    "process-local asyncio.Semaphore. Cross-worker LLM rate limiting "
                    "is DISABLED. Error: %s",
                    e,
                )
                self._redis_available = False

        async with self._local_sem:
            yield
