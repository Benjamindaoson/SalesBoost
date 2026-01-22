"""
Reports API Endpoints
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from pydantic import BaseModel, Field

from app.core.database import get_db_session
from app.models.runtime_models import Session, Message
from app.services.report_service import ReportService
from app.services.curriculum_planner import CurriculumPlanner
from app.services.adoption_tracker import AdoptionTracker
from app.services.strategy_analyzer import StrategyAnalyzer
from app.schemas.reports import TrainingReport
from app.api import deps
from app.models.saas_models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

report_service = ReportService()
curriculum_planner = CurriculumPlanner()


class SimulationResult(BaseModel):
    episode_id: str
    status: str = Field(..., description="DEAL_WON/FAILED/TIMEOUT")
    total_steps: int
    objection_tags: List[str] = Field(default_factory=list)
    started_at: datetime


class SimulationSummaryResponse(BaseModel):
    success_rate: float
    avg_turns: float
    common_objections: List[Dict[str, Any]]
    time_series: List[Dict[str, Any]]

class TaskStatsResponse(BaseModel):
    total: int
    completed: int
    inProgress: int
    notStarted: int
    averageScore: float

class TaskProgress(BaseModel):
    completed: int
    total: int
    score: Optional[float] = None

class DateRange(BaseModel):
    start: str
    end: str

class TaskItemResponse(BaseModel):
    id: str
    courseName: str
    courseTags: List[str]
    taskInfo: str
    taskLink: Optional[str] = None
    status: str
    dateRange: DateRange
    progress: TaskProgress


def get_simulation_stats() -> List[SimulationResult]:
    now = datetime.utcnow()
    return [
        SimulationResult(
            episode_id="sim_001",
            status="DEAL_WON",
            total_steps=12,
            objection_tags=["price", "security"],
            started_at=now,
        ),
        SimulationResult(
            episode_id="sim_002",
            status="FAILED",
            total_steps=8,
            objection_tags=["timing"],
            started_at=now,
        ),
        SimulationResult(
            episode_id="sim_003",
            status="DEAL_WON",
            total_steps=15,
            objection_tags=["price", "integration"],
            started_at=now,
        ),
    ]


@router.get("/stats/tasks", response_model=TaskStatsResponse)
async def get_task_stats(
    db: AsyncSession = Depends(get_db_session),
    # In future, filter by current user
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get aggregated task statistics.
    
    For MVP: Calculates stats based on Session records.
    - Total: Total distinct sessions
    - Completed: Sessions with status='completed' or 'deal_won'
    - In Progress: Sessions with status='active'
    - Not Started: Placeholder (or count of assigned scenarios - completed)
    - Average Score: Avg of final_score
    """
    
    # Calculate stats from sessions
    query = select(
        func.count(Session.id).label("total"),
        func.sum(case((Session.status.in_(['completed', 'deal_won']), 1), else_=0)).label("completed"),
        func.sum(case((Session.status == 'active', 1), else_=0)).label("in_progress"),
        func.avg(Session.final_score).label("avg_score")
    )
    
    result = await db.execute(query)
    stats = result.one()
    
    total = stats.total or 0
    completed = stats.completed or 0
    in_progress = stats.in_progress or 0
    avg_score = round(stats.avg_score or 0, 1)
    
    # For MVP, we might not have explicit "assigned tasks" table yet,
    # so "not_started" is hard to calculate dynamically without a task assignment model.
    # We'll use a placeholder or derived value.
    # Let's assume a fixed curriculum size of 10 for demo purposes, or just 0 if not tracking assignments.
    not_started = max(0, 10 - total) 

    return TaskStatsResponse(
        total=total + not_started, # Total assigned + ad-hoc
        completed=completed,
        inProgress=in_progress,
        notStarted=not_started,
        averageScore=avg_score
    )


@router.get("/tasks", response_model=List[TaskItemResponse])
async def get_tasks(
    status: str = Query("all", description="Filter by status: all, not_started, in_progress, completed"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get list of tasks (sessions/scenarios).
    """
    
    # Query sessions
    stmt = select(Session).order_by(Session.updated_at.desc())
    
    if status != "all":
        if status == "completed":
            stmt = stmt.where(Session.status.in_(['completed', 'deal_won']))
        elif status == "in_progress":
            stmt = stmt.where(Session.status == 'active')
        elif status == "not_started":
            # Sessions are by definition started, so this would return empty
            # unless we query a Scenarios table.
            # For MVP, we return empty list for not_started filters on sessions
            return []

    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    tasks = []
    for session in sessions:
        # Map session to TaskItemResponse
        # Use session data to populate fields
        
        # Infer date range (start to update)
        start_date = session.started_at.strftime("%Y-%m-%d")
        end_date = session.updated_at.strftime("%Y-%m-%d")
        
        # Infer tags/info from session metadata or defaults
        tags = ["销售技巧"]
        if session.session_type:
            tags.append(session.session_type)
            
        task_info = f"客户: {session.customer_id}" # Placeholder
        
        # Calculate progress (turns / estimated max turns?)
        # For MVP, use turn_count
        completed_turns = session.turn_count
        total_turns = 10 # Estimate
        
        # Map status
        task_status = "in_progress"
        if session.status in ['completed', 'deal_won', 'failed']:
            task_status = "completed"
            
        tasks.append(TaskItemResponse(
            id=session.id,
            courseName="实战演练", # Generic name
            courseTags=tags,
            taskInfo=task_info,
            taskLink=None,
            status=task_status,
            dateRange=DateRange(start=start_date, end=end_date),
            progress=TaskProgress(
                completed=completed_turns, 
                total=total_turns,
                score=session.final_score
            )
        ))
        
    return tasks


@router.get("/{session_id}", response_model=TrainingReport)
async def get_session_report(
    session_id: str,
    include_details: bool = Query(False, description="是否包含轮次详情"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取训练报告"""
    # 查询会话
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 查询消息
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.turn_number)
    )
    messages = result.scalars().all()
    
    # 生成报告
    report = await report_service.generate_report(
        session=session,
        messages=list(messages),
        include_turn_details=include_details,
    )
    
    return report


@router.get("/user/{user_id}/summary")
async def get_user_summary(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户训练摘要"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    if not sessions:
        return {
            "user_id": user_id,
            "total_sessions": 0,
            "recent_sessions": [],
            "avg_score": None,
        }
    
    scores = [s.final_score for s in sessions if s.final_score]
    avg_score = sum(scores) / len(scores) if scores else None
    
    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "recent_sessions": [
            {
                "id": s.id,
                "status": s.status,
                "final_score": s.final_score,
                "final_stage": s.final_stage,
                "started_at": s.started_at,
            }
            for s in sessions[:5]
        ],
        "avg_score": round(avg_score, 2) if avg_score else None,
    }


@router.get("/simulation/summary", response_model=SimulationSummaryResponse)
async def get_simulation_summary(
    current_user: User = Depends(deps.get_current_active_user),
):
    """Get aggregated simulation stats for dashboard charts."""
    stats = get_simulation_stats()
    total = len(stats)
    wins = sum(1 for s in stats if s.status == "DEAL_WON")
    success_rate = round((wins / total) * 100, 2) if total else 0.0
    avg_turns = round(sum(s.total_steps for s in stats) / total, 2) if total else 0.0

    objection_counts: Dict[str, int] = {}
    for s in stats:
        for tag in s.objection_tags:
            objection_counts[tag] = objection_counts.get(tag, 0) + 1

    common_objections = [
        {"tag": tag, "count": count}
        for tag, count in sorted(objection_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    time_series = [
        {
            "timestamp": s.started_at.isoformat(),
            "episode_id": s.episode_id,
            "status": s.status,
            "turns": s.total_steps,
            "success": s.status == "DEAL_WON",
        }
        for s in stats
    ]

    return SimulationSummaryResponse(
        success_rate=success_rate,
        avg_turns=avg_turns,
        common_objections=common_objections,
        time_series=time_series,
    )



# ============================================================
# 销冠能力复制系统 API - 回答 5 个核心问题
# ============================================================

@router.get("/user/{user_id}/curriculum")
async def get_curriculum_plan(
    user_id: str,
    max_focus_items: int = Query(3, ge=1, le=5, description="最大训练焦点数"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取个性化训练计划
    
    回答核心问题：
    - 我下一步应该练什么场景？
    - 为什么推荐这个场景？
    - 如果我继续练 N 次，大概能补多少差距？
    """
    plan = await curriculum_planner.generate_curriculum(
        db=db,
        user_id=user_id,
        max_focus_items=max_focus_items,
    )
    
    return {
        "user_id": user_id,
        "next_training_plan": [focus.model_dump() for focus in plan.next_training_plan],
        "reasoning": plan.reasoning,
        "expected_improvement": plan.expected_improvement,
    }


@router.get("/user/{user_id}/strategy-profile")
async def get_strategy_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户策略画像
    
    回答核心问题：
    - 我在哪些情境下最常偏离销冠策略？
    - 我的整体最优策略选择率是多少？
    """
    profile = await StrategyAnalyzer.get_user_strategy_profile(db=db, user_id=user_id)
    return profile


@router.get("/user/{user_id}/strategy-deviations")
async def get_strategy_deviations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取策略偏离统计
    
    回答核心问题：
    - 我在哪些情境下最常偏离销冠策略？
    - 我最常用的非最优策略是什么？
    """
    deviations = await StrategyAnalyzer.get_strategy_deviation_stats(
        db=db,
        user_id=user_id,
        limit=limit,
    )
    return {
        "user_id": user_id,
        "deviations": deviations,
    }


@router.get("/user/{user_id}/effective-suggestions")
async def get_effective_suggestions(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取最有效的建议类型统计
    
    回答核心问题：
    - 哪 3 类 Coach 建议，最容易让我变强？
    """
    stats = await AdoptionTracker.get_effective_suggestions_stats(
        db=db,
        user_id=user_id,
        limit=limit,
    )
    return {
        "user_id": user_id,
        "effective_suggestions": stats,
    }


@router.get("/user/{user_id}/skill-improvements")
async def get_skill_improvements(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取最近的能力提升来源
    
    回答核心问题：
    - 我最近 10 次能力提升来自哪些采纳？
    """
    improvements = await curriculum_planner.get_recent_skill_improvements(
        db=db,
        user_id=user_id,
        limit=limit,
    )
    return {
        "user_id": user_id,
        "recent_improvements": improvements,
    }


@router.get("/user/{user_id}/future-estimate")
async def get_future_estimate(
    user_id: str,
    training_count: int = Query(3, ge=1, le=10, description="预估训练次数"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    预估未来训练提升
    
    回答核心问题：
    - 如果我继续练 N 次，大概能补多少差距？
    """
    estimate = await curriculum_planner.estimate_future_improvement(
        db=db,
        user_id=user_id,
        training_count=training_count,
    )
    return {
        "user_id": user_id,
        "training_count": training_count,
        "estimated_improvement": estimate,
    }


@router.post("/user/{user_id}/update-profile")
async def update_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新用户策略画像
    
    触发 UserStrategyProfile 的重新计算和持久化
    """
    profile = await curriculum_planner.update_user_profile(db=db, user_id=user_id)
    await db.commit()
    
    return {
        "user_id": user_id,
        "message": "Profile updated successfully",
        "profile_id": profile.id,
        "adoption_rate": profile.adoption_rate,
        "effective_adoption_rate": profile.effective_adoption_rate,
        "top_weakness_situations": profile.top_weakness_situations,
    }
