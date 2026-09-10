"""Adaptive Memory — PostgreSQL-backed long-term memory with time decay."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from salesagent.core.settings import settings
from salesagent.memory.decay import effective_score

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


class AdaptiveMemory:
    """
    Long-term memory stored in PostgreSQL.
    Retrieval uses time-decay to surface the most relevant, recent entities.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self,
        session_id: str,
        entity_type: str,
        key: str,
        value: str,
        importance_score: float = 0.5,
    ) -> None:
        """Insert or update a memory entity."""
        from sqlalchemy import select
        from salesagent.models.db_models import MemoryEntity

        result = await self.db.execute(
            select(MemoryEntity).where(
                MemoryEntity.session_id == session_id,
                MemoryEntity.entity_type == entity_type,
                MemoryEntity.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if existing:
            existing.value = value
            existing.importance_score = max(existing.importance_score, importance_score)
            existing.last_accessed_at = now
        else:
            entity = MemoryEntity(
                session_id=session_id,
                entity_type=entity_type,
                key=key,
                value=value,
                importance_score=importance_score,
                last_accessed_at=now,
            )
            self.db.add(entity)

        await self.db.commit()

    async def retrieve(
        self, session_id: str, threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve all memory entities for a session, sorted by effective_score descending.
        Filters out entities below the importance threshold.
        """
        from sqlalchemy import select
        from salesagent.models.db_models import MemoryEntity

        threshold = threshold or settings.memory_importance_threshold
        result = await self.db.execute(
            select(MemoryEntity).where(MemoryEntity.session_id == session_id)
        )
        entities = result.scalars().all()

        now = datetime.now(timezone.utc)
        scored: list[dict[str, Any]] = []
        for e in entities:
            score = effective_score(
                importance_score=e.importance_score,
                last_accessed_at=e.last_accessed_at,
                entity_type=e.entity_type,
                now=now,
            )
            if score >= threshold:
                scored.append({
                    "entity_type": e.entity_type,
                    "key": e.key,
                    "value": e.value,
                    "effective_score": score,
                    "importance_score": e.importance_score,
                })

        scored.sort(key=lambda x: x["effective_score"], reverse=True)
        return scored

    async def build_customer_profile(self, session_id: str) -> dict[str, Any]:
        """Build a structured customer profile from memory entities."""
        entities = await self.retrieve(session_id)
        profile: dict[str, Any] = {}
        for e in entities:
            profile.setdefault(e["entity_type"], {})[e["key"]] = e["value"]
        return profile
