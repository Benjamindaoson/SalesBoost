"""Tests for AgentMemory.maybe_promote() — L1→L2 promotion."""
import time
import pytest
import numpy as np
from app.agents.memory.agent_memory import AgentMemory, MemoryEntry, MemoryType


def _make_entry(importance: float, memory_id: str = "test-id") -> MemoryEntry:
    return MemoryEntry(
        memory_id=memory_id,
        memory_type=MemoryType.EPISODIC,
        content="Customer asked about pricing",
        metadata={"session": "s1"},
        importance=importance,
        access_count=0,
        last_access=time.time(),
        created_at=time.time(),
    )


@pytest.fixture
def mem():
    return AgentMemory(agent_id="test-agent")


async def test_maybe_promote_below_threshold_returns_false(mem):
    entry = _make_entry(importance=0.5)
    promoted = await mem.maybe_promote(entry)
    assert promoted is False
    assert entry.memory_id not in mem.semantic_memory


async def test_maybe_promote_at_threshold_returns_true(mem):
    entry = _make_entry(importance=0.75)
    promoted = await mem.maybe_promote(entry)
    assert promoted is True
    assert entry.memory_id in mem.semantic_memory


async def test_maybe_promote_above_threshold_returns_true(mem):
    entry = _make_entry(importance=0.9)
    promoted = await mem.maybe_promote(entry)
    assert promoted is True
    assert entry.memory_id in mem.semantic_memory


async def test_maybe_promote_entry_has_semantic_type(mem):
    entry = _make_entry(importance=0.8)
    await mem.maybe_promote(entry)
    promoted = mem.semantic_memory[entry.memory_id]
    assert promoted.memory_type == MemoryType.SEMANTIC


async def test_maybe_promote_metadata_marks_source(mem):
    entry = _make_entry(importance=0.8)
    await mem.maybe_promote(entry)
    promoted = mem.semantic_memory[entry.memory_id]
    assert promoted.metadata.get("promoted_from") == "episodic"


async def test_maybe_promote_idempotent(mem):
    entry = _make_entry(importance=0.8)
    first = await mem.maybe_promote(entry)
    second = await mem.maybe_promote(entry)
    assert first is True
    assert second is False  # Already in L2, not a new promotion
    assert len([k for k in mem.semantic_memory if k == entry.memory_id]) == 1


async def test_maybe_promote_below_threshold_no_side_effects(mem):
    entry = _make_entry(importance=0.74)
    await mem.maybe_promote(entry)
    assert mem.semantic_memory == {}
