"""MVP micro feedback API."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_user
from api.auth_schemas import UserSchema as User
from core.database import get_db_session
from models.feedback_models import SessionFeedback
from models.runtime_models import Session
from schemas.mvp import MicroFeedbackResponse
from app.agents.ask.feedback_agent import MicroFeedbackService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mvp", tags=["mvp"])

feedback_service = MicroFeedbackService()


@router.get("/sessions/{session_id}/feedback", response_model=MicroFeedbackResponse)
async def get_session_feedback(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    feedback_result = await db.execute(
        select(SessionFeedback).where(SessionFeedback.session_id == session_id)
    )
    existing_feedback = feedback_result.scalar_one_or_none()

    if existing_feedback:
        return MicroFeedbackResponse(
            feedback_items=existing_feedback.feedback_items,
            session_id=session_id,
            total_turns=existing_feedback.total_turns,
        )

    try:
        feedback_response = await feedback_service.generate_feedback(session_id, db)

        feedback_record = SessionFeedback(
            id=str(uuid.uuid4()),
            session_id=session_id,
            feedback_items=[item.model_dump() for item in feedback_response.feedback_items],
            total_turns=feedback_response.total_turns,
            generated_at=datetime.utcnow(),
        )
        db.add(feedback_record)
        await db.commit()

        logger.info("Generated feedback for session %s", session_id)
        return feedback_response
    except Exception as e:
        logger.error("Failed to generate feedback: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate feedback")
