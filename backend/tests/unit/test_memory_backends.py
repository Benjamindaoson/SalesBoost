"""
Unit Tests: AgentMemory Persistent Backends
===========================================

覆盖范围:
  - RedisEpisodicBackend: save / load / delete_session（mock aioredis）
  - QdrantSemanticBackend: ensure_collection / upsert / upsert_many / search / load_all（mock AsyncQdrantClient）
  - ProceduralMemoryStub: 所有方法必须抛 NotImplementedError
  - AgentMemory.attach_backends / load_session / save_session 集成流程（双 mock）
  - store_interaction / store_fact / maybe_promote → 写后自动触发后端持久化
"""

from __future__ import annotations

import json
import time
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.memory.memory_backend import (
    RedisEpisodicBackend,
    QdrantSemanticBackend,
    ProceduralMemoryStub,
)
from app.agents.memory.agent_memory import AgentMemory, MemoryEntry, MemoryType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    memory_id: str = "ep_abc123",
    memory_type: MemoryType = MemoryType.EPISODIC,
    content: str = "客户对价格有异议",
    importance: float = 0.8,
) -> MemoryEntry:
    entry = MemoryEntry(
        memory_id=memory_id,
        memory_type=memory_type,
        content=content,
        metadata={"session": "s1"},
        importance=importance,
    )
    entry.embedding = np.ones(1024, dtype=np.float32)
    return entry


# ===========================================================================
# RedisEpisodicBackend
# ===========================================================================

class TestRedisEpisodicBackend:
    @pytest.fixture
    def backend(self):
        return RedisEpisodicBackend(redis_url="redis://localhost:6379/0", ttl_seconds=3600)

    @pytest.fixture
    def mock_redis(self):
        """Simulate aioredis pipeline + hgetall interface."""
        client = AsyncMock()
        pipe = AsyncMock()
        pipe.delete = AsyncMock()
        pipe.hset = AsyncMock()
        pipe.expire = AsyncMock()
        pipe.execute = AsyncMock(return_value=[1, 1, 1])
        client.pipeline = MagicMock(return_value=pipe)
        client.hgetall = AsyncMock(return_value={})
        client.delete = AsyncMock(return_value=1)
        return client, pipe

    async def test_save_stores_entries(self, backend, mock_redis):
        client, pipe = mock_redis
        backend._client = client

        entries = [_make_entry("ep_001"), _make_entry("ep_002", importance=0.6)]
        result = await backend.save("agent_1", "sess_1", entries)

        assert result is True
        pipe.hset.assert_called_once()
        # mapping kwarg should have 2 keys
        _, kwargs = pipe.hset.call_args
        assert len(kwargs["mapping"]) == 2
        pipe.expire.assert_called_once_with("agent_memory:episodic:agent_1:sess_1", 3600)

    async def test_save_empty_entries_deletes_key(self, backend, mock_redis):
        client, _ = mock_redis
        backend._client = client

        result = await backend.save("agent_1", "sess_1", [])
        assert result is True
        client.delete.assert_called_once()

    async def test_save_embedding_not_in_payload(self, backend, mock_redis):
        """embedding (np.ndarray) must be stripped before JSON serialization."""
        client, pipe = mock_redis
        backend._client = client

        entry = _make_entry("ep_x")
        assert entry.embedding is not None  # has embedding
        await backend.save("agent_1", "sess_1", [entry])

        _, kwargs = pipe.hset.call_args
        serialized = list(kwargs["mapping"].values())[0]
        d = json.loads(serialized)
        assert "embedding" not in d

    async def test_load_returns_dicts(self, backend, mock_redis):
        client, _ = mock_redis
        sample = _make_entry("ep_001").to_dict()
        sample.pop("embedding", None)
        client.hgetall = AsyncMock(
            return_value={"ep_001": json.dumps(sample, ensure_ascii=False)}
        )
        backend._client = client

        result = await backend.load("agent_1", "sess_1")
        assert len(result) == 1
        assert result[0]["memory_id"] == "ep_001"

    async def test_load_returns_empty_on_miss(self, backend, mock_redis):
        client, _ = mock_redis
        client.hgetall = AsyncMock(return_value={})
        backend._client = client

        result = await backend.load("agent_1", "no_such_session")
        assert result == []

    async def test_save_returns_false_on_redis_error(self, backend):
        """Redis errors must NOT propagate; return False instead."""
        backend._client = AsyncMock()
        backend._client.pipeline = MagicMock(side_effect=Exception("connection refused"))

        result = await backend.save("a", "s", [_make_entry()])
        assert result is False

    async def test_load_returns_empty_on_redis_error(self, backend):
        backend._client = AsyncMock()
        backend._client.hgetall = AsyncMock(side_effect=Exception("timeout"))

        result = await backend.load("a", "s")
        assert result == []

    async def test_delete_session(self, backend, mock_redis):
        client, _ = mock_redis
        backend._client = client

        result = await backend.delete_session("agent_1", "sess_1")
        assert result is True
        client.delete.assert_called_once()


# ===========================================================================
# QdrantSemanticBackend
# ===========================================================================

class TestQdrantSemanticBackend:
    @pytest.fixture
    def backend(self):
        b = QdrantSemanticBackend(
            qdrant_url="http://localhost:6333",
            collection_prefix="agent_mem",
            vector_size=1024,
        )
        return b

    def _mock_qdrant_client(self):
        """Return a mock AsyncQdrantClient."""
        client = AsyncMock()
        # get_collections returns object with .collections list
        coll_mock = MagicMock()
        coll_mock.name = "agent_mem_agent_1"
        collections_resp = MagicMock()
        collections_resp.collections = [coll_mock]
        client.get_collections = AsyncMock(return_value=collections_resp)
        client.create_collection = AsyncMock()
        client.upsert = AsyncMock()
        client.search = AsyncMock(return_value=[])
        client.scroll = AsyncMock(return_value=([], None))
        client.close = AsyncMock()
        return client

    async def test_ensure_collection_creates_if_missing(self, backend):
        client = self._mock_qdrant_client()
        # Return empty collection list so it will create
        empty = MagicMock()
        empty.collections = []
        client.get_collections = AsyncMock(return_value=empty)
        backend._client = client

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            result = await backend.ensure_collection("new_agent")

        assert result is True
        client.create_collection.assert_called_once()

    async def test_ensure_collection_skips_if_exists(self, backend):
        client = self._mock_qdrant_client()  # already has agent_mem_agent_1
        backend._client = client

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            result = await backend.ensure_collection("agent_1")

        assert result is True
        client.create_collection.assert_not_called()

    async def test_upsert_skips_entry_without_embedding(self, backend):
        entry = MemoryEntry(
            memory_id="sem_x",
            memory_type=MemoryType.SEMANTIC,
            content="fact",
            metadata={},
        )
        # No embedding set
        client = self._mock_qdrant_client()
        backend._client = client

        result = await backend.upsert("agent_1", entry)
        assert result is False
        client.upsert.assert_not_called()

    async def test_upsert_with_embedding(self, backend):
        entry = _make_entry("sem_001", memory_type=MemoryType.SEMANTIC)
        client = self._mock_qdrant_client()
        backend._client = client
        backend._ensured.add("agent_mem_agent_1")  # skip ensure step

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            result = await backend.upsert("agent_1", entry)

        assert result is True
        client.upsert.assert_called_once()

    async def test_upsert_many_returns_count(self, backend):
        entries = [_make_entry(f"sem_{i}", memory_type=MemoryType.SEMANTIC) for i in range(3)]
        client = self._mock_qdrant_client()
        backend._client = client
        backend._ensured.add("agent_mem_agent_1")

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            count = await backend.upsert_many("agent_1", entries)

        assert count == 3

    async def test_upsert_returns_false_on_error(self, backend):
        entry = _make_entry("sem_err", memory_type=MemoryType.SEMANTIC)
        client = self._mock_qdrant_client()
        client.upsert = AsyncMock(side_effect=Exception("Qdrant down"))
        backend._client = client
        backend._ensured.add("agent_mem_agent_1")

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            result = await backend.upsert("agent_1", entry)

        assert result is False

    async def test_search_returns_payload_dicts(self, backend):
        hit = MagicMock()
        hit.score = 0.92
        hit.payload = {
            "memory_id": "sem_001",
            "memory_type": "semantic",
            "content": "客户预算 50 万",
            "metadata": {},
            "importance": 0.8,
            "access_count": 0,
            "last_access": time.time(),
            "created_at": time.time(),
        }
        client = self._mock_qdrant_client()
        client.search = AsyncMock(return_value=[hit])
        backend._client = client
        backend._ensured.add("agent_mem_agent_1")

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            results = await backend.search("agent_1", [0.1] * 1024, top_k=5)

        assert len(results) == 1
        assert results[0]["memory_id"] == "sem_001"
        assert results[0]["_score"] == 0.92

    async def test_search_returns_empty_on_error(self, backend):
        client = self._mock_qdrant_client()
        client.search = AsyncMock(side_effect=Exception("timeout"))
        backend._client = client
        backend._ensured.add("agent_mem_agent_1")

        with patch("app.agents.memory.memory_backend.QdrantSemanticBackend._get_client", return_value=client):
            backend._client = client
            results = await backend.search("agent_1", [0.1] * 1024)

        assert results == []


# ===========================================================================
# ProceduralMemoryStub
# ===========================================================================

class TestProceduralMemoryStub:
    @pytest.fixture
    def stub(self):
        return ProceduralMemoryStub()

    async def test_store_rule_raises(self, stub):
        with pytest.raises(NotImplementedError):
            await stub.store_rule("agent_1", {"intent": "OBJECTION"}, {"tactic": "TCO"})

    async def test_match_rules_raises(self, stub):
        with pytest.raises(NotImplementedError):
            await stub.match_rules("agent_1", {"intent": "OBJECTION"})

    async def test_delete_rule_raises(self, stub):
        with pytest.raises(NotImplementedError):
            await stub.delete_rule("agent_1", "rule_001")

    async def test_list_rules_raises(self, stub):
        with pytest.raises(NotImplementedError):
            await stub.list_rules("agent_1")


# ===========================================================================
# AgentMemory integration: attach_backends + load_session + save_session
# ===========================================================================

class TestAgentMemoryWithBackends:
    @pytest.fixture
    def memory(self):
        return AgentMemory(agent_id="test_agent", max_episodic=100)

    def _l1_mock(self, load_return=None):
        m = AsyncMock(spec=RedisEpisodicBackend)
        m.load = AsyncMock(return_value=load_return or [])
        m.save = AsyncMock(return_value=True)
        m.delete_session = AsyncMock(return_value=True)
        return m

    def _l2_mock(self, load_all_return=None, search_return=None):
        m = AsyncMock(spec=QdrantSemanticBackend)
        m.load_all = AsyncMock(return_value=load_all_return or [])
        m.upsert = AsyncMock(return_value=True)
        m.upsert_many = AsyncMock(return_value=0)
        m.search = AsyncMock(return_value=search_return or [])
        return m

    def test_attach_backends_sets_fields(self, memory):
        l1 = self._l1_mock()
        l2 = self._l2_mock()
        memory.attach_backends(l1=l1, l2=l2)
        assert memory._l1 is l1
        assert memory._l2 is l2
        assert memory._l3 is None

    async def test_load_session_populates_episodic_from_l1(self, memory):
        entry_dict = _make_entry("ep_001").to_dict()
        entry_dict.pop("embedding", None)
        l1 = self._l1_mock(load_return=[entry_dict])
        l2 = self._l2_mock()
        memory.attach_backends(l1=l1, l2=l2)

        with patch.object(memory, "_generate_embedding", return_value=np.ones(1024)):
            await memory.load_session("sess_abc")

        assert memory._session_id == "sess_abc"
        assert len(memory.episodic_memory) == 1
        assert memory.episodic_memory[0].memory_id == "ep_001"

    async def test_load_session_populates_semantic_from_l2(self, memory):
        sem_dict = _make_entry("sem_001", memory_type=MemoryType.SEMANTIC).to_dict()
        sem_dict.pop("embedding", None)
        l1 = self._l1_mock()
        l2 = self._l2_mock(load_all_return=[sem_dict])
        memory.attach_backends(l1=l1, l2=l2)

        with patch.object(memory, "_generate_embedding", return_value=np.ones(1024)):
            await memory.load_session("sess_abc")

        assert "sem_001" in memory.semantic_memory

    async def test_save_session_calls_both_backends(self, memory):
        l1 = self._l1_mock()
        l2 = self._l2_mock()
        memory.attach_backends(l1=l1, l2=l2)
        memory._session_id = "sess_xyz"
        memory.episodic_memory.append(_make_entry("ep_001"))
        memory.semantic_memory["key1"] = _make_entry("sem_001", memory_type=MemoryType.SEMANTIC)

        await memory.save_session()

        l1.save.assert_called_once()
        l2.upsert_many.assert_called_once()

    async def test_save_session_noop_without_session_id(self, memory):
        l1 = self._l1_mock()
        memory.attach_backends(l1=l1)
        # _session_id is None by default
        await memory.save_session()
        l1.save.assert_not_called()

    async def test_store_interaction_triggers_l1_save(self, memory):
        l1 = self._l1_mock()
        memory.attach_backends(l1=l1)
        memory._session_id = "sess_1"

        with patch.object(memory, "_generate_embedding", return_value=np.ones(1024)), \
             patch.object(memory, "_extract_semantic_facts", new=AsyncMock()):
            await memory.store_interaction("客户询问价格", importance=0.6)

        l1.save.assert_called_once()

    async def test_store_fact_triggers_l2_upsert(self, memory):
        l2 = self._l2_mock()
        memory.attach_backends(l2=l2)

        with patch.object(memory, "_generate_embedding", return_value=np.ones(1024)):
            await memory.store_fact("customer_budget", "预算 50 万", importance=0.8)

        l2.upsert.assert_called_once()

    async def test_maybe_promote_triggers_l2_upsert(self, memory):
        l2 = self._l2_mock()
        memory.attach_backends(l2=l2)

        entry = _make_entry("ep_high", importance=0.9)
        with patch.object(memory, "_generate_embedding", return_value=np.ones(1024)):
            promoted = await memory.maybe_promote(entry)

        assert promoted is True
        l2.upsert.assert_called_once()
