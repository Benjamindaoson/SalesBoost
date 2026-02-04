"""
Sessions API Endpoints
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from api.deps import audit_access, require_user
from api.auth_schemas import UserSchema as User
from models.runtime_models import Session
from app.tasks.evaluation_task import run_evaluation_task
from app.tasks.store import TASK_STORE, TaskResult, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(require_user), Depends(audit_access)])
# ... (existing SessionCreate and SessionResponse)

@router.get("/tasks/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """
    Get the status of a background task.
    """
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASK_STORE[task_id]

@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """
    Get the result of a completed background task.
    """
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = TASK_STORE[task_id]
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task not yet completed")
        
    return task.result



class SessionCreate(BaseModel):
    """创建会话请求"""
    user_id: str
    course_id: str
    scenario_id: str
    persona_id: str


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: str
    course_id: str
    scenario_id: str
    status: str
    total_turns: int
    final_score: Optional[float]
    final_stage: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """会话列表响应"""
    items: List[SessionResponse]
    total: int
    page: int
    page_size: int


@router.post("", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """Create a new training session."""
    if current_user.role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    session = Session(
        id=session_id,
        user_id=request.user_id,
        course_id=request.course_id,
        scenario_id=request.scenario_id,
        persona_id=request.persona_id,
        status="active",
        started_at=now,
        last_activity_at=now,
    )

    db.add(session)
    await db.flush()

    logger.info(f"Session created: {session_id}")
    return session


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """List sessions."""
    query = select(Session)

    if current_user.role != "admin":
        user_id = current_user.id

    if user_id:
        query = query.where(Session.user_id == user_id)
    if status:
        query = query.where(Session.status == status)

    offset = (page - 1) * page_size
    query = query.order_by(Session.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    sessions = result.scalars().all()

    count_query = select(Session)
    if user_id:
        count_query = count_query.where(Session.user_id == user_id)
    if status:
        count_query = count_query.where(Session.status == status)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return SessionListResponse(
        items=sessions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """获取会话详情"""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return session


@router.get("/{session_id}/review")
async def get_session_review(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """
    Get session review data for frontend dashboard.
    Aggregates Strategy Decisions, Adoptions, and Skill Diffs.
    """
    from models.adoption_models import AdoptionRecord, StrategyDecision
    from models.runtime_models import EvaluationLog
    
    # 1. Verify Session
    session_res = await db.execute(select(Session).where(Session.id == session_id))
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    # 2. Get Strategy Decisions
    strategies_res = await db.execute(
        select(StrategyDecision).where(StrategyDecision.session_id == session_id).order_by(StrategyDecision.turn_id)
    )
    strategies = strategies_res.scalars().all()
    
    # 3. Get Adoptions
    adoptions_res = await db.execute(
        select(AdoptionRecord).where(AdoptionRecord.session_id == session_id)
    )
    adoptions = adoptions_res.scalars().all()
    
    # 4. Get Evaluations
    evals_res = await db.execute(
        select(EvaluationLog).where(EvaluationLog.session_id == session_id).order_by(EvaluationLog.turn_number)
    )
    evals_res.scalars().all()
    
    # 5. Get Matrix Evaluation (PRD)
    matrix_result = session.matrix_eval_result
    
    # Aggregate Data
    
    # Strategy Review
    strategy_review = []
    for s in strategies:
        strategy_review.append({
            "turn": s.turn_id,
            "situation": s.situation_type,
            "user_strategy": s.strategy_chosen,
            "golden_strategy": s.golden_strategy,
            "is_optimal": s.is_optimal,
            "reason": s.optimality_reason
        })
        
    # Effective Adoptions
    effective_adoptions = []
    ineffective_attempts = []
    
    for a in adoptions:
        item = {
            "turn": a.turn_id,
            "technique": a.technique_name,
            "style": a.adoption_style.value,
            "skill_delta": a.skill_delta
        }
        if a.is_effective:
            effective_adoptions.append(item)
        elif a.adopted:
            ineffective_attempts.append(item)
            
    # Skill Delta Summary
    # Calculate total delta across session
    total_delta = {}
    for a in adoptions:
        if a.is_effective and a.skill_delta:
            for k, v in a.skill_delta.items():
                total_delta[k] = round(total_delta.get(k, 0) + v, 2)
                
    return {
        "session_id": session_id,
        "summary": {
            "total_turns": session.total_turns,
            "final_score": session.final_score,
            "skill_improvement": total_delta,
            "matrix_evaluation": matrix_result # Expose to frontend
        },
        "strategy_timeline": strategy_review,
        "highlights": {
            "effective_adoptions": effective_adoptions,
            "ineffective_attempts": ineffective_attempts
        }
    }

@router.post("/{session_id}/evaluate")
async def evaluate_session_endpoint(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """
    Trigger async evaluation for a session.
    Returns a task_id immediately.
    """
    # 1. Verify Session Exists
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session must be completed before evaluation")

    # 2. Create Task ID
    task_id = f"eval_{uuid.uuid4()}"
    
    # 3. Register Task (Queued)
    TASK_STORE[task_id] = TaskResult(
        task_id=task_id,
        status=TaskStatus.QUEUED,
        created_at=datetime.utcnow()
    )
    
    # 4. Dispatch to BackgroundTasks
    background_tasks.add_task(run_evaluation_task, task_id, session_id)
    
    logger.info(f"Dispatched evaluation task {task_id} for session {session_id}")
    
    return {"task_id": task_id, "status": "queued"}

@router.patch("/{session_id}/complete")
async def complete_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    """
    完成会话并触发在线评估 (Legacy endpoint updated to use BackgroundTasks)
    """
    # 1. Fetch Session
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 2. Update Status
    session.status = "completed"
    session.completed_at = datetime.utcnow()
    await db.flush()
    
    # 3. Trigger Evaluation via Background Task
    # Reuse the logic from evaluate_session_endpoint
    task_id = f"eval_{uuid.uuid4()}"
    
    TASK_STORE[task_id] = TaskResult(
        task_id=task_id,
        status=TaskStatus.QUEUED,
        created_at=datetime.utcnow()
    )
    
    background_tasks.add_task(run_evaluation_task, task_id, session_id)
    
    return {
        "message": "Session completed and evaluation triggered", 
        "session_id": session_id,
        "task_id": task_id
    }
