"""Shared writer for memory events (DB + vector)."""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from models.memory_service_models import MemoryEvent
from app.infra.events.schemas import MemoryEventPayload

try:
    from functools import lru_cache
except ImportError:  # pragma: no cover
    lru_cache = None  # type: ignore

try:
    from app.memory.storage.vector_store import VectorStore
except Exception:  # pragma: no cover
    VectorStore = None  # type: ignore

logger = logging.getLogger(__name__)


if lru_cache:
    @lru_cache(maxsize=8)
    def _get_vector_store(collection_name: str):
        if VectorStore is None:
            return None
        try:
            return VectorStore(collection_name=collection_name)
        except Exception as exc:  # pragma: no cover
            logger.warning("VectorStore init failed: %s", exc)
            return None
else:  # pragma: no cover
    def _get_vector_store(collection_name: str):
        if VectorStore is None:
            return None
        try:
            return VectorStore(collection_name=collection_name)
        except Exception as exc:
            logger.warning("VectorStore init failed: %s", exc)
            return None


def _compact_json(data: object) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(data)


async def record_event(payload: MemoryEventPayload, db: Optional[AsyncSession] = None) -> None:
    """Persist memory event to Postgres and vector store."""
    async for session in get_db_session():
        try:
            event = MemoryEvent(
                event_id=payload.event_id,
                tenant_id=payload.tenant_id,
                user_id=payload.user_id,
                session_id=payload.session_id,
                channel=payload.channel,
                turn_index=payload.turn_index,
                speaker=payload.speaker,
                raw_text_ref=payload.raw_text_ref,
                summary=payload.summary,
                intent_top1=payload.intent_top1,
                intent_topk=payload.intent_topk,
                stage=payload.stage,
                objection_type=payload.objection_type,
                entities=payload.entities,
                sentiment=payload.sentiment,
                tension=payload.tension,
                compliance_flags=payload.compliance_flags,
                coach_suggestions_shown=payload.coach_suggestions_shown,
                coach_suggestions_taken=payload.coach_suggestions_taken,
                metadata_json=payload.metadata,
            )
            session.add(event)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            break

    if payload.summary:
        vector_store = _get_vector_store("memory_event_summary")
        if vector_store is not None:
            vector_store.add_documents(
                [payload.summary],
                [
                    {
                        "tenant_id": payload.tenant_id,
                        "user_id": payload.user_id,
                        "session_id": payload.session_id,
                        "event_id": payload.event_id,
                        "speaker": payload.speaker,
                        "intent_top1": payload.intent_top1,
                        "stage": payload.stage,
                        "objection_type": payload.objection_type,
                    }
                ],
                [payload.event_id],
            )
