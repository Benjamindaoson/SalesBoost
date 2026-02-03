"""Budget manager for cost control and usage tracking."""
import logging
from typing import Dict, Optional, Any
import json
import time

from core.redis import get_redis

logger = logging.getLogger(__name__)

class BudgetManager:
    """
    Budget Manager for cost control.
    Tracks token usage and cost per session and tenant.
    """
    def __init__(self, daily_limit: float = 10.0, session_limit: float = 0.5) -> None:
        self.daily_limit = daily_limit
        self.session_limit = session_limit
        self.redis_prefix = "salesboost:budget:"

    async def track_cost(self, session_id: str, cost: float, tenant_id: str = "default") -> bool:
        """
        Record cost and check if limits are exceeded.
        """
        redis = await get_redis()
        
        # 1. Track session cost
        session_key = f"{self.redis_prefix}session:{session_id}"
        current_session_cost = await redis.incrbyfloat(session_key, cost)
        await redis.expire(session_key, 3600 * 24) # 24h TTL
        
        # 2. Track tenant daily cost
        today = time.strftime("%Y-%m-%d")
        tenant_key = f"{self.redis_prefix}tenant:{tenant_id}:{today}"
        current_tenant_cost = await redis.incrbyfloat(tenant_key, cost)
        await redis.expire(tenant_key, 3600 * 25) # 25h TTL
        
        # 3. Check limits
        if current_session_cost > self.session_limit:
            logger.warning(f"Session budget exceeded: {session_id} | {current_session_cost} > {self.session_limit}")
            return False
            
        if current_tenant_cost > self.daily_limit:
            logger.warning(f"Tenant daily budget exceeded: {tenant_id} | {current_tenant_cost} > {self.daily_limit}")
            return False
            
        return True

    async def get_session_cost(self, session_id: str) -> float:
        redis = await get_redis()
        val = await redis.get(f"{self.redis_prefix}session:{session_id}")
        return float(val) if val else 0.0

    async def get_tenant_daily_cost(self, tenant_id: str) -> float:
        redis = await get_redis()
        today = time.strftime("%Y-%m-%d")
        val = await redis.get(f"{self.redis_prefix}tenant:{tenant_id}:{today}")
        return float(val) if val else 0.0
