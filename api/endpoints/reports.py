"""Reports API Endpoints."""
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import audit_access, require_user
from api.auth_schemas import UserSchema as User
from core.database import get_db_session
from models.runtime_models import Message, Session
from schemas.reports import TrainingReport
from app.agents.evaluate.adoption_tracker import AdoptionTracker
from app.agents.evaluate.curriculum_planner import CurriculumPlanner
from app.agents.evaluate.report_generator import ReportService
from app.agents.evaluate.strategy_analyzer import StrategyAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(audit_access)])

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


def _ensure_session_access(session: Session, current_user: User) -> None:
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


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


@router.get("/{session_id}", response_model=TrainingReport)
async def get_session_report(
    session_id: str,
    include_details: bool = Query(False, description="include turn details"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _ensure_session_access(session, current_user)

    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.turn_number)
    )
    messages = result.scalars().all()

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
    current_user: User = Depends(require_user),
):
    if current_user.role != "admin" and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

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
            "count": 0,
            "items": [],
        }

    items = []
    for s in sessions:
        items.append(
            {
                "session_id": s.id,
                "status": s.status,
                "total_turns": s.total_turns,
                "final_score": s.final_score,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
        )

    return {"user_id": user_id, "count": len(items), "items": items}
