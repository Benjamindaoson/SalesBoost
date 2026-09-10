"""Sessions API — includes HITL approval and takeover."""
from __future__ import annotations

import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db, get_redis
from salesagent.models.db_models import Session as SessionModel, Message
from salesagent.models.schemas import SessionCreate, SessionResponse
from salesagent.auth.dependencies import get_current_user
from salesagent.auth.permissions import check_resource_ownership

log = structlog.get_logger()
router = APIRouter()

@router.post("/")
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    session = SessionModel(
        customer_id=payload.customer_id,
        agent_id=payload.agent_id,
        metadata_=payload.metadata,
        status="active",
        current_stage="ICEBREAK",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    log.info("Create session", session_id=session.id, user=current_user.get("sub"))
    return {
        "session_id": session.id,
        "id": session.id,
        "status": session.status,
        "current_stage": session.current_stage,
    }

@router.get("/")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    log.info("List sessions", user=current_user.get("sub"))

    # Admin can see all sessions, users only see their own
    user_role = current_user.get("role", "user")
    user_id = current_user.get("user_id") or current_user.get("sub")

    if user_role == "admin":
        result = await db.execute(select(SessionModel).order_by(SessionModel.updated_at.desc()))
    else:
        # Filter by customer_id (assuming sessions have customer_id field)
        result = await db.execute(
            select(SessionModel)
            .where(SessionModel.customer_id == user_id)
            .order_by(SessionModel.updated_at.desc())
        )

    return result.scalars().all()

@router.get("/active")
async def list_active_sessions(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get active sessions list for dashboard."""
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.status == "active")
        .order_by(SessionModel.updated_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": s.id,
            "customer_name": s.customer_id or "未知",
            "intent_score": 0.0,
            "last_message": "",
            "last_message_time": s.updated_at.isoformat() if s.updated_at else None,
            "current_stage": s.current_stage,
            "unread_count": 0,
            "ai_driving": s.ai_driving if hasattr(s, "ai_driving") else True,
        }
        for s in sessions
    ]

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    log.info("Get session", session_id=session_id, user=current_user.get("sub"))
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check ownership (admin can access all)
    check_resource_ownership(session.customer_id, current_user)

    return session

@router.post("/{session_id}/approve")
async def approve_session(
    session_id: str,
    override_text: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """V3.1: Approve a paused session and provide optional manual override."""
    log.info("Approve session", session_id=session_id, user=current_user.get("sub"))
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check ownership (admin can approve all)
    check_resource_ownership(session.customer_id, current_user)

    if not session.is_waiting_approval:
        raise HTTPException(status_code=400, detail="Session is not waiting for approval")

    session.is_waiting_approval = False
    session.pending_human_override = override_text
    await db.commit()

    log.info("Session approved", session_id=session_id, has_override=bool(override_text))
    return {"status": "approved", "session_id": session_id}


@router.post("/{session_id}/takeover")
async def takeover_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """User takes over the session from AI.

    Sets a Redis flag to pause AI responses and updates DB state.

    Args:
        session_id: Session ID
        db: Database session
        redis: Redis client

    Returns:
        Status response
    """
    # Check if session exists
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set Redis flag (atomic operation)
    await redis.set(f"session:{session_id}:ai_paused", "1")

    # Update database state
    await db.execute(
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(
            ai_driving=False,
            takeover_at=datetime.datetime.now(datetime.timezone.utc),
        )
    )
    await db.commit()

    log.info("Session taken over by human", session_id=session_id)

    return {"status": "success", "ai_driving": False, "session_id": session_id}


@router.post("/{session_id}/resume-ai")
async def resume_ai(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Resume AI driving mode.

    Clears the Redis pause flag and updates DB state.

    Args:
        session_id: Session ID
        db: Database session
        redis: Redis client

    Returns:
        Status response
    """
    # Check if session exists
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clear Redis flag
    await redis.delete(f"session:{session_id}:ai_paused")

    # Update database state
    await db.execute(
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(ai_driving=True)
    )
    await db.commit()

    log.info("AI driving resumed", session_id=session_id)

    return {"status": "success", "ai_driving": True, "session_id": session_id}


@router.get("/{session_id}/suggestion")
async def get_ai_suggestion(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get AI suggestion for next response (when human is driving).

    Args:
        session_id: Session ID
        db: Database session
        redis: Redis client

    Returns:
        AI suggestion
    """
    # Check if session exists
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get recent messages
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    messages = result.scalars().all()

    if not messages:
        return {"suggestion": "暂无建议"}

    # Generate suggestion using reasoning chain
    try:
        from salesagent.reasoning.chain import SalesReasoningChain
        from salesagent.llm.gateway import ModelGateway
        from salesagent.fsm.sales_fsm import SaleStage

        gateway = ModelGateway()
        reasoning = SalesReasoningChain(gateway=gateway, redis=redis)

        # Prepare message history
        msg_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

        # Run reasoning
        reasoning_output = await reasoning.run(
            messages=msg_history,
            fsm_stage=SaleStage(session.current_stage) if session.current_stage else SaleStage.ICEBREAK,
            session_id=session_id,
        )

        # Generate suggestion text
        tactics = reasoning_output.recommended_tactics
        suggestion = (
            f"建议使用 {tactics.primary} 策略，"
            f"语气保持 {tactics.tone}。"
        )

        if tactics.avoid:
            suggestion += f" 避免使用：{', '.join(tactics.avoid)}。"

        return {"suggestion": suggestion, "tactics": tactics.model_dump()}

    except Exception as e:
        log.error("Failed to generate AI suggestion", session_id=session_id, error=str(e))
        return {"suggestion": "生成建议失败，请稍后重试"}


# Kept unregistered to avoid routing after "/{session_id}".
async def get_active_sessions(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get active sessions list for dashboard.

    Returns:
        List of active sessions with key metrics
    """
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.status == "active")
        .order_by(SessionModel.updated_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": s.id,
            "customer_name": s.customer_id or "未知",
            "intent_score": 0.0,
            "last_message": "",
            "last_message_time": s.updated_at.isoformat() if s.updated_at else None,
            "current_stage": s.current_stage,
            "unread_count": 0,  # TODO: implement unread count
            "ai_driving": s.ai_driving if hasattr(s, "ai_driving") else True,
        }
        for s in sessions
    ]
