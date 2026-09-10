"""Unit tests for Memory system."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from salesagent.memory.decay import effective_score


def test_memory_decay_no_decay():
    """Test memory entities with infinite half-life (name, company)."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=365)  # 1 year ago

    score = effective_score(
        importance_score=0.8,
        last_accessed_at=past,
        entity_type="name",
        now=now,
    )
    # Name should not decay
    assert score == 0.8


def test_memory_decay_short_lived():
    """Test memory entities with short half-life (emotion)."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)  # 2 days ago (emotion half-life is 1 day)

    score = effective_score(
        importance_score=0.8,
        last_accessed_at=past,
        entity_type="emotion",
        now=now,
    )
    # After 2 half-lives, score should be ~0.2 (0.8 * 0.5 * 0.5)
    assert 0.15 < score < 0.25


def test_memory_decay_medium_lived():
    """Test memory entities with medium half-life (budget)."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=7)  # 7 days ago (budget half-life is 7 days)

    score = effective_score(
        importance_score=0.8,
        last_accessed_at=past,
        entity_type="budget",
        now=now,
    )
    # After 1 half-life, score should be ~0.4 (0.8 * 0.5)
    assert 0.35 < score < 0.45


def test_memory_decay_recent():
    """Test that recent memories have minimal decay."""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=1)  # 1 hour ago

    score = effective_score(
        importance_score=0.8,
        last_accessed_at=recent,
        entity_type="budget",
        now=now,
    )
    # Very recent, should be close to original
    assert score > 0.75


def test_memory_importance_threshold():
    """Test that low importance memories decay faster."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=7)

    high_importance = effective_score(
        importance_score=0.9,
        last_accessed_at=past,
        entity_type="budget",
        now=now,
    )

    low_importance = effective_score(
        importance_score=0.3,
        last_accessed_at=past,
        entity_type="budget",
        now=now,
    )

    assert high_importance > low_importance
    assert high_importance > 0.4
    assert low_importance < 0.2
