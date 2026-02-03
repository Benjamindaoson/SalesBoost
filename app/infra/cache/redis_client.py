import logging
import asyncio
import time
from typing import Optional, Dict, Any, List
from core.redis import get_redis, InMemoryCache

logger = logging.getLogger(__name__)

class RobustRedisClient:
    """
    A robust wrapper around Redis client with automatic memory fallback.
    Ensures critical paths (like model routing) never fail due to Redis issues.
    """
    
    def __init__(self):
        self._client = None
        self._memory_fallback: Dict[str, Any] = {}
        self._is_redis_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30 # seconds

    async def initialize(self):
        """Initialize connection"""
        try:
            self._client = await get_redis()
            if isinstance(self._client, InMemoryCache):
                self._is_redis_healthy = False
                logger.warning("Initialized with InMemoryCache (Redis unavailable)")
            else:
                await self._client.ping()
                self._is_redis_healthy = True
                logger.info("RobustRedisClient initialized successfully")
        except Exception as e:
            self._is_redis_healthy = False
            logger.error(f"Failed to initialize Redis: {e}. Using memory fallback.")

    async def _ensure_connection(self):
        """Periodically check connection health if down"""
        if self._is_redis_healthy:
            return

        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            return

        self._last_health_check = now
        try:
            # Try to get fresh client
            client = await get_redis()
            if not isinstance(client, InMemoryCache):
                await client.ping()
                self._client = client
                self._is_redis_healthy = True
                logger.info("Redis connection restored!")
                # Optional: Sync memory fallback to Redis here
        except Exception as e:
            logger.debug(f"Redis still down: {e}")

    async def is_healthy(self) -> bool:
        """Check and return current Redis health."""
        await self._ensure_connection()
        return bool(self._is_redis_healthy)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields from a hash"""
        await self._ensure_connection()
        
        if self._is_redis_healthy:
            try:
                return await self._client.hgetall(key)
            except Exception as e:
                logger.error(f"[CRITICAL] Redis hgetall failed: {e}. Switching to memory.")
                self._is_redis_healthy = False
        
        # Fallback
        return self._memory_fallback.get(key, {})

    async def hset(self, key: str, mapping: Dict[str, Any]):
        """Set hash fields"""
        await self._ensure_connection()
        
        # Always update memory for consistency/fallback
        if key not in self._memory_fallback:
            self._memory_fallback[key] = {}
        self._memory_fallback[key].update(mapping)

        if self._is_redis_healthy:
            try:
                await self._client.hset(key, mapping=mapping)
            except Exception as e:
                logger.error(f"[CRITICAL] Redis hset failed: {e}. Switching to memory.")
                self._is_redis_healthy = False

    async def eval(self, script: str, numkeys: int, *keys_and_args):
        """Execute Lua script"""
        await self._ensure_connection()
        
        if self._is_redis_healthy:
            try:
                return await self._client.eval(script, numkeys, *keys_and_args)
            except Exception as e:
                logger.error(f"[CRITICAL] Redis eval failed: {e}. Switching to memory.")
                self._is_redis_healthy = False
        
        # Lua fallback is hard to genericize perfectly, 
        # so we return None to trigger application-level fallback logic
        return None

    async def lpush(self, key: str, *values: Any) -> int:
        """Prepend values to a list"""
        await self._ensure_connection()
        
        # Memory update
        if key not in self._memory_fallback:
            self._memory_fallback[key] = []
        if isinstance(self._memory_fallback[key], list):
            for v in values:
                self._memory_fallback[key].insert(0, v)

        if self._is_redis_healthy:
            try:
                return await self._client.lpush(key, *values)
            except Exception as e:
                logger.error(f"[CRITICAL] Redis lpush failed: {e}. Switching to memory.")
                self._is_redis_healthy = False
        
        return len(self._memory_fallback.get(key, []))

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim a list to the specified range"""
        await self._ensure_connection()
        
        # Memory update
        if key in self._memory_fallback and isinstance(self._memory_fallback[key], list):
            lst = self._memory_fallback[key]
            # Redis ltrim keeps elements in [start, end] inclusive
            # Handle negative indices if needed, but for history usually 0, N
            if end == -1:
                self._memory_fallback[key] = lst[start:]
            else:
                self._memory_fallback[key] = lst[start:end+1]

        if self._is_redis_healthy:
            try:
                await self._client.ltrim(key, start, end)
                return True
            except Exception as e:
                logger.error(f"[CRITICAL] Redis ltrim failed: {e}. Switching to memory.")
                self._is_redis_healthy = False
        
        return True

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of elements from a list"""
        await self._ensure_connection()

        if self._is_redis_healthy:
            try:
                return await self._client.lrange(key, start, end)
            except Exception as e:
                logger.error(f"[CRITICAL] Redis lrange failed: {e}. Switching to memory.")
                self._is_redis_healthy = False
        
        # Memory Fallback
        if key in self._memory_fallback and isinstance(self._memory_fallback[key], list):
            lst = self._memory_fallback[key]
            if end == -1:
                return lst[start:]
            return lst[start:end+1]
        return []

    def get_memory_fallback(self, key: str) -> Dict[str, Any]:
        """Direct access to memory fallback for debugging/initialization"""
        return self._memory_fallback.get(key, {})

# Global instance
redis_client = RobustRedisClient()
