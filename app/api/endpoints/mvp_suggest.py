"""
MVP 实时辅助 API - 一句话话术
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.schemas.mvp import QuickSuggestRequest, QuickSuggestResponse
from app.services.quick_suggest_service import QuickSuggestService
from app.models.runtime_models import Session, SessionState
from app.api.endpoints.websocket import manager
from app.fsm.engine import FSMEngine
from app.schemas.fsm import FSMState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mvp", tags=["mvp"])

suggest_service = QuickSuggestService()


@router.post("/suggest", response_model=QuickSuggestResponse)
async def get_quick_suggest(
    request: QuickSuggestRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取一句话话术建议（MVP核心功能）
    
    输入：{session_id, last_user_msg, optional_context}
    输出：{intent_label, suggested_reply, alt_replies, confidence, evidence}
    """
    # 加载会话
    session_result = await db.execute(
        select(Session).where(Session.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 获取 Orchestrator（如果已存在）
    orchestrator = manager.get_orchestrator(request.session_id)
    
    if not orchestrator:
        raise HTTPException(status_code=400, detail="Session not initialized")
    
    # 加载会话状态
    state_result = await db.execute(
        select(SessionState).where(SessionState.session_id == request.session_id)
    )
    session_state = state_result.scalar_one_or_none()
    
    if not session_state:
        raise HTTPException(status_code=400, detail="Session state not found")
    
    # 生成建议
    try:
        response = await suggest_service.generate_suggest(
            session_id=request.session_id,
            last_user_msg=request.last_user_msg,
            conversation_history=orchestrator.conversation_history,
            fsm_state=orchestrator.fsm_state,
            optional_context=request.optional_context,
        )
        
        logger.info(f"Generated suggest for session {request.session_id}: {response.intent_label}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate suggest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate suggest: {str(e)}")

