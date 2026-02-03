"""MVP quick suggest API."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_user
from api.auth_schemas import UserSchema as User
from core.database import get_db_session
from models.runtime_models import Message, Session, SessionState
from schemas.mvp import QuickSuggestRequest, QuickSuggestResponse
from app.agents.ask.quick_suggest import QuickSuggestService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mvp", tags=["mvp"])

suggest_service = QuickSuggestService()


@router.post("/suggest", response_model=QuickSuggestResponse)
async def get_quick_suggest(
    request: QuickSuggestRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    session_result = await db.execute(select(Session).where(Session.id == request.session_id))
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    state_result = await db.execute(select(SessionState).where(SessionState.session_id == request.session_id))
    session_state = state_result.scalar_one_or_none()
    if not session_state:
        raise HTTPException(status_code=400, detail="Session state not found")

    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == request.session_id, Message.status == "committed")
        .order_by(Message.turn_number.desc())
        .limit(10)
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    conversation_history = [{"role": m.role, "content": m.content} for m in history_msgs]

    try:
        response = await suggest_service.generate_suggest(
            session_id=request.session_id,
            last_user_msg=request.last_user_msg,
            conversation_history=conversation_history,
            fsm_state={
                "current_stage": session_state.current_stage,
                "turn_count": session_state.turn_count,
                "npc_mood": session_state.npc_mood,
            },
            optional_context=request.optional_context,
        )
        logger.info("Generated suggest for session %s", request.session_id)
        return response
    except Exception as e:
        logger.error("Failed to generate suggest: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate suggest")
