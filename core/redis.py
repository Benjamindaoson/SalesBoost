"""
Redis Configuration
会话状态缓存
"""
import logging
import time
from typing import Any, Optional

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis 客户端（可选依赖）
_redis_client = None


async def get_redis():
    """获取 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Redis client initialized")
        except ImportError:
            logger.warning("redis package not installed, using in-memory fallback")
            _redis_client = InMemoryCache()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory fallback")
            _redis_client = InMemoryCache()
    return _redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global _redis_client
    if _redis_client and hasattr(_redis_client, "close"):
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


class InMemoryLock:
    """Async context manager to simulate redis-py lock"""
    def __init__(self, name: str):
        self.name = name

    async def __aenter__(self):
        # In-memory mock lock just lets you in immediately
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class InMemoryCache:
    """内存缓存（Redis 不可用时的降级方案）"""
    
    def __init__(self):
        self._store: dict[str, Any] = {}
        self._ttl: dict[str, float] = {}

    def _cleanup_key(self, key: str) -> None:
        expires_at = self._ttl.get(key)
        if expires_at is not None and expires_at <= time.time():
            self._store.pop(key, None)
            self._ttl.pop(key, None)
    
    async def get(self, key: str) -> Optional[str]:
        self._cleanup_key(key)
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._ttl[key] = time.time() + ex
        else:
            self._ttl.pop(key, None)
        return True
    
    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            self._ttl.pop(key, None)
            return 1
        return 0
    
    async def exists(self, key: str) -> int:
        self._cleanup_key(key)
        return 1 if key in self._store else 0

    async def incr(self, key: str) -> int:
        self._cleanup_key(key)
        current = int(self._store.get(key, 0) or 0)
        current += 1
        self._store[key] = current
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._store:
            self._ttl[key] = time.time() + seconds
            return True
        return False

    async def xadd(self, name: str, fields: dict, id: str = "*", maxlen: Optional[int] = None, approximate: bool = True) -> str:
        """Simulate Redis XADD for streams"""
        if name not in self._store:
            self._store[name] = []
        
        # Simple ID generation: timestamp-sequence
        import time
        ts = int(time.time() * 1000)
        if id == "*":
            # Very simple ID generation
            seq = len(self._store[name])
            msg_id = f"{ts}-{seq}"
        else:
            msg_id = id
            
        self._store[name].append((msg_id, fields))
        return msg_id

    def lock(self, name: str, timeout: Optional[float] = None, sleep: float = 0.1):
        """Simulate Redis Distributed Lock"""
        return InMemoryLock(name)

    async def xrange(self, name: str, min: str = "-", max: str = "+", count: Optional[int] = None) -> list:
        """Simulate Redis XRANGE for streams"""
        if name not in self._store:
            return []
        
        # Simplified implementation: return all, ignoring min/max parsing
        # Real XRANGE is complex, but for WAL replay we usually want all
        return self._store[name]

    async def close(self):
        pass
