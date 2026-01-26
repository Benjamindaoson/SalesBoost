import logging
import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_models import AgentEvent, AgentEventType

logger = logging.getLogger(__name__)


class MemoryEventStore:
    """Event Store writer for agent_events."""

    async def record_event(
        self,
        db: Optional[AsyncSession],
        *,
        tenant_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        turn_id: Optional[int],
        agent_name: str,
        event_type: AgentEventType,
        payload: dict,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
    ) -> Optional[str]:
        if db is None:
            return None

        event_id = str(uuid.uuid4())
        event = AgentEvent(
            event_id=event_id,
            ts=datetime.utcnow(),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            turn_id=turn_id,
            agent_name=agent_name,
            event_type=event_type,
            payload_json=payload,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
        )
        db.add(event)
        try:
            await db.commit()
            return event_id
        except Exception as exc:
            await db.rollback()
            logger.error(f"Failed to record agent event: {exc}")
            return None
