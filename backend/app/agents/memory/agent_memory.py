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

        logger.info(f"AgentMemory initialized for {agent_id}")

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

        在生产环境中，应该使用真实的嵌入模型（如BGE-M3）
        这里使用简单的TF-IDF模拟
        """
        # Simple hash-based embedding for demo
        # In production, use real embedding model
        import hashlib

        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to 128-dim vector
        embedding = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)
        embedding = np.tile(embedding, 8)[:128]  # Extend to 128 dims

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

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
