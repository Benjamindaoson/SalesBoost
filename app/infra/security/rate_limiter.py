import time
import asyncio
import logging
from typing import Optional, Dict, Any
from redis import asyncio as aioredis
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, EventBase

logger = logging.getLogger(__name__)

class RateLimitEventPayload(EventBase):
    key: str
    limit: int
    window: int
    current_count: int
    details: Dict[str, Any] = {}

class RateLimiter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        
    async def connect(self):
        if not self.redis:
            try:
                self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            except Exception as e:
                logger.error(f"Failed to connect to Redis for RateLimiter: {e}")

    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Sliding window rate limiter using Redis
        key: identifier (e.g., user_id or tenant_id)
        limit: max requests
        window: time window in seconds
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return True # Fail open if Redis down

        now = time.time()
        window_start = now - window
        
        redis_key = f"rate_limit:{key}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Count remaining
            pipe.zcard(redis_key)
            # Add current
            pipe.zadd(redis_key, {str(now): now})
            # Set expiry
            pipe.expire(redis_key, window)
            
            results = await pipe.execute()
            
        current_count = results[1]
        
        allowed = current_count < limit
        
        if not allowed:
            # Publish Degradation Event
            logger.warning(f"Rate limit exceeded for {key}. Publishing REQUEST_DEGRADED.")
            try:
                payload = RateLimitEventPayload(
                    event_id=f"limit_{key}_{int(now)}",
                    key=key,
                    limit=limit,
                    window=window,
                    current_count=current_count,
                    reason="Rate limit exceeded",
                    severity="warning"
                )
                # Fire and forget
                asyncio.create_task(bus.publish(EventType.REQUEST_DEGRADED, payload))
            except Exception as e:
                logger.error(f"Failed to publish degradation event: {e}")
                
        return allowed

rate_limiter = RateLimiter()
