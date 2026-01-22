import logging
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_models import (
    MemoryItem,
    MemoryStatus,
    MemoryType,
    ReflectiveRule,
    RuleStatus,
    Episode,
)
from app.schemas.memory import MemoryCandidate, TurnState
from app.services.memory_event_store import MemoryEventStore
from app.models.memory_models import AgentEventType

logger = logging.getLogger(__name__)


class MemoryWriteService:
    """Slow Path memory write pipeline."""

    def __init__(self):
        self.event_store = MemoryEventStore()

    async def ensure_episode(
        self,
        db: Optional[AsyncSession],
        *,
        turn_state: TurnState,
        outcome: Optional[str] = None,
        score_overall: Optional[float] = None,
        summary: Optional[str] = None,
        replay_pointer: Optional[str] = None,
    ) -> Optional[str]:
        if db is None:
            return None
        stmt = select(Episode).where(Episode.session_id == turn_state.session_id)
        result = await db.execute(stmt)
        episode = result.scalar_one_or_none()
        if not episode:
            episode = Episode(
                episode_id=str(uuid.uuid4()),
                tenant_id=turn_state.tenant_id,
                user_id=turn_state.user_id,
                session_id=turn_state.session_id,
                scenario_id=turn_state.scenario_id,
                persona_id=turn_state.persona_id,
                start_ts=datetime.utcnow(),
                outcome=outcome,
                score_overall=score_overall,
                episode_summary=summary,
                replay_pointer=replay_pointer,
            )
            db.add(episode)
        else:
            episode.end_ts = datetime.utcnow()
            if outcome:
                episode.outcome = outcome
            if score_overall is not None:
                episode.score_overall = score_overall
            if summary:
                episode.episode_summary = summary
            if replay_pointer:
                episode.replay_pointer = replay_pointer
        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Failed to ensure episode: {exc}")
            return None
        return episode.episode_id

    async def enqueue_candidates(
        self,
        db: Optional[AsyncSession],
        *,
        turn_state: TurnState,
        candidates: List[MemoryCandidate],
        trace_id: Optional[str] = None,
    ) -> List[str]:
        if db is None or not candidates:
            return []

        memory_ids: List[str] = []
        for candidate in candidates:
            candidate_type = candidate.memory_type.value
            if candidate_type == MemoryType.SEMANTIC.value:
                memory_id = str(uuid.uuid4())
                memory_ids.append(memory_id)
                item = MemoryItem(
                    memory_id=memory_id,
                    memory_type=MemoryType.SEMANTIC,
                    tenant_id=turn_state.tenant_id,
                    scope=candidate.scope,
                    scope_id=candidate.scope_id,
                    source_episode_id=candidate.source_episode_id,
                    title=candidate.title,
                    content=candidate.content,
                    tags=list(candidate.tags or []),
                    confidence=candidate.confidence,
                    status=MemoryStatus.SHADOW,
                    version=1,
                    created_by=candidate.created_by,
                )
                db.add(item)
            elif candidate_type == MemoryType.REFLECTIVE.value:
                rule_id = str(uuid.uuid4())
                memory_id = str(uuid.uuid4())
                memory_ids.append(memory_id)
                rule = ReflectiveRule(
                    rule_id=rule_id,
                    tenant_id=turn_state.tenant_id,
                    scope=candidate.scope,
                    scope_id=candidate.scope_id,
                    trigger=candidate.reflective_trigger or {},
                    action=candidate.reflective_action or {},
                    priority=0,
                    status=RuleStatus.SHADOW,
                    version=1,
                    source_episode_id=candidate.source_episode_id,
                    explain=candidate.explain,
                )
                db.add(rule)
                item = MemoryItem(
                    memory_id=memory_id,
                    memory_type=MemoryType.REFLECTIVE,
                    tenant_id=turn_state.tenant_id,
                    scope=candidate.scope,
                    scope_id=candidate.scope_id,
                    source_episode_id=candidate.source_episode_id,
                    title=candidate.title,
                    content=candidate.content,
                    tags=list(candidate.tags or []),
                    confidence=candidate.confidence,
                    status=MemoryStatus.SHADOW,
                    version=1,
                    created_by=candidate.created_by,
                )
                db.add(item)

        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Failed to enqueue memory candidates: {exc}")
            return []

        await self.event_store.record_event(
            db,
            tenant_id=turn_state.tenant_id,
            user_id=turn_state.user_id,
            session_id=turn_state.session_id,
            turn_id=turn_state.turn_id,
            agent_name="MemoryWriteService",
            event_type=AgentEventType.WRITE_MEMORY,
            payload={"memory_ids": memory_ids, "count": len(memory_ids)},
            trace_id=trace_id,
        )
        return memory_ids
