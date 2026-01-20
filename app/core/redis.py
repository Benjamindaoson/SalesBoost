"""
Redis Configuration
会话状态缓存
"""
import json
import logging
from typing import Optional, Any
from app.core.config import get_settings

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


class InMemoryCache:
    """内存缓存（Redis 不可用时的降级方案）"""
    
    def __init__(self):
        self._store: dict[str, Any] = {}
        self._ttl: dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True
    
    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0
    
    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0
