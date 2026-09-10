"""Evaluation API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db
from salesagent.models.db_models import EvaluationRecord
from salesagent.models.schemas import EvaluationRecordResponse, SessionEvaluationSummary
from salesagent.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/{session_id}/summary", response_model=SessionEvaluationSummary)
async def get_session_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SessionEvaluationSummary:
    from salesagent.evaluation.session_level import SessionEvaluator
    evaluator = SessionEvaluator(db=db)
    return await evaluator.evaluate(session_id)


@router.get("/records")
async def list_evaluation_records(
    session_id: str | None = None,
    level: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    q = select(EvaluationRecord).order_by(EvaluationRecord.created_at.desc()).limit(limit)
    if session_id:
        q = q.where(EvaluationRecord.session_id == session_id)
    if level:
        q = q.where(EvaluationRecord.level == level)
    result = await db.execute(q)
    records = result.scalars().all()
    return [{"id": r.id, "session_id": r.session_id, "level": r.level, "scores": r.scores} for r in records]
