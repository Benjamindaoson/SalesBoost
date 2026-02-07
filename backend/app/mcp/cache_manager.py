"""
MCP Cache Manager - 智能缓存管理器

提供智能缓存功能，避免重复工具调用。

核心功能：
1. 工具执行结果缓存
2. 执行计划结果缓存
3. 缓存命中率统计
4. TTL管理

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class MCPCacheManager:
    """
    MCP智能缓存管理器

    使用Redis缓存工具执行结果，避免重复计算。

    Usage:
        cache = MCPCacheManager(redis_client)

        # 检查缓存
        result = await cache.get_tool_result("knowledge_retriever", {...}, {...})
        if result:
            return result

        # 执行工具
        result = await execute_tool(...)

        # 缓存结果
        await cache.set_tool_result("knowledge_retriever", {...}, {...}, result)
    """

    def __init__(
        self,
        redis_client: Redis,
        default_ttl: int = 3600,  # 1小时
        enable_stats: bool = True,
    ):
        """
        Initialize cache manager

        Args:
            redis_client: Redis client
            default_ttl: Default TTL in seconds
            enable_stats: Enable statistics tracking
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # Statistics
        self.hit_count = 0
        self.miss_count = 0

    def _generate_cache_key(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """
        生成缓存键

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            context: Execution context

        Returns:
            Cache key
        """
        # 只使用影响结果的参数
        cache_data = {
            "tool": tool_name,
            "params": parameters,
            "context": context,
        }

        # 排序后序列化，确保一致性
        cache_str = json.dumps(cache_data, sort_keys=True)

        # 生成哈希
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        return f"mcp:cache:tool:{cache_hash}"

    def _generate_plan_key(self, plan_id: str, intent: str, context: Dict[str, Any]) -> str:
        """
        生成执行计划缓存键

        Args:
            plan_id: Plan ID
            intent: Intent
            context: Context

        Returns:
            Cache key
        """
        cache_data = {
            "plan_id": plan_id,
            "intent": intent,
            "context": context,
        }

        cache_str = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        return f"mcp:cache:plan:{cache_hash}"

    async def get_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        获取工具执行结果缓存

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            context: Execution context

        Returns:
            Cached result or None
        """
        key = self._generate_cache_key(tool_name, parameters, context)

        try:
            cached = await self.redis.get(key)

            if cached:
                if self.enable_stats:
                    self.hit_count += 1

                logger.debug(f"Cache hit for {tool_name}")
                return json.loads(cached)

            if self.enable_stats:
                self.miss_count += 1

            logger.debug(f"Cache miss for {tool_name}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        设置工具执行结果缓存

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            context: Execution context
            result: Execution result
            ttl: TTL in seconds (optional)
        """
        key = self._generate_cache_key(tool_name, parameters, context)
        ttl = ttl or self.default_ttl

        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result),
            )
            logger.debug(f"Cached result for {tool_name} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def get_plan_result(
        self,
        plan_id: str,
        intent: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        获取执行计划结果缓存

        Args:
            plan_id: Plan ID
            intent: Intent
            context: Context

        Returns:
            Cached result or None
        """
        key = self._generate_plan_key(plan_id, intent, context)

        try:
            cached = await self.redis.get(key)

            if cached:
                if self.enable_stats:
                    self.hit_count += 1

                logger.debug(f"Cache hit for plan {plan_id}")
                return json.loads(cached)

            if self.enable_stats:
                self.miss_count += 1

            logger.debug(f"Cache miss for plan {plan_id}")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_plan_result(
        self,
        plan_id: str,
        intent: str,
        context: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        设置执行计划结果缓存

        Args:
            plan_id: Plan ID
            intent: Intent
            context: Context
            result: Execution result
            ttl: TTL in seconds (optional)
        """
        key = self._generate_plan_key(plan_id, intent, context)
        ttl = ttl or self.default_ttl

        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result),
            )
            logger.debug(f"Cached result for plan {plan_id} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def invalidate_tool(self, tool_name: str):
        """
        使工具的所有缓存失效

        Args:
            tool_name: Tool name
        """
        pattern = f"mcp:cache:tool:*"

        try:
            # 扫描并删除匹配的键
            count = 0
            async for key in self.redis.scan_iter(match=pattern):
                # 检查是否是该工具的缓存
                cached = await self.redis.get(key)
                if cached:
                    data = json.loads(cached)
                    if data.get("tool_name") == tool_name:
                        await self.redis.delete(key)
                        count += 1

            logger.info(f"Invalidated {count} cache entries for {tool_name}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def clear_all(self):
        """清除所有MCP缓存"""
        try:
            count = 0

            # 清除工具缓存
            async for key in self.redis.scan_iter(match="mcp:cache:tool:*"):
                await self.redis.delete(key)
                count += 1

            # 清除计划缓存
            async for key in self.redis.scan_iter(match="mcp:cache:plan:*"):
                await self.redis.delete(key)
                count += 1

            logger.info(f"Cleared {count} cache entries")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            Statistics dict
        """
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.0

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total,
            "hit_rate": hit_rate,
        }

    def reset_stats(self):
        """重置统计"""
        self.hit_count = 0
        self.miss_count = 0
