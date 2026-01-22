import logging
from typing import Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_models import AgentEvent, AgentEventType, MemoryItem, MemoryStatus

logger = logging.getLogger(__name__)


class MemoryMetricsService:
    """Memory metrics aggregation."""

    async def get_metrics(self, db: Optional[AsyncSession]) -> Dict[str, float]:
        if db is None:
            return {
                "memory_hit_rate": 0.0,
                "memory_contribution_rate": 0.0,
                "memory_pollution_rate": 0.0,
                "replay_consistency": 0.0,
                "shadow_to_active_rate": 0.0,
            }

        hit_rate = await self._average_metric(db, "memory_hit_rate")
        contribution = await self._average_metric(db, "memory_contribution_rate")

        total_items_stmt = select(func.count()).select_from(MemoryItem)
        total_items = (await db.execute(total_items_stmt)).scalar_one()
        polluted_stmt = select(func.count()).select_from(MemoryItem).where(
            MemoryItem.status.in_([MemoryStatus.DEPRECATED, MemoryStatus.DELETED])
        )
        polluted = (await db.execute(polluted_stmt)).scalar_one()
        pollution_rate = (polluted / total_items) if total_items else 0.0

        replay_consistency = await self._average_metric(db, "replay_consistency")
        shadow_to_active = await self._average_metric(db, "shadow_to_active_rate")

        return {
            "memory_hit_rate": hit_rate,
            "memory_contribution_rate": contribution,
            "memory_pollution_rate": pollution_rate,
            "replay_consistency": replay_consistency,
            "shadow_to_active_rate": shadow_to_active,
        }

    async def _average_metric(self, db: AsyncSession, metric_key: str) -> float:
        stmt = (
            select(func.avg(AgentEvent.payload_json[metric_key].as_float()))
            .where(AgentEvent.event_type == AgentEventType.METRIC)
        )
        result = await db.execute(stmt)
        value = result.scalar()
        return float(value) if value is not None else 0.0
