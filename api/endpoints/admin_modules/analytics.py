"""
Admin analytics endpoints.
"""
import math
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.admin_deps import get_current_admin
from api.auth_schemas import UserSchema as User
from core.database import get_db_session
from models.runtime_models import Message, Session

router = APIRouter()


class CostTrendPoint(BaseModel):
    date: str
    cost_usd: float
    input_tokens: int
    output_tokens: int


class SkillAverages(BaseModel):
    opening: float = Field(0.0, ge=0.0, le=10.0)
    discovery: float = Field(0.0, ge=0.0, le=10.0)
    closing: float = Field(0.0, ge=0.0, le=10.0)


class AnalyticsOverview(BaseModel):
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    active_users_7d: int
    total_practice_seconds_7d: int
    competency_index: float
    skill_averages: SkillAverages
    cost_trend: List[CostTrendPoint]


@router.get("", response_model=AnalyticsOverview)
async def get_admin_analytics(
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsOverview:
    try:
        now = datetime.utcnow()
        start_date = now - timedelta(days=6)

        token_query = select(
            func.coalesce(
                func.sum(case((Message.role == "user", func.length(Message.content)), else_=0)), 0
            ).label("input_chars"),
            func.coalesce(
                func.sum(case((Message.role == "npc", func.length(Message.content)), else_=0)), 0
            ).label("output_chars"),
        )
        token_row = (await db.execute(token_query)).one()
        input_chars = int(token_row.input_chars or 0)
        output_chars = int(token_row.output_chars or 0)
        input_tokens = int(math.ceil(input_chars / 4)) if input_chars else 0
        output_tokens = int(math.ceil(output_chars / 4)) if output_chars else 0
        total_cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)

        day_expr = func.date(Message.created_at).label("day")
        trend_query = (
            select(
                day_expr,
                func.coalesce(
                    func.sum(case((Message.role == "user", func.length(Message.content)), else_=0)), 0
                ).label("input_chars"),
                func.coalesce(
                    func.sum(case((Message.role == "npc", func.length(Message.content)), else_=0)), 0
                ).label("output_chars"),
            )
            .where(Message.created_at >= start_date)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        trend_rows = (await db.execute(trend_query)).all()
        trend_map: Dict[str, Dict[str, int]] = {}
        for row in trend_rows:
            day_key = row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day)
            trend_map[day_key] = {
                "input_chars": int(row.input_chars or 0),
                "output_chars": int(row.output_chars or 0),
            }

        cost_trend: List[CostTrendPoint] = []
        for offset in range(7):
            day = (start_date + timedelta(days=offset)).date()
            day_key = day.isoformat()
            day_stats = trend_map.get(day_key, {"input_chars": 0, "output_chars": 0})
            day_input_tokens = int(math.ceil(day_stats["input_chars"] / 4)) if day_stats["input_chars"] else 0
            day_output_tokens = int(math.ceil(day_stats["output_chars"] / 4)) if day_stats["output_chars"] else 0
            day_cost = (day_input_tokens * 0.00001) + (day_output_tokens * 0.00003)
            cost_trend.append(
                CostTrendPoint(
                    date=day_key,
                    cost_usd=round(day_cost, 6),
                    input_tokens=day_input_tokens,
                    output_tokens=day_output_tokens,
                )
            )

        stage_query = (
            select(Message.stage, func.avg(Message.turn_score))
            .where(
                Message.turn_score.is_not(None),
                Message.stage.in_(["OPENING", "NEEDS_DISCOVERY", "CLOSING"]),
            )
            .group_by(Message.stage)
        )
        stage_rows = (await db.execute(stage_query)).all()
        stage_scores = {row.stage: float(row[1] or 0.0) for row in stage_rows}
        skill_averages = SkillAverages(
            opening=round(stage_scores.get("OPENING", 0.0), 2),
            discovery=round(stage_scores.get("NEEDS_DISCOVERY", 0.0), 2),
            closing=round(stage_scores.get("CLOSING", 0.0), 2),
        )
        competency_values = [v for v in skill_averages.model_dump().values() if v > 0]
        competency_index = round(sum(competency_values) / len(competency_values), 2) if competency_values else 0.0

        session_query = (
            select(Session.user_id, Session.started_at, Session.last_activity_at, Session.total_duration_seconds)
            .where(Session.last_activity_at >= start_date)
        )
        session_rows = (await db.execute(session_query)).all()
        active_users = {row.user_id for row in session_rows if row.user_id}
        total_seconds = 0
        for row in session_rows:
            duration = int(row.total_duration_seconds or 0)
            if duration <= 0 and row.started_at and row.last_activity_at:
                delta = row.last_activity_at - row.started_at
                duration = max(0, int(delta.total_seconds()))
            total_seconds += duration

        return AnalyticsOverview(
            total_cost_usd=round(total_cost, 6),
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            active_users_7d=len(active_users),
            total_practice_seconds_7d=total_seconds,
            competency_index=competency_index,
            skill_averages=skill_averages,
            cost_trend=cost_trend,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analytics computation failed: {exc}") from exc
