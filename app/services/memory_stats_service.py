import logging
from typing import Any, List

from sqlalchemy import select

from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, MemoryOutcomeEventPayload
from core.database import get_db_session
from core.redis import get_redis
from models.memory_service_models import MemoryEvent, MemoryStrategyUnit

logger = logging.getLogger(__name__)

DEDUP_TTL_SECONDS = 60 * 60 * 24


async def _claim_dedupe_key(key: str, ttl_seconds: int) -> bool:
    client = await get_redis()
    try:
        result = await client.set(key, "1", ex=ttl_seconds, nx=True)
        if result is True or result == "OK":
            return True
        if result in (None, False):
            return False
    except TypeError:
        pass

    try:
        exists = await client.exists(key)
        if exists:
            return False
        await client.set(key, "1", ex=ttl_seconds)
        return True
    except Exception:
        return False


async def _release_dedupe_key(key: str) -> None:
    client = await get_redis()
    try:
        await client.delete(key)
    except Exception:
        return None


@bus.subscribe(EventType.MEMORY_OUTCOME_RECORDED)
async def handle_outcome(payload: Any) -> None:
    if isinstance(payload, dict):
        payload = MemoryOutcomeEventPayload(**payload)

    dedupe_key = f"memory:outcome:{payload.outcome_id}"
    if not await _claim_dedupe_key(dedupe_key, DEDUP_TTL_SECONDS):
        return None

    try:
        strategy_ids: List[str] = list(payload.strategy_ids or [])
        async for db in get_db_session():
            try:
                if not strategy_ids:
                    event_stmt = select(MemoryEvent).where(
                        MemoryEvent.event_id == payload.event_id,
                        MemoryEvent.tenant_id == payload.tenant_id,
                    )
                    event_result = await db.execute(event_stmt)
                    event = event_result.scalar_one_or_none()
                    if event is not None:
                        if event.coach_suggestions_taken:
                            strategy_ids = list(event.coach_suggestions_taken)
                        elif event.coach_suggestions_shown and payload.adopted:
                            strategy_ids = list(event.coach_suggestions_shown)

                if not strategy_ids:
                    break

                progressed = bool(
                    payload.stage_before and payload.stage_after and payload.stage_before != payload.stage_after
                )
                risked = payload.compliance_result == "blocked"

                for strategy_id in strategy_ids:
                    stmt = select(MemoryStrategyUnit).where(
                        MemoryStrategyUnit.tenant_id == payload.tenant_id,
                        MemoryStrategyUnit.strategy_id == strategy_id,
                    )
                    result = await db.execute(stmt)
                    strategy = result.scalar_one_or_none()
                    if strategy is None:
                        continue

                    stats = dict(strategy.stats or {})
                    total = int(stats.get("total_count", 0)) + 1
                    adopted_count = int(stats.get("adopted_count", 0)) + (1 if payload.adopted else 0)
                    progress_count = int(stats.get("progress_count", 0)) + (1 if progressed else 0)
                    risk_count = int(stats.get("risk_count", 0)) + (1 if risked else 0)

                    stats.update(
                        {
                            "total_count": total,
                            "adopted_count": adopted_count,
                            "progress_count": progress_count,
                            "risk_count": risk_count,
                            "adoption_rate": round(adopted_count / total, 4) if total else 0.0,
                            "progress_rate": round(progress_count / total, 4) if total else 0.0,
                            "risk_rate": round(risk_count / total, 4) if total else 0.0,
                        }
                    )
                    strategy.stats = stats

                    evidence_ids = list(strategy.evidence_event_ids or [])
                    if payload.event_id not in evidence_ids:
                        evidence_ids.append(payload.event_id)
                        strategy.evidence_event_ids = evidence_ids

                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error("Failed to update strategy stats: %s", exc)
                raise
            finally:
                break
    except Exception:
        await _release_dedupe_key(dedupe_key)
        return None


def initialize_plugin():
    logger.info("Initializing MemoryStatsService plugin")
    return True
