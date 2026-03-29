"""
Agent Memory Network - 智能记忆系统

实现多层次记忆架构：
1. 情节记忆 (Episodic Memory) - 存储具体交互事件
2. 语义记忆 (Semantic Memory) - 存储抽象知识和事实
3. 工作记忆 (Working Memory) - 短期活跃信息

使用向量检索实现高效记忆查询。

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """记忆类型"""
    EPISODIC = "episodic"  # 情节记忆
    SEMANTIC = "semantic"  # 语义记忆
    WORKING = "working"    # 工作记忆


@dataclass
class MemoryEntry:
    """记忆条目"""
    memory_id: str
    memory_type: MemoryType
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    importance: float = 0.5  # 0.0-1.0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_access": self.last_access,
            "created_at": self.created_at,
        }


class AgentMemory:
    """
    Agent记忆网络

    核心功能：
    1. 多层次记忆存储
    2. 向量相似度检索
    3. 记忆重要性评估
    4. 记忆遗忘机制
    5. 记忆巩固

    Usage:
        memory = AgentMemory(agent_id="sdr_001")

        # 存储交互
        await memory.store_interaction(
            content="Customer asked about pricing",
            metadata={"customer": "Acme Corp", "intent": "pricing"}
        )

        # 检索相关记忆
        relevant = await memory.retrieve_relevant(
            query="What did customer ask about?",
            top_k=5
        )
    """

    def __init__(
        self,
        agent_id: str,
        max_episodic: int = 1000,
        max_semantic: int = 500,
        max_working: int = 10,
        forgetting_threshold: float = 0.1,
    ):
        """
        Initialize memory system

        Args:
            agent_id: Agent identifier
            max_episodic: Max episodic memories
            max_semantic: Max semantic memories
            max_working: Max working memories
            forgetting_threshold: Importance threshold for forgetting
        """
        self.agent_id = agent_id
        self.max_episodic = max_episodic
        self.max_semantic = max_semantic
        self.max_working = max_working
        self.forgetting_threshold = forgetting_threshold

        # Memory stores
        self.episodic_memory: List[MemoryEntry] = []
        self.semantic_memory: Dict[str, MemoryEntry] = {}
        self.working_memory: List[MemoryEntry] = []

        # Statistics
        self.total_stored = 0
        self.total_retrieved = 0
        self.total_forgotten = 0

        # Persistent backends (attached after construction via attach_backends())
        # L1 = RedisEpisodicBackend  — fast session cache
        # L2 = QdrantSemanticBackend — cross-session vector store
        # L3 = ProceduralMemoryStub  — not yet implemented
        self._l1 = None  # type: Optional[Any]
        self._l2 = None  # type: Optional[Any]
        self._l3 = None  # type: Optional[Any]
        self._session_id: Optional[str] = None

        logger.info(f"AgentMemory initialized for {agent_id}")

    # ------------------------------------------------------------------
    # Backend management
    # ------------------------------------------------------------------

    def attach_backends(self, l1=None, l2=None, l3=None) -> None:
        """
        挂载持久化后端。在 AgentMemory 构造后、load_session() 前调用。

        Args:
            l1: RedisEpisodicBackend 实例（或 None 表示不启用）
            l2: QdrantSemanticBackend 实例（或 None 表示不启用）
            l3: ProceduralMemoryStub 实例（或 None；当前为 stub，未实现）

        示例:
            from app.agents.memory.memory_backend import (
                RedisEpisodicBackend, QdrantSemanticBackend
            )
            memory.attach_backends(
                l1=RedisEpisodicBackend(redis_url=settings.REDIS_URL),
                l2=QdrantSemanticBackend(qdrant_url=settings.AGENT_MEMORY_QDRANT_URL),
            )
        """
        self._l1 = l1
        self._l2 = l2
        self._l3 = l3
        backends = []
        if l1:
            backends.append("L1-Redis")
        if l2:
            backends.append("L2-Qdrant")
        if l3:
            backends.append("L3-Procedural")
        logger.info(
            "[AgentMemory:%s] Backends attached: %s",
            self.agent_id,
            ", ".join(backends) if backends else "none (in-process only)",
        )

    @classmethod
    async def create_with_backends(cls, agent_id: str, **kwargs) -> "AgentMemory":
        """Factory: construct AgentMemory and wire L1/L2 backends from app settings.

        Reads AGENT_MEMORY_REDIS_ENABLED and AGENT_MEMORY_QDRANT_ENABLED from
        config. If disabled, the returned instance runs fully in-process (no
        infra required). Call ``load_session(session_id)`` afterwards to
        restore a prior session.

        Args:
            agent_id: Unique identifier for this agent.
            **kwargs: Forwarded to AgentMemory.__init__ (e.g. max_interactions).

        Returns:
            Fully initialised AgentMemory with backends attached.
        """
        from backend.app.core.config import settings
        from backend.app.agents.memory.memory_backend import (
            RedisEpisodicBackend,
            QdrantSemanticBackend,
        )

        instance = cls(agent_id=agent_id, **kwargs)
        l1 = None
        l2 = None

        if settings.AGENT_MEMORY_REDIS_ENABLED:
            try:
                import redis.asyncio as aioredis
                redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                l1 = RedisEpisodicBackend(
                    redis_client=redis_client,
                    ttl_seconds=settings.AGENT_MEMORY_REDIS_TTL_SECONDS,
                )
                logger.info("AgentMemory L1 Redis attached for agent=%s", agent_id)
            except Exception as exc:
                logger.warning("AgentMemory L1 Redis failed: %s", exc)

        if settings.AGENT_MEMORY_QDRANT_ENABLED:
            try:
                from qdrant_client import AsyncQdrantClient
                qdrant_client = AsyncQdrantClient(
                    url=settings.AGENT_MEMORY_QDRANT_URL,
                    api_key=settings.AGENT_MEMORY_QDRANT_API_KEY,
                )
                collection_name = (
                    f"{settings.AGENT_MEMORY_QDRANT_COLLECTION_PREFIX}_{agent_id}"
                )
                l2 = QdrantSemanticBackend(
                    client=qdrant_client,
                    collection_name=collection_name,
                    vector_size=settings.AGENT_MEMORY_VECTOR_SIZE,
                )
                await l2.ensure_collection()
                logger.info(
                    "AgentMemory L2 Qdrant attached for agent=%s collection=%s",
                    agent_id, collection_name,
                )
            except Exception as exc:
                logger.warning("AgentMemory L2 Qdrant failed: %s", exc)

        # L3 ProceduralMemory is a stub — not yet implemented.
        instance.attach_backends(l1=l1, l2=l2, l3=None)
        return instance

    async def load_session(self, session_id: str) -> None:
        """
        从持久化后端加载 session 记忆到进程内缓存。

        加载顺序:
            1. L1 (Redis) → 恢复情节记忆（本 session 快照）
            2. L2 (Qdrant) → 恢复语义记忆（跨 session 持久化事实）

        任一后端失败时静默降级（fail-safe）：进程内缓存为空但程序正常运行。

        Args:
            session_id: 当前会话 ID（与 LangGraph checkpointer 的 thread_id 保持一致）
        """
        self._session_id = session_id

        # --- L1: Redis episodic ---
        if self._l1 is not None:
            raw_entries = await self._l1.load(self.agent_id, session_id)
            for item in raw_entries:
                try:
                    entry = MemoryEntry(
                        memory_id=item["memory_id"],
                        memory_type=MemoryType(item["memory_type"]),
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                        importance=item.get("importance", 0.5),
                        access_count=item.get("access_count", 0),
                        last_access=item.get("last_access", time.time()),
                        created_at=item.get("created_at", time.time()),
                    )
                    # Re-generate embedding (not stored in Redis)
                    entry.embedding = await self._generate_embedding(entry.content)
                    self.episodic_memory.append(entry)
                except Exception as exc:
                    logger.warning("[AgentMemory] load_session L1 entry error: %s", exc)
            logger.info(
                "[AgentMemory:%s] L1 loaded %d episodic entries for session %s",
                self.agent_id, len(self.episodic_memory), session_id,
            )

        # --- L2: Qdrant semantic ---
        if self._l2 is not None:
            raw_facts = await self._l2.load_all(self.agent_id)
            for item in raw_facts:
                try:
                    key = item.get("memory_id", "")
                    if not key:
                        continue
                    entry = MemoryEntry(
                        memory_id=key,
                        memory_type=MemoryType(item.get("memory_type", "semantic")),
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                        importance=item.get("importance", 0.7),
                        access_count=item.get("access_count", 0),
                        last_access=item.get("last_access", time.time()),
                        created_at=item.get("created_at", time.time()),
                    )
                    entry.embedding = await self._generate_embedding(entry.content)
                    self.semantic_memory[key] = entry
                except Exception as exc:
                    logger.warning("[AgentMemory] load_session L2 entry error: %s", exc)
            logger.info(
                "[AgentMemory:%s] L2 loaded %d semantic entries",
                self.agent_id, len(self.semantic_memory),
            )

    async def save_session(self) -> None:
        """
        将进程内记忆快照写回持久化后端。

        调用时机:
            - session 正常结束时（websocket 断开、用户登出）
            - 定期 checkpoint（推荐每 N 条交互后调用一次）

        写入策略:
            L1 (Redis): 保存全部情节记忆 + 工作记忆（当前 session 快照）
            L2 (Qdrant): 批量 upsert 全部语义记忆

        任一后端失败时静默降级，不影响进程内副本。
        """
        if self._session_id is None:
            logger.debug("[AgentMemory:%s] save_session called but no session_id set", self.agent_id)
            return

        if self._l1 is not None:
            all_episodic = list(self.episodic_memory) + list(self.working_memory)
            ok = await self._l1.save(self.agent_id, self._session_id, all_episodic)
            if ok:
                logger.info(
                    "[AgentMemory:%s] L1 saved %d entries", self.agent_id, len(all_episodic)
                )

        if self._l2 is not None:
            semantic_entries = list(self.semantic_memory.values())
            n = await self._l2.upsert_many(self.agent_id, semantic_entries)
            logger.info("[AgentMemory:%s] L2 upserted %d semantic entries", self.agent_id, n)

    async def store_interaction(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """
        存储交互到情节记忆

        Args:
            content: Memory content
            metadata: Additional metadata
            importance: Importance score (0.0-1.0)

        Returns:
            Memory ID
        """
        import uuid

        memory_id = f"ep_{uuid.uuid4().hex[:12]}"
        metadata = metadata or {}

        # Create memory entry
        entry = MemoryEntry(
            memory_id=memory_id,
            memory_type=MemoryType.EPISODIC,
            content=content,
            metadata=metadata,
            importance=importance,
        )

        # Generate embedding
        entry.embedding = await self._generate_embedding(content)

        # Store to episodic memory
        self.episodic_memory.append(entry)
        self.total_stored += 1

        # Also add to working memory
        await self._add_to_working_memory(entry)

        # Persist to L1 (Redis) — async, fail-safe
        if self._l1 is not None and self._session_id is not None:
            await self._l1.save(
                self.agent_id, self._session_id, self.episodic_memory
            )

        # Extract facts to semantic memory
        await self._extract_semantic_facts(entry)

        # Trigger forgetting if needed
        if len(self.episodic_memory) > self.max_episodic:
            await self._forget_unimportant_memories()

        logger.debug(f"Stored episodic memory: {memory_id}")
        return memory_id

    async def store_fact(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.7,
    ) -> str:
        """
        存储事实到语义记忆

        Args:
            key: Fact key (e.g., "customer_preference")
            content: Fact content
            metadata: Additional metadata
            importance: Importance score

        Returns:
            Memory ID
        """
        import uuid

        memory_id = f"sem_{uuid.uuid4().hex[:12]}"
        metadata = metadata or {}

        entry = MemoryEntry(
            memory_id=memory_id,
            memory_type=MemoryType.SEMANTIC,
            content=content,
            metadata=metadata,
            importance=importance,
        )

        entry.embedding = await self._generate_embedding(content)

        # Store or update
        if key in self.semantic_memory:
            # Update existing fact
            old_entry = self.semantic_memory[key]
            entry.access_count = old_entry.access_count
            logger.debug(f"Updated semantic fact: {key}")
        else:
            logger.debug(f"Stored new semantic fact: {key}")

        self.semantic_memory[key] = entry
        self.total_stored += 1

        # Persist to L2 (Qdrant) — async, fail-safe
        if self._l2 is not None:
            await self._l2.upsert(self.agent_id, entry)

        # Limit semantic memory size
        if len(self.semantic_memory) > self.max_semantic:
            await self._prune_semantic_memory()

        return memory_id

    async def retrieve_relevant(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5,
        min_importance: float = 0.0,
    ) -> List[MemoryEntry]:
        """
        检索相关记忆

        Args:
            query: Query text
            memory_type: Filter by memory type (optional)
            top_k: Number of results
            min_importance: Minimum importance threshold

        Returns:
            List of relevant memories
        """
        query_embedding = await self._generate_embedding(query)

        # Collect candidate memories
        candidates: List[MemoryEntry] = []

        if memory_type is None or memory_type == MemoryType.EPISODIC:
            candidates.extend(self.episodic_memory)

        if memory_type is None or memory_type == MemoryType.SEMANTIC:
            candidates.extend(self.semantic_memory.values())

        if memory_type is None or memory_type == MemoryType.WORKING:
            candidates.extend(self.working_memory)

        # Filter by importance
        candidates = [m for m in candidates if m.importance >= min_importance]

        if not candidates:
            return []

        # Calculate similarities
        similarities = []
        for memory in candidates:
            if memory.embedding is not None:
                sim = self._cosine_similarity(query_embedding, memory.embedding)
                # Boost by importance and recency
                recency_boost = self._calculate_recency_boost(memory)
                importance_boost = memory.importance
                final_score = sim * 0.6 + recency_boost * 0.2 + importance_boost * 0.2
                similarities.append((memory, final_score))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top-k
        results = [m for m, _ in similarities[:top_k]]

        # Update access statistics
        for memory in results:
            memory.access_count += 1
            memory.last_access = time.time()

        self.total_retrieved += len(results)

        # Augment with L2 (Qdrant) vector search — finds cross-session semantic memories
        # not yet loaded into the in-process dict.
        if self._l2 is not None and query_embedding is not None:
            try:
                remote_payloads = await self._l2.search(
                    agent_id=self.agent_id,
                    query_vector=query_embedding.tolist(),
                    top_k=top_k,
                    min_score=0.5,
                    memory_type_filter=(
                        memory_type.value if memory_type is not None else None
                    ),
                )
                known_ids = {m.memory_id for m in results}
                for payload in remote_payloads:
                    mid = payload.get("memory_id", "")
                    if mid and mid not in known_ids:
                        try:
                            remote_entry = MemoryEntry(
                                memory_id=mid,
                                memory_type=MemoryType(payload.get("memory_type", "semantic")),
                                content=payload["content"],
                                metadata=payload.get("metadata", {}),
                                importance=payload.get("importance", 0.5),
                                access_count=payload.get("access_count", 0),
                                last_access=payload.get("last_access", time.time()),
                                created_at=payload.get("created_at", time.time()),
                            )
                            results.append(remote_entry)
                            known_ids.add(mid)
                        except Exception:
                            pass
                # Re-sort after augmentation and re-apply top_k
                results = results[:top_k]
            except Exception as exc:
                logger.debug("[AgentMemory] L2 augment failed (non-fatal): %s", exc)

        logger.debug(f"Retrieved {len(results)} relevant memories for query: {query[:50]}")
        return results

    async def get_working_memory(self) -> List[MemoryEntry]:
        """获取工作记忆（当前活跃信息）"""
        return self.working_memory.copy()

    async def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory.clear()
        logger.debug("Working memory cleared")

    async def consolidate_memories(self):
        """
        记忆巩固

        将重要的情节记忆提取为语义记忆
        """
        # Find high-importance episodic memories
        important_episodes = [
            m for m in self.episodic_memory
            if m.importance > 0.7 and m.access_count > 2
        ]

        consolidated = 0
        for episode in important_episodes:
            # Extract key facts
            facts = await self._extract_facts_from_episode(episode)

            for key, content in facts.items():
                await self.store_fact(
                    key=key,
                    content=content,
                    metadata={"source": episode.memory_id},
                    importance=episode.importance,
                )
                consolidated += 1

        logger.info(f"Consolidated {consolidated} facts from episodic memory")

    async def _add_to_working_memory(self, entry: MemoryEntry):
        """添加到工作记忆"""
        self.working_memory.append(entry)

        # Limit working memory size (FIFO)
        if len(self.working_memory) > self.max_working:
            removed = self.working_memory.pop(0)
            logger.debug(f"Removed from working memory: {removed.memory_id}")

    async def _extract_semantic_facts(self, entry: MemoryEntry):
        """从情节记忆提取语义事实"""
        # Simple extraction based on metadata
        metadata = entry.metadata

        # Extract customer preferences
        if "customer" in metadata and "preference" in entry.content.lower():
            key = f"customer_{metadata['customer']}_preference"
            await self.store_fact(
                key=key,
                content=entry.content,
                metadata={"extracted_from": entry.memory_id},
                importance=0.6,
            )

        # Extract objections
        if "objection" in metadata or "concern" in entry.content.lower():
            key = f"objection_{metadata.get('objection_type', 'general')}"
            await self.store_fact(
                key=key,
                content=entry.content,
                metadata={"extracted_from": entry.memory_id},
                importance=0.7,
            )

    async def _extract_facts_from_episode(self, episode: MemoryEntry) -> Dict[str, str]:
        """从情节中提取事实"""
        facts = {}

        # Extract based on metadata
        if "customer" in episode.metadata:
            customer = episode.metadata["customer"]
            facts[f"customer_{customer}_interaction"] = episode.content

        if "intent" in episode.metadata:
            intent = episode.metadata["intent"]
            facts[f"intent_{intent}_example"] = episode.content

        return facts

    async def _forget_unimportant_memories(self):
        """遗忘不重要的记忆"""
        # Calculate forgetting scores
        scores = []
        for memory in self.episodic_memory:
            # Forgetting score based on importance, recency, and access
            recency = (time.time() - memory.last_access) / 86400  # days
            forget_score = (
                (1 - memory.importance) * 0.5 +
                min(recency / 30, 1.0) * 0.3 +
                (1 / (memory.access_count + 1)) * 0.2
            )
            scores.append((memory, forget_score))

        # Sort by forgetting score (higher = more likely to forget)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Forget top 10% least important
        num_to_forget = max(1, len(self.episodic_memory) // 10)
        to_forget = [m for m, _ in scores[:num_to_forget]]

        for memory in to_forget:
            self.episodic_memory.remove(memory)
            self.total_forgotten += 1

        logger.info(f"Forgot {len(to_forget)} unimportant memories")

    async def _prune_semantic_memory(self):
        """修剪语义记忆"""
        # Remove least accessed facts
        facts = list(self.semantic_memory.items())
        facts.sort(key=lambda x: x[1].access_count)

        num_to_remove = len(facts) - self.max_semantic
        for key, _ in facts[:num_to_remove]:
            del self.semantic_memory[key]
            self.total_forgotten += 1

        logger.info(f"Pruned {num_to_remove} semantic facts")

    async def _generate_embedding(self, text: str) -> np.ndarray:
        """
        生成文本嵌入

        使用 EmbeddingModelManager (BGE/OpenAI) 生成真实语义向量。
        MD5 回退已移除：伪 embedding 会导致语义检索完全失效。
        """
        try:
            from ...infra.search.embedding_manager import EmbeddingModelManager

            manager = EmbeddingModelManager.get_instance()
            emb_list = manager.encode_single(text or " ")
            return np.array(emb_list, dtype=np.float32)
        except Exception as e:
            raise RuntimeError(
                f"AgentMemory requires EmbeddingManager for semantic retrieval. "
                f"Configure BGE/OpenAI embedding and ensure embedding_manager is initialized. Original: {e}"
            ) from e

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _calculate_recency_boost(self, memory: MemoryEntry) -> float:
        """计算时间新近性加成"""
        age_days = (time.time() - memory.created_at) / 86400
        # Exponential decay
        return np.exp(-age_days / 7)  # Half-life of 7 days

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        return {
            "agent_id": self.agent_id,
            "episodic_count": len(self.episodic_memory),
            "semantic_count": len(self.semantic_memory),
            "working_count": len(self.working_memory),
            "total_stored": self.total_stored,
            "total_retrieved": self.total_retrieved,
            "total_forgotten": self.total_forgotten,
            "avg_episodic_importance": np.mean([m.importance for m in self.episodic_memory]) if self.episodic_memory else 0.0,
            "avg_semantic_importance": np.mean([m.importance for m in self.semantic_memory.values()]) if self.semantic_memory else 0.0,
        }

    async def save_to_disk(self, filepath: str):
        """保存记忆到磁盘"""
        data = {
            "agent_id": self.agent_id,
            "episodic": [m.to_dict() for m in self.episodic_memory],
            "semantic": {k: v.to_dict() for k, v in self.semantic_memory.items()},
            "stats": self.get_stats(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Memory saved to {filepath}")

    async def load_from_disk(self, filepath: str):
        """从磁盘加载记忆"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Load episodic memories
        self.episodic_memory = []
        for item in data.get("episodic", []):
            entry = MemoryEntry(
                memory_id=item["memory_id"],
                memory_type=MemoryType(item["memory_type"]),
                content=item["content"],
                metadata=item["metadata"],
                importance=item["importance"],
                access_count=item["access_count"],
                last_access=item["last_access"],
                created_at=item["created_at"],
            )
            # Regenerate embedding
            entry.embedding = await self._generate_embedding(entry.content)
            self.episodic_memory.append(entry)

        # Load semantic memories
        self.semantic_memory = {}
        for key, item in data.get("semantic", {}).items():
            entry = MemoryEntry(
                memory_id=item["memory_id"],
                memory_type=MemoryType(item["memory_type"]),
                content=item["content"],
                metadata=item["metadata"],
                importance=item["importance"],
                access_count=item["access_count"],
                last_access=item["last_access"],
                created_at=item["created_at"],
            )
            entry.embedding = await self._generate_embedding(entry.content)
            self.semantic_memory[key] = entry

        logger.info(f"Memory loaded from {filepath}")

    # ------------------------------------------------------------------
    # L1 → L2 promotion
    # L1 = in-process episodic list (fast, volatile)
    # L2 = semantic memory dict (slower, durable within session)
    # Entries with importance >= threshold are promoted to L2 so they
    # survive beyond the working-memory window.
    # ------------------------------------------------------------------
    PROMOTION_THRESHOLD: float = 0.75

    async def maybe_promote(self, entry: MemoryEntry) -> bool:
        """
        Promote a memory entry from L1 (episodic) to L2 (semantic) when its
        importance score meets or exceeds PROMOTION_THRESHOLD.

        Returns True if the entry was promoted, False otherwise.
        """
        if entry.importance < self.PROMOTION_THRESHOLD:
            return False

        key = entry.memory_id
        if key in self.semantic_memory:
            # Already promoted — update importance if higher
            if entry.importance > self.semantic_memory[key].importance:
                self.semantic_memory[key].importance = entry.importance
            return False  # Not a new promotion

        # Copy to L2
        promoted = MemoryEntry(
            memory_id=entry.memory_id,
            memory_type=MemoryType.SEMANTIC,
            content=entry.content,
            metadata={**entry.metadata, "promoted_from": "episodic"},
            embedding=entry.embedding,
            importance=entry.importance,
            access_count=entry.access_count,
            last_access=entry.last_access,
            created_at=entry.created_at,
        )
        self.semantic_memory[key] = promoted
        logger.debug(
            "[AgentMemory] Promoted entry %s to L2 (importance=%.2f)",
            key, entry.importance,
        )

        # Persist promoted entry to Qdrant L2 — async, fail-safe
        if self._l2 is not None:
            await self._l2.upsert(self.agent_id, promoted)

        return True
