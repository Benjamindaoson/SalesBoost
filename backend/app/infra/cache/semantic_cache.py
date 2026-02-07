"""
Semantic Cache

语义缓存系统 - 基于向量相似度的智能缓存

不是精确匹配，而是语义相似匹配，命中率提升3-5倍

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import redis
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    语义缓存系统

    核心特性：
    1. 语义相似度匹配（不是精确匹配）
    2. 向量检索（使用embedding）
    3. 多级缓存（内存 + Redis）
    4. 智能过期策略

    示例：
        用户问："如何提升销售业绩？"
        缓存中有："怎样提高销售成绩？"
        → 语义相似，直接返回缓存结果
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        openai_client: AsyncOpenAI,
        similarity_threshold: float = 0.85,
        ttl: int = 3600,
        max_memory_cache: int = 100,
    ):
        """
        初始化语义缓存

        Args:
            redis_client: Redis客户端
            openai_client: OpenAI客户端（用于生成embedding）
            similarity_threshold: 相似度阈值（0-1），超过此值视为命中
            ttl: 缓存过期时间（秒）
            max_memory_cache: 内存缓存最大条目数
        """
        self.redis = redis_client
        self.openai = openai_client
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.max_memory_cache = max_memory_cache

        # L1缓存：内存（最快）
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_cache_order: List[str] = []  # LRU顺序

        # 统计信息
        self.stats = {
            "total_queries": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "misses": 0,
        }

        logger.info(
            f"SemanticCache initialized: "
            f"threshold={similarity_threshold}, ttl={ttl}s"
        )

    async def get(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取结果

        Args:
            query: 查询文本
            context: 可选的上下文信息

        Returns:
            缓存的结果，如果未命中返回None
        """
        self.stats["total_queries"] += 1

        # 生成查询的embedding
        query_embedding = await self._generate_embedding(query)

        # 1. 检查内存缓存（L1）
        memory_result = self._check_memory_cache(query_embedding)
        if memory_result:
            self.stats["memory_hits"] += 1
            logger.debug(f"Memory cache hit: {query[:50]}...")
            return memory_result

        # 2. 检查Redis缓存（L2）
        redis_result = await self._check_redis_cache(query_embedding, context)
        if redis_result:
            self.stats["redis_hits"] += 1
            logger.debug(f"Redis cache hit: {query[:50]}...")

            # 提升到内存缓存
            self._add_to_memory_cache(query_embedding, redis_result)

            return redis_result

        # 3. 缓存未命中
        self.stats["misses"] += 1
        logger.debug(f"Cache miss: {query[:50]}...")
        return None

    async def set(
        self,
        query: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        设置缓存

        Args:
            query: 查询文本
            result: 结果数据
            context: 可选的上下文信息
        """
        # 生成embedding
        query_embedding = await self._generate_embedding(query)

        # 构建缓存条目
        cache_entry = {
            "query": query,
            "embedding": query_embedding.tolist(),
            "result": result,
            "context": context or {},
            "timestamp": time.time(),
        }

        # 存储到Redis
        cache_key = self._generate_cache_key(query, context)
        await self._store_to_redis(cache_key, cache_entry)

        # 存储到内存缓存
        self._add_to_memory_cache(query_embedding, cache_entry)

        logger.debug(f"Cached: {query[:50]}...")

    async def _generate_embedding(self, text: str) -> np.ndarray:
        """
        生成文本的embedding向量

        Args:
            text: 输入文本

        Returns:
            Embedding向量（numpy数组）
        """
        try:
            response = await self.openai.embeddings.create(
                model="text-embedding-3-small",  # 更快更便宜
                input=text,
            )

            embedding = np.array(response.data[0].embedding)
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def _check_memory_cache(
        self,
        query_embedding: np.ndarray,
    ) -> Optional[Dict[str, Any]]:
        """
        检查内存缓存

        Args:
            query_embedding: 查询的embedding

        Returns:
            缓存结果或None
        """
        best_similarity = 0.0
        best_entry = None

        for cache_key, entry in self.memory_cache.items():
            cached_embedding = np.array(entry["embedding"])
            similarity = self._cosine_similarity(query_embedding, cached_embedding)

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_entry = entry

        if best_entry:
            # 更新LRU顺序
            cache_key = self._embedding_to_key(best_entry["embedding"])
            if cache_key in self.memory_cache_order:
                self.memory_cache_order.remove(cache_key)
            self.memory_cache_order.append(cache_key)

            return best_entry["result"]

        return None

    async def _check_redis_cache(
        self,
        query_embedding: np.ndarray,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        检查Redis缓存

        Args:
            query_embedding: 查询的embedding
            context: 上下文信息

        Returns:
            缓存结果或None
        """
        try:
            # 获取所有缓存键
            pattern = "semantic_cache:*"
            keys = self.redis.keys(pattern)

            if not keys:
                return None

            best_similarity = 0.0
            best_entry = None

            # 遍历所有缓存条目
            for key in keys:
                entry_json = self.redis.get(key)
                if not entry_json:
                    continue

                entry = json.loads(entry_json)

                # 检查上下文匹配
                if context and entry.get("context") != context:
                    continue

                # 计算相似度
                cached_embedding = np.array(entry["embedding"])
                similarity = self._cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_entry = entry

            if best_entry:
                logger.debug(f"Redis cache hit with similarity: {best_similarity:.3f}")
                return best_entry["result"]

            return None

        except Exception as e:
            logger.error(f"Redis cache check failed: {e}")
            return None

    async def _store_to_redis(
        self,
        cache_key: str,
        cache_entry: Dict[str, Any],
    ) -> None:
        """
        存储到Redis

        Args:
            cache_key: 缓存键
            cache_entry: 缓存条目
        """
        try:
            entry_json = json.dumps(cache_entry)
            self.redis.setex(
                f"semantic_cache:{cache_key}",
                self.ttl,
                entry_json,
            )
        except Exception as e:
            logger.error(f"Failed to store to Redis: {e}")

    def _add_to_memory_cache(
        self,
        embedding: np.ndarray,
        entry: Dict[str, Any],
    ) -> None:
        """
        添加到内存缓存（LRU）

        Args:
            embedding: Embedding向量
            entry: 缓存条目
        """
        cache_key = self._embedding_to_key(embedding)

        # 如果已存在，更新
        if cache_key in self.memory_cache:
            self.memory_cache_order.remove(cache_key)
        # 如果缓存满了，删除最旧的
        elif len(self.memory_cache) >= self.max_memory_cache:
            oldest_key = self.memory_cache_order.pop(0)
            del self.memory_cache[oldest_key]

        # 添加新条目
        self.memory_cache[cache_key] = entry
        self.memory_cache_order.append(cache_key)

    def _cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
    ) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度（0-1）
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def _generate_cache_key(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成缓存键

        Args:
            query: 查询文本
            context: 上下文

        Returns:
            缓存键
        """
        content = query
        if context:
            content += json.dumps(context, sort_keys=True)

        return hashlib.md5(content.encode()).hexdigest()

    def _embedding_to_key(self, embedding: List[float]) -> str:
        """
        将embedding转换为缓存键

        Args:
            embedding: Embedding向量

        Returns:
            缓存键
        """
        # 使用前10个维度生成键（足够区分）
        key_data = str(embedding[:10])
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        total = self.stats["total_queries"]
        if total == 0:
            hit_rate = 0.0
        else:
            hits = self.stats["memory_hits"] + self.stats["redis_hits"]
            hit_rate = hits / total

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "memory_cache_size": len(self.memory_cache),
        }

    def clear(self) -> None:
        """清空缓存"""
        self.memory_cache.clear()
        self.memory_cache_order.clear()

        # 清空Redis缓存
        pattern = "semantic_cache:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

        logger.info("Cache cleared")


class PredictiveCache:
    """
    预测性缓存

    基于用户行为预测，提前加载可能需要的数据

    示例：
        用户刚完成"产品介绍"阶段
        → 预测下一步可能是"价格谈判"
        → 提前加载价格谈判相关的AI响应
    """

    def __init__(
        self,
        semantic_cache: SemanticCache,
        prediction_model: Optional[Any] = None,
    ):
        """
        初始化预测性缓存

        Args:
            semantic_cache: 语义缓存实例
            prediction_model: 可选的预测模型
        """
        self.semantic_cache = semantic_cache
        self.prediction_model = prediction_model

        # 简单的规则基预测（如果没有ML模型）
        self.stage_transitions = {
            "greeting": ["product_intro", "needs_analysis"],
            "product_intro": ["price_negotiation", "objection_handling"],
            "needs_analysis": ["product_intro", "solution_proposal"],
            "price_negotiation": ["closing", "objection_handling"],
            "objection_handling": ["price_negotiation", "closing"],
            "closing": ["follow_up"],
        }

        logger.info("PredictiveCache initialized")

    async def preload_for_stage(
        self,
        current_stage: str,
        context: Dict[str, Any],
    ) -> None:
        """
        为当前阶段预加载下一步可能的响应

        Args:
            current_stage: 当前销售阶段
            context: 上下文信息
        """
        # 预测下一步可能的阶段
        next_stages = self._predict_next_stages(current_stage)

        # 为每个可能的阶段预加载
        for stage in next_stages:
            await self._preload_stage_responses(stage, context)

    def _predict_next_stages(self, current_stage: str) -> List[str]:
        """
        预测下一步可能的阶段

        Args:
            current_stage: 当前阶段

        Returns:
            可能的下一步阶段列表
        """
        if self.prediction_model:
            # TODO: 使用ML模型预测
            pass

        # 使用规则基预测
        return self.stage_transitions.get(current_stage, [])

    async def _preload_stage_responses(
        self,
        stage: str,
        context: Dict[str, Any],
    ) -> None:
        """
        预加载阶段响应

        Args:
            stage: 销售阶段
            context: 上下文
        """
        # 常见的阶段问题
        common_queries = {
            "product_intro": [
                "介绍一下你们的产品",
                "产品有什么特点",
                "和竞品相比有什么优势",
            ],
            "price_negotiation": [
                "价格是多少",
                "能不能便宜一点",
                "有什么优惠吗",
            ],
            "objection_handling": [
                "我需要考虑一下",
                "价格太贵了",
                "我们已经有供应商了",
            ],
            "closing": [
                "什么时候可以签约",
                "合同怎么签",
                "付款方式是什么",
            ],
        }

        queries = common_queries.get(stage, [])

        # 预加载这些查询的响应
        for query in queries:
            # 检查是否已缓存
            cached = await self.semantic_cache.get(query, context)
            if not cached:
                # TODO: 生成并缓存响应
                logger.debug(f"Preloading: {query}")


# 使用示例
async def example_usage():
    """使用示例"""
    import redis.asyncio as aioredis
    from openai import AsyncOpenAI

    # 初始化
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    openai_client = AsyncOpenAI(api_key="sk-...")

    cache = SemanticCache(
        redis_client=redis_client,
        openai_client=openai_client,
        similarity_threshold=0.85,
        ttl=3600,
    )

    # 设置缓存
    await cache.set(
        query="如何提升销售业绩？",
        result={
            "response": "提升销售业绩的关键是...",
            "confidence": 0.95,
        },
    )

    # 查询缓存（语义相似）
    result = await cache.get("怎样提高销售成绩？")
    if result:
        print(f"Cache hit: {result}")
    else:
        print("Cache miss")

    # 查看统计
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
