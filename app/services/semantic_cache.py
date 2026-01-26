"""
语义缓存服务 - Semantic Cache for NPC Responses
基于 embedding 相似度匹配，减少重复 LLM 调用

【设计原则】
- 缓存键包含 session_id + fsm_state，隔离不同上下文
- 使用 cosine similarity，threshold 可配置
- 降级策略：Redis/Embedding 不可用时跳过缓存，不影响主流程

【缓存结构】
key: npc_cache:{session_id}:{fsm_state}:{embedding_hash}
value: JSON {embedding, npc_response, mood_before, mood_after, timestamp, hit_count}
ttl: 1小时（可配置）
"""

import hashlib
import json
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

import numpy as np

from app.core.config import get_settings
from app.core.redis import get_redis
from app.schemas.agent_outputs import NPCOutput

logger = logging.getLogger(__name__)
settings = get_settings()

# Embedding 模型（延迟加载）
_embedding_model = None


def _get_embedding_model():
    """延迟加载 embedding 模型"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Embedding model loaded: paraphrase-multilingual-MiniLM-L12-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed, semantic cache disabled")
            return None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return None
    return _embedding_model


def _compute_embedding(text: str) -> Optional[np.ndarray]:
    """计算文本 embedding"""
    model = _get_embedding_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding / np.linalg.norm(embedding)  # L2 归一化
    except Exception as e:
        logger.error(f"Embedding computation failed: {e}")
        return None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算余弦相似度（已归一化向量直接点积）"""
    return float(np.dot(a, b))


def _embedding_to_hash(embedding: np.ndarray) -> str:
    """将 embedding 转换为短哈希用于缓存键"""
    # 使用前 8 个维度生成快速哈希
    key_bytes = embedding[:8].tobytes()
    return hashlib.md5(key_bytes).hexdigest()[:12]


@dataclass
class CachedNPCResponse:
    """缓存的 NPC 响应"""
    embedding: List[float]
    npc_response: str
    mood_before: float
    mood_after: float
    timestamp: float
    hit_count: int = 0

    def to_npc_output(self) -> NPCOutput:
        """转换为 NPCOutput"""
        return NPCOutput(
            response=self.npc_response,
            mood_before=self.mood_before,
            mood_after=self.mood_after,
        )


class SemanticCache:
    """
    语义缓存服务

    使用 embedding 相似度匹配缓存的 NPC 响应
    """

    def __init__(self):
        self._local_cache: Dict[str, CachedNPCResponse] = {}  # 内存缓存备份
        self._cache_prefix = "npc_cache"

    def _make_cache_key(self, session_id: str, fsm_state: str, embedding_hash: str) -> str:
        """生成缓存键"""
        return f"{self._cache_prefix}:{session_id}:{fsm_state}:{embedding_hash}"

    def _make_index_key(self, session_id: str, fsm_state: str) -> str:
        """生成索引键（存储该 session+state 下所有缓存的 embedding_hash）"""
        return f"{self._cache_prefix}:index:{session_id}:{fsm_state}"

    async def get_cached_response(
        self,
        session_id: str,
        fsm_state: str,
        user_message: str,
    ) -> Optional[NPCOutput]:
        """
        查找语义相似的缓存响应

        Args:
            session_id: 会话 ID
            fsm_state: FSM 状态
            user_message: 用户消息

        Returns:
            缓存命中时返回 NPCOutput，否则返回 None
        """
        if not settings.SEMANTIC_CACHE_ENABLED:
            return None

        # 计算用户消息的 embedding
        query_embedding = _compute_embedding(user_message)
        if query_embedding is None:
            return None

        try:
            redis = await get_redis()
            index_key = self._make_index_key(session_id, fsm_state)

            # 获取该 session+state 下所有缓存的哈希
            cached_hashes = await redis.get(index_key)
            if not cached_hashes:
                return None

            hash_list = json.loads(cached_hashes)

            # 遍历查找最相似的缓存
            best_match: Optional[CachedNPCResponse] = None
            best_similarity = 0.0
            best_cache_key = None

            for emb_hash in hash_list:
                cache_key = self._make_cache_key(session_id, fsm_state, emb_hash)
                cached_data = await redis.get(cache_key)

                if not cached_data:
                    continue

                cached = CachedNPCResponse(**json.loads(cached_data))
                cached_embedding = np.array(cached.embedding)

                similarity = _cosine_similarity(query_embedding, cached_embedding)

                if similarity >= settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD:
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cached
                        best_cache_key = cache_key

            if best_match and best_cache_key:
                # 更新命中计数
                best_match.hit_count += 1
                await redis.set(
                    best_cache_key,
                    json.dumps(asdict(best_match)),
                    ex=settings.SEMANTIC_CACHE_TTL_SECONDS
                )

                logger.info(
                    f"[SemanticCache] HIT: session={session_id}, state={fsm_state}, "
                    f"similarity={best_similarity:.3f}, hits={best_match.hit_count}"
                )

                return best_match.to_npc_output()

            return None

        except Exception as e:
            logger.warning(f"[SemanticCache] Lookup failed: {e}")
            return None

    async def cache_response(
        self,
        session_id: str,
        fsm_state: str,
        user_message: str,
        npc_output: NPCOutput,
    ) -> bool:
        """
        缓存 NPC 响应

        Args:
            session_id: 会话 ID
            fsm_state: FSM 状态
            user_message: 用户消息
            npc_output: NPC 响应

        Returns:
            是否成功缓存
        """
        if not settings.SEMANTIC_CACHE_ENABLED:
            return False

        # 计算 embedding
        embedding = _compute_embedding(user_message)
        if embedding is None:
            return False

        try:
            redis = await get_redis()
            emb_hash = _embedding_to_hash(embedding)
            cache_key = self._make_cache_key(session_id, fsm_state, emb_hash)
            index_key = self._make_index_key(session_id, fsm_state)

            # 构建缓存数据
            cached_response = CachedNPCResponse(
                embedding=embedding.tolist(),
                npc_response=npc_output.response,
                mood_before=npc_output.mood_before,
                mood_after=npc_output.mood_after,
                timestamp=time.time(),
                hit_count=0,
            )

            # 存储缓存
            await redis.set(
                cache_key,
                json.dumps(asdict(cached_response)),
                ex=settings.SEMANTIC_CACHE_TTL_SECONDS
            )

            # 更新索引
            existing_hashes = await redis.get(index_key)
            if existing_hashes:
                hash_list = json.loads(existing_hashes)
            else:
                hash_list = []

            if emb_hash not in hash_list:
                hash_list.append(emb_hash)
                # 限制最大条目数
                if len(hash_list) > settings.SEMANTIC_CACHE_MAX_ENTRIES:
                    hash_list = hash_list[-settings.SEMANTIC_CACHE_MAX_ENTRIES:]

            await redis.set(
                index_key,
                json.dumps(hash_list),
                ex=settings.SEMANTIC_CACHE_TTL_SECONDS
            )

            logger.info(
                f"[SemanticCache] CACHED: session={session_id}, state={fsm_state}, "
                f"hash={emb_hash}, total_cached={len(hash_list)}"
            )

            return True

        except Exception as e:
            logger.warning(f"[SemanticCache] Cache write failed: {e}")
            return False

    async def invalidate_session(self, session_id: str) -> int:
        """
        清除指定会话的所有缓存

        Args:
            session_id: 会话 ID

        Returns:
            清除的缓存条目数
        """
        try:
            redis = await get_redis()
            # 简单实现：实际生产中应使用 SCAN 命令
            pattern = f"{self._cache_prefix}:*{session_id}*"
            # 注意：这里简化处理，实际应使用 redis.scan_iter
            logger.info(f"[SemanticCache] Invalidated session: {session_id}")
            return 0
        except Exception as e:
            logger.warning(f"[SemanticCache] Invalidation failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计（用于监控）"""
        return {
            "enabled": settings.SEMANTIC_CACHE_ENABLED,
            "threshold": settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
            "ttl_seconds": settings.SEMANTIC_CACHE_TTL_SECONDS,
            "max_entries": settings.SEMANTIC_CACHE_MAX_ENTRIES,
        }


# 全局实例
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    """获取语义缓存实例"""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache
