"""
MVP 轻量复盘 API
"""
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.schemas.mvp import MicroFeedbackResponse
from app.services.micro_feedback_service import MicroFeedbackService
from app.models.feedback_models import SessionFeedback
from app.models.runtime_models import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mvp", tags=["mvp"])

feedback_service = MicroFeedbackService()


@router.get("/sessions/{session_id}/feedback", response_model=MicroFeedbackResponse)
async def get_session_feedback(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取会话轻量复盘（<=3条反馈）
    
    会话结束时调用，返回可执行反馈
    """
    # 检查是否已生成反馈
    feedback_result = await db.execute(
        select(SessionFeedback).where(SessionFeedback.session_id == session_id)
    )
    existing_feedback = feedback_result.scalar_one_or_none()
    
    if existing_feedback:
        # 返回已存在的反馈
        return MicroFeedbackResponse(
            feedback_items=existing_feedback.feedback_items,
            session_id=session_id,
            total_turns=existing_feedback.total_turns,
        )
    
    # 生成新反馈
    try:
        feedback_response = await feedback_service.generate_feedback(session_id, db)
        
        # 保存到数据库
        feedback_record = SessionFeedback(
            id=str(uuid.uuid4()),
            session_id=session_id,
            feedback_items=[item.model_dump() for item in feedback_response.feedback_items],
            total_turns=feedback_response.total_turns,
            generated_at=datetime.utcnow(),
        )
        db.add(feedback_record)
        await db.commit()
        
        logger.info(f"Generated feedback for session {session_id}: {len(feedback_response.feedback_items)} items")
        return feedback_response
        
    except Exception as e:
        logger.error(f"Failed to generate feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate feedback: {str(e)}")

