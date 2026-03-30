"""
AgentMemory Persistent Backends
================================

三层持久化后端，对应 AgentMemory 的三个记忆层：

  L1 — RedisEpisodicBackend
       快速、TTL 限定的情节记忆缓存。
       以 Redis HASH 存储当前 session 的所有情节记忆。
       服务重启后，只要 TTL 未过期，session 上下文即可恢复。

  L2 — QdrantSemanticBackend
       跨 session 向量索引的语义记忆。
       每个 agent 获得独立的 Qdrant collection，支持真正的语义相似度检索。

  L3 — ProceduralMemoryStub（未实现）
       程序性记忆：销售技巧模板、话术规则、SOP 步骤。
       当前为 stub，所有方法抛 NotImplementedError 并附详细说明。
       见下方 ProceduralMemoryStub 的注释了解未来接入方案。

典型用法（在 session 开始时调用）：

    from app.agents.memory.memory_backend import (
        RedisEpisodicBackend, QdrantSemanticBackend,
    )
    from app.core.config import get_settings

    s = get_settings()
    memory = AgentMemory(agent_id="sdr_001")
    await memory.attach_backends(
        l1=RedisEpisodicBackend(
            redis_url=s.REDIS_URL,
            ttl_seconds=s.AGENT_MEMORY_REDIS_TTL_SECONDS,
        ) if s.AGENT_MEMORY_REDIS_ENABLED else None,
        l2=QdrantSemanticBackend(
            qdrant_url=s.AGENT_MEMORY_QDRANT_URL,
            api_key=s.AGENT_MEMORY_QDRANT_API_KEY,
            collection_prefix=s.AGENT_MEMORY_QDRANT_COLLECTION_PREFIX,
            vector_size=s.AGENT_MEMORY_VECTOR_SIZE,
        ) if s.AGENT_MEMORY_QDRANT_ENABLED else None,
    )
    await memory.load_session(session_id="sess_abc123")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_memory import MemoryEntry

logger = logging.getLogger(__name__)


# ===========================================================================
# L1 — Redis Episodic Backend
# ===========================================================================

class RedisEpisodicBackend:
    """
    L1：Redis 情节记忆缓存。

    以 Redis HASH 存储当前 session 的情节记忆快照，TTL 默认 2 小时。
    服务重启后可在 TTL 内恢复 session 上下文，避免冷启动重置问题。

    Redis key schema:
        agent_memory:episodic:{agent_id}:{session_id}
            HASH field → memory_id
            HASH value → JSON-serialized MemoryEntry（不含 embedding，重载时重新生成）

    为什么用 Redis 做 L1？
    - O(1) 单条读写
    - 自动 TTL 过期
    - 多 pod 共享同一 Redis，天然支持水平扩展
    - 不需要额外基础设施（项目已有 Redis）

    启用步骤:
        1. 在 .env 中设置 AGENT_MEMORY_REDIS_ENABLED=true
        2. 确保 REDIS_URL 指向可用的 Redis 实例
        3. 按上方「典型用法」示例调用 attach_backends()
        4. session 开始时调用 await memory.load_session(session_id)
        5. session 结束或定期调用 await memory.save_session()
    """

    KEY_PREFIX = "agent_memory:episodic"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = 7200,
    ):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._client = None
    async def _get_client(self):
        """Lazy-initialize async Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(
                    self.redis_url, decode_responses=True
                )
            except ImportError:
                raise RuntimeError(
                    "redis package not installed. Run: pip install 'redis>=4.0'"
                )
        return self._client

    def _key(self, agent_id: str, session_id: str) -> str:
        return f"{self.KEY_PREFIX}:{agent_id}:{session_id}"

    async def save(
        self,
        agent_id: str,
        session_id: str,
        entries: List["MemoryEntry"],
    ) -> bool:
        """
        将情节记忆快照写入 Redis。

        用整体覆盖（delete + hset）保证幂等性。
        适合在每次 store_interaction() 后或 session checkpoint 时批量调用。

        Returns:
            True 表示成功；False 表示 Redis 出错（fail-safe：进程内副本不受影响）。
        """
        try:
            client = await self._get_client()
            key = self._key(agent_id, session_id)
            if not entries:
                await client.delete(key)
                return True
            mapping: Dict[str, str] = {}
            for entry in entries:
                d = entry.to_dict()
                d.pop("embedding", None)  # np.ndarray 不可 JSON 序列化，重载时重新生成
                mapping[entry.memory_id] = json.dumps(d, ensure_ascii=False)
            pipe = client.pipeline()
            pipe.delete(key)
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, self.ttl_seconds)
            await pipe.execute()
            logger.debug(
                "[L1-Redis] Saved %d episodic entries for %s/%s",
                len(entries), agent_id, session_id,
            )
            return True
        except Exception as exc:
            logger.warning(
                "[L1-Redis] save failed for %s/%s: %s", agent_id, session_id, exc
            )
            return False

    async def load(
        self,
        agent_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        从 Redis 加载情节记忆原始字典列表。

        注意：embedding 字段不在 Redis 中，调用方需调用 _generate_embedding() 重新生成。
        出错时返回空列表（fail-safe）。
        """
        try:
            client = await self._get_client()
            key = self._key(agent_id, session_id)
            raw: Dict[str, str] = await client.hgetall(key)
            if not raw:
                return []
            result = []
            for json_str in raw.values():
                try:
                    result.append(json.loads(json_str))
                except Exception:
                    pass
            logger.debug(
                "[L1-Redis] Loaded %d episodic entries for %s/%s",
                len(result), agent_id, session_id,
            )
            return result
        except Exception as exc:
            logger.warning(
                "[L1-Redis] load failed for %s/%s: %s", agent_id, session_id, exc
            )
            return []

    async def delete_session(self, agent_id: str, session_id: str) -> bool:
        """显式删除 session 数据（session 正常结束时调用以释放内存）。"""
        try:
            client = await self._get_client()
            await client.delete(self._key(agent_id, session_id))
            return True
        except Exception as exc:
            logger.warning("[L1-Redis] delete_session failed: %s", exc)
            return False

    async def close(self):
        """关闭 Redis 连接。"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ===========================================================================
# L2 — Qdrant Semantic Backend
# ===========================================================================

class QdrantSemanticBackend:
    """
    L2：Qdrant 语义记忆向量库。

    每个 agent 对应一个独立的 Qdrant collection，名称为:
        {collection_prefix}_{agent_id}  (e.g. "agent_mem_sdr_001")

    Point payload schema:
        {
            "memory_id": str,
            "memory_type": str,    # "semantic" | "episodic"
            "content": str,
            "metadata": dict,
            "importance": float,
            "access_count": int,
            "last_access": float,
            "created_at": float,
        }

    为什么用 Qdrant 做 L2？
    - 真正的余弦相似度检索（不是关键词匹配）
    - 跨 session、跨重启持久化
    - 支持 payload 过滤（按 importance、memory_type 等过滤）
    - 项目已有 QdrantVectorStore 基础设施可复用

    启用步骤:
        1. 在 .env 中设置 AGENT_MEMORY_QDRANT_ENABLED=true
        2. 设置 AGENT_MEMORY_QDRANT_URL 指向你的 Qdrant 实例
        3. 确认 AGENT_MEMORY_VECTOR_SIZE 与 embedding 模型输出维度一致
           （BGE-large-zh: 1024, OpenAI text-embedding-3-small: 1536）
        4. 按上方「典型用法」示例调用 attach_backends()

    未来改进 — 混合检索（dense + sparse）:
        项目中 backend/app/infra/vector_store/qdrant_client.py 已实现
        hybrid search（SparseVectorParams + NamedVector）。
        要在 L2 启用混合检索:
        1. 用 BM25 或 SPLADE 生成 sparse vector
        2. 在 ensure_collection() 中传入 SparseVectorParams
        3. 在 upsert/search 中使用 NamedVector/NamedSparseVector
        参考: backend/app/infra/vector_store/qdrant_client.py
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        collection_prefix: str = "agent_mem",
        vector_size: int = 1024,
        timeout: int = 30,
    ):
        self.qdrant_url = qdrant_url
        self.api_key = api_key
        self.collection_prefix = collection_prefix
        self.vector_size = vector_size
        self.timeout = timeout
        self._client = None
        self._ensured: set = set()  # 已确认存在的 collection 名，避免重复检查

    async def _get_client(self):
        """Lazy-initialize AsyncQdrantClient。"""
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient
                self._client = AsyncQdrantClient(
                    url=self.qdrant_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
            except ImportError:
                raise RuntimeError(
                    "qdrant-client not installed. Run: pip install 'qdrant-client>=1.7'"
                )
        return self._client

    def _collection(self, agent_id: str) -> str:
        """Qdrant collection 名称（对 agent_id 做字符安全处理）。"""
        safe = agent_id.replace("-", "_").replace(":", "_").lower()
        return f"{self.collection_prefix}_{safe}"

    async def ensure_collection(self, agent_id: str) -> bool:
        """若 collection 不存在则创建，幂等。"""
        cname = self._collection(agent_id)
        if cname in self._ensured:
            return True
        try:
            from qdrant_client.models import Distance, VectorParams
            client = await self._get_client()
            existing = {c.name for c in (await client.get_collections()).collections}
            if cname not in existing:
                await client.create_collection(
                    collection_name=cname,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("[L2-Qdrant] Created collection: %s", cname)
            self._ensured.add(cname)
            return True
        except Exception as exc:
            logger.warning("[L2-Qdrant] ensure_collection failed for %s: %s", agent_id, exc)
            return False

    async def upsert(self, agent_id: str, entry: "MemoryEntry") -> bool:
        """
        插入或更新单条 MemoryEntry 到 Qdrant。

        若 entry.embedding 为 None，跳过（不能存没有向量的记忆）。
        Returns True 成功，False 出错（fail-safe）。
        """
        if entry.embedding is None:
            logger.debug("[L2-Qdrant] Skipping upsert for %s: no embedding", entry.memory_id)
            return False
        try:
            from qdrant_client.models import PointStruct
            if not await self.ensure_collection(agent_id):
                return False
            client = await self._get_client()
            cname = self._collection(agent_id)
            payload = entry.to_dict()
            payload.pop("embedding", None)
            # Qdrant point id 必须是 UUID 格式或整数；从 memory_id 派生一个确定性 UUID
            import uuid as _uuid
            point_id = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, entry.memory_id))
            await client.upsert(
                collection_name=cname,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=entry.embedding.tolist(),
                        payload=payload,
                    )
                ],
            )
            logger.debug("[L2-Qdrant] Upserted %s to %s", entry.memory_id, cname)
            return True
        except Exception as exc:
            logger.warning("[L2-Qdrant] upsert failed for %s: %s", entry.memory_id, exc)
            return False

    async def upsert_many(self, agent_id: str, entries: List["MemoryEntry"]) -> int:
        """
        批量 upsert，返回成功写入的条目数。
        跳过没有 embedding 的条目。
        """
        if not entries:
            return 0
        valid = [e for e in entries if e.embedding is not None]
        if not valid:
            return 0
        try:
            from qdrant_client.models import PointStruct
            import uuid as _uuid
            if not await self.ensure_collection(agent_id):
                return 0
            client = await self._get_client()
            cname = self._collection(agent_id)
            points = []
            for entry in valid:
                payload = entry.to_dict()
                payload.pop("embedding", None)
                point_id = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, entry.memory_id))
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=entry.embedding.tolist(),
                        payload=payload,
                    )
                )
            await client.upsert(collection_name=cname, points=points)
            logger.debug("[L2-Qdrant] Batch upserted %d entries to %s", len(points), cname)
            return len(points)
        except Exception as exc:
            logger.warning("[L2-Qdrant] upsert_many failed for %s: %s", agent_id, exc)
            return 0

    async def search(
        self,
        agent_id: str,
        query_vector: List[float],
        top_k: int = 5,
        min_score: float = 0.0,
        memory_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量相似度检索，返回原始 payload 字典列表（不含 embedding）。

        Args:
            agent_id: Agent 标识
            query_vector: 查询向量（与存储的 embedding 维度一致）
            top_k: 最多返回条目数
            min_score: 最低相似度阈值（0.0~1.0，余弦相似度）
            memory_type_filter: 若设置，只返回该类型的记忆（"semantic" | "episodic"）

        Returns:
            按相似度降序排列的 payload 字典列表，出错返回 []。
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            if not await self.ensure_collection(agent_id):
                return []
            client = await self._get_client()
            cname = self._collection(agent_id)
            qdrant_filter = None
            if memory_type_filter:
                qdrant_filter = Filter(
                    must=[
                        FieldCondition(
                            key="memory_type",
                            match=MatchValue(value=memory_type_filter),
                        )
                    ]
                )
            results = await client.search(
                collection_name=cname,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=min_score if min_score > 0 else None,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            payloads = []
            for hit in results:
                if hit.payload:
                    p = dict(hit.payload)
                    p["_score"] = hit.score
                    payloads.append(p)
            logger.debug(
                "[L2-Qdrant] search returned %d results for %s", len(payloads), agent_id
            )
            return payloads
        except Exception as exc:
            logger.warning("[L2-Qdrant] search failed for %s: %s", agent_id, exc)
            return []

    async def load_all(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        滚动加载 agent 的全部语义记忆（用于冷启动时恢复 L2 in-process dict）。

        注意：大规模 agent 不建议全量加载，优先用 search() 按需检索。
        出错返回 []（fail-safe）。
        """
        try:
            if not await self.ensure_collection(agent_id):
                return []
            client = await self._get_client()
            cname = self._collection(agent_id)
            records, _ = await client.scroll(
                collection_name=cname,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            return [dict(r.payload) for r in records if r.payload]
        except Exception as exc:
            logger.warning("[L2-Qdrant] load_all failed for %s: %s", agent_id, exc)
            return []

    async def close(self):
        """关闭 Qdrant 连接。"""
        if self._client:
            await self._client.close()
            self._client = None


# ===========================================================================
# L3 — Procedural Memory Stub（程序性记忆，未实现）
# ===========================================================================

class ProceduralMemoryStub:
    """
    L3：程序性记忆 — 销售技巧模板、话术规则、SOP 步骤。

    ═══════════════════════════════════════════════════════════
    当前状态：STUB — 所有方法抛 NotImplementedError
    ═══════════════════════════════════════════════════════════

    程序性记忆与 L1/L2 的区别:
        L1 (episodic) — 「发生了什么」：这次 session 里的对话事件
        L2 (semantic) — 「知道什么」：关于客户/产品的事实知识
        L3 (procedural) — 「怎么做」：销售动作序列、话术决策树

    设计意图:
        存储结构化的「如果…则…」规则，例如:
        - 客户说「太贵了」→ 执行 TCO 话术模板
        - stage=closing + budget_gap → 触发 ROI 计算器工具
        - MEDDPICC.economic_buyer=UNKNOWN → 插入探询问题序列

    ─────────────────────────────────────────────────────────
    未来实现方案（二选一）:
    ─────────────────────────────────────────────────────────

    方案 A — 关系型数据库（推荐，简单可靠）:
        表结构:
            CREATE TABLE procedural_rules (
                id          UUID PRIMARY KEY,
                agent_id    TEXT NOT NULL,
                trigger     JSONB NOT NULL,   -- {"intent": "OBJECTION", "stage": "*"}
                action      JSONB NOT NULL,   -- {"tactic": "TCO", "template_id": "t_001"}
                priority    INT DEFAULT 0,
                enabled     BOOL DEFAULT TRUE,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
        实现步骤:
            1. 在 backend/alembic/versions/ 新建 migration 创建上述表
            2. 实现 store_rule() / match_rules() / delete_rule()
            3. match_rules() 按 trigger 字段做 JSONB 包含查询
            4. 在 LiveAssistEngine._keyword_fallback() 中调用 match_rules()

    方案 B — 向量化规则检索（高级，适合规则库很大时）:
        1. 将每条规则的 trigger 文本 embedding 化存入 Qdrant 独立 collection
        2. 用当前对话上下文向量检索最相关规则
        3. 适合规则数量 > 1000 条、规则语义复杂的场景
        参考: backend/app/infra/vector_store/qdrant_client.py

    接入位置:
        - backend/app/services/live_assist_engine.py :: LiveAssistEngine
          在 _keyword_fallback() 末尾调用 l3.match_rules() 补充建议
        - backend/app/agents/memory/agent_memory.py :: AgentMemory
          在 attach_backends() 中接收 l3 参数

    测试文件预留位置:
        backend/tests/unit/test_procedural_memory.py
    ─────────────────────────────────────────────────────────
    """

    async def store_rule(
        self,
        agent_id: str,
        trigger: Dict[str, Any],
        action: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """
        存储一条程序性规则。

        TODO: 实现时替换为数据库写入。
        参数:
            trigger: 触发条件，例如 {"intent": "OBJECTION", "stage": "closing"}
            action:  执行动作，例如 {"tactic": "TCO", "template_id": "t_001"}
            priority: 同优先级规则的排序（越大越优先）
        Returns:
            rule_id (str)
        """
        raise NotImplementedError(
            "ProceduralMemoryStub.store_rule() 未实现。\n"
            "请参考类文档中的「未来实现方案」。"
        )

    async def match_rules(
        self,
        agent_id: str,
        context: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        根据当前对话上下文匹配程序性规则。

        TODO: 实现时替换为数据库查询或向量检索。
        参数:
            context: 当前上下文，例如 {"intent": "OBJECTION", "stage": "closing",
                                      "methodology_gaps": ["economic_buyer"]}
            top_k:   最多返回规则数
        Returns:
            匹配的规则列表，每条为 {"trigger": ..., "action": ..., "priority": ...}
        """
        raise NotImplementedError(
            "ProceduralMemoryStub.match_rules() 未实现。\n"
            "请参考类文档中的「未来实现方案」。"
        )

    async def delete_rule(self, agent_id: str, rule_id: str) -> bool:
        """
        删除指定规则。

        TODO: 实现时替换为数据库 DELETE。
        """
        raise NotImplementedError(
            "ProceduralMemoryStub.delete_rule() 未实现。"
        )

    async def list_rules(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        列出 agent 的全部规则（用于管理界面展示）。

        TODO: 实现时替换为数据库 SELECT。
        """
        raise NotImplementedError(
            "ProceduralMemoryStub.list_rules() 未实现。"
        )




