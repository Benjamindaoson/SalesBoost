"""Data retention utilities."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from core.config import get_settings
from core.database import async_session_factory
from models.runtime_models import Message, Session, SessionState, EvaluationLog
from models.saas_models import AuditLog


async def run_retention_cleanup() -> int:
    settings = get_settings()
    if not settings.RETENTION_ENABLED:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.DATA_RETENTION_DAYS)
    deleted = 0

    async with async_session_factory() as session:
        for stmt in [
            delete(Message).where(Message.created_at < cutoff),
            delete(SessionState).where(SessionState.created_at < cutoff),
            delete(EvaluationLog).where(EvaluationLog.created_at < cutoff),
            delete(Session).where(Session.created_at < cutoff),
            delete(AuditLog).where(AuditLog.created_at < cutoff),
        ]:
            result = await session.execute(stmt)
            deleted += result.rowcount or 0
        await session.commit()

    return deleted
