"""
Cockpit API

Executive dashboard endpoints providing real-time funnel, methodology stats,
team performance, and event feed.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...models.deal import Deal, DealStage, Encounter, CockpitEvent
from ...models.evaluation import Evaluation
from ...services.methodology_engine import MethodologyEngine, MethodologyState

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cockpit"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FunnelItem(BaseModel):
    stage: str
    label: str
    count: int
    total_amount: float


class TodayStats(BaseModel):
    encounters_today: int
    new_deals_today: int
    stage_advances_today: int
    deals_won_today: int
    deals_lost_today: int


class WinPrediction(BaseModel):
    predicted_amount: float
    confidence: float
    target_amount: float
    target_pct: float


class MethodologyDimStat(BaseModel):
    dimension: str
    label: str
    avg_pct: float


class MethodologyOverview(BaseModel):
    avg_score: float
    total_deals: int
    dimension_stats: List[MethodologyDimStat]
    weakest: Optional[str] = None
    insight: Optional[str] = None


class TeamMemberStat(BaseModel):
    user_id: int
    deals_count: int
    avg_methodology_score: float
    encounters_count: int
    won_count: int


class EventItem(BaseModel):
    id: int
    event_type: str
    payload: Optional[dict] = None
    created_at: str


class CockpitOverview(BaseModel):
    funnel: List[FunnelItem]
    today: TodayStats
    prediction: WinPrediction
    methodology: MethodologyOverview
    recent_events: List[EventItem]


# ---------------------------------------------------------------------------
# Stage display labels
# ---------------------------------------------------------------------------

STAGE_LABELS = {
    "lead": "线索",
    "qualified": "机会",
    "proposal": "方案",
    "negotiation": "谈判",
    "closed_won": "成交",
    "closed_lost": "流失",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/cockpit/overview", response_model=CockpitOverview)
async def cockpit_overview(
    db: AsyncSession = Depends(get_db_session),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- Funnel ---
    funnel_stmt = (
        select(
            Deal.stage,
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.amount), 0),
        )
        .group_by(Deal.stage)
    )
    funnel_result = await db.execute(funnel_stmt)
    funnel_rows = funnel_result.all()

    stage_order = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]
    funnel_map = {}
    for row in funnel_rows:
        sv = row[0].value if hasattr(row[0], "value") else str(row[0])
        funnel_map[sv] = (row[1], float(row[2]))

    funnel = [
        FunnelItem(
            stage=s,
            label=STAGE_LABELS.get(s, s),
            count=funnel_map.get(s, (0, 0))[0],
            total_amount=funnel_map.get(s, (0, 0))[1],
        )
        for s in stage_order
    ]

    # --- Today stats ---
    enc_count_stmt = select(func.count(Encounter.id)).where(Encounter.created_at >= today_start)
    enc_count = (await db.execute(enc_count_stmt)).scalar() or 0

    new_deals_stmt = select(func.count(Deal.id)).where(Deal.created_at >= today_start)
    new_deals = (await db.execute(new_deals_stmt)).scalar() or 0

    stage_adv_stmt = select(func.count(CockpitEvent.id)).where(
        and_(CockpitEvent.event_type == "stage_changed", CockpitEvent.created_at >= today_start)
    )
    stage_advances = (await db.execute(stage_adv_stmt)).scalar() or 0

    won_stmt = select(func.count(Deal.id)).where(
        and_(Deal.stage == DealStage.CLOSED_WON, Deal.updated_at >= today_start)
    )
    won = (await db.execute(won_stmt)).scalar() or 0

    lost_stmt = select(func.count(Deal.id)).where(
        and_(Deal.stage == DealStage.CLOSED_LOST, Deal.updated_at >= today_start)
    )
    lost = (await db.execute(lost_stmt)).scalar() or 0

    today = TodayStats(
        encounters_today=enc_count,
        new_deals_today=new_deals,
        stage_advances_today=stage_advances,
        deals_won_today=won,
        deals_lost_today=lost,
    )

    # --- Win prediction ---
    active_deals_stmt = select(Deal).where(
        Deal.stage.notin_([DealStage.CLOSED_WON, DealStage.CLOSED_LOST])
    )
    active_deals_result = await db.execute(active_deals_stmt)
    active_deals = active_deals_result.scalars().all()

    predicted_amount = 0.0
    for d in active_deals:
        score = d.methodology_score or 0
        prob = min(score / 100.0, 0.95)
        predicted_amount += (d.amount or 0) * prob

    target_amount = max(predicted_amount * 1.3, 100000)
    confidence = 0.73 if active_deals else 0.0

    prediction = WinPrediction(
        predicted_amount=round(predicted_amount, 2),
        confidence=confidence,
        target_amount=round(target_amount, 2),
        target_pct=round((predicted_amount / target_amount) * 100, 1) if target_amount else 0,
    )

    # --- Methodology overview ---
    from ...services.methodology_engine import FRAMEWORK_DEFINITIONS

    all_states = []
    for d in active_deals:
        if d.methodology_state:
            try:
                all_states.append(json.loads(d.methodology_state))
            except Exception:
                pass

    agg = MethodologyEngine.aggregate_team_stats(all_states)

    meddpicc_dims = FRAMEWORK_DEFINITIONS.get("meddpicc", {}).get("dimensions", {})
    dim_stats = []
    for dim_key, avg_val in agg.get("dimension_averages", {}).items():
        label = meddpicc_dims.get(dim_key, {}).get("label", dim_key)
        dim_stats.append(MethodologyDimStat(dimension=dim_key, label=label, avg_pct=avg_val))
    dim_stats.sort(key=lambda x: x.avg_pct)

    weakest = agg.get("weakest")
    weakest_label = meddpicc_dims.get(weakest, {}).get("label", weakest) if weakest else None
    weakest_pct = agg.get("dimension_averages", {}).get(weakest, 0) if weakest else 0
    insight = None
    if weakest_label:
        insight = f"{int(100 - weakest_pct)}% 的商机未确认 {weakest_label} — 建议重点关注"

    methodology = MethodologyOverview(
        avg_score=agg.get("avg_score", 0),
        total_deals=agg.get("total_deals", 0),
        dimension_stats=dim_stats,
        weakest=weakest,
        insight=insight,
    )

    # --- Recent events ---
    events_stmt = (
        select(CockpitEvent)
        .order_by(desc(CockpitEvent.created_at))
        .limit(20)
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    recent_events = []
    for ev in events:
        payload = None
        try:
            if ev.payload:
                payload = json.loads(ev.payload)
        except Exception:
            pass
        recent_events.append(EventItem(
            id=ev.id,
            event_type=ev.event_type,
            payload=payload,
            created_at=str(ev.created_at) if ev.created_at else "",
        ))

    return CockpitOverview(
        funnel=funnel,
        today=today,
        prediction=prediction,
        methodology=methodology,
        recent_events=recent_events,
    )


@router.get("/cockpit/funnel", response_model=List[FunnelItem])
async def cockpit_funnel(db: AsyncSession = Depends(get_db_session)):
    stmt = (
        select(
            Deal.stage,
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.amount), 0),
        )
        .group_by(Deal.stage)
    )
    result = await db.execute(stmt)
    rows = result.all()

    stage_order = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]
    funnel_map = {}
    for row in rows:
        sv = row[0].value if hasattr(row[0], "value") else str(row[0])
        funnel_map[sv] = (row[1], float(row[2]))

    return [
        FunnelItem(
            stage=s,
            label=STAGE_LABELS.get(s, s),
            count=funnel_map.get(s, (0, 0))[0],
            total_amount=funnel_map.get(s, (0, 0))[1],
        )
        for s in stage_order
    ]


@router.get("/cockpit/methodology-stats", response_model=MethodologyOverview)
async def cockpit_methodology_stats(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).where(Deal.stage.notin_([DealStage.CLOSED_WON, DealStage.CLOSED_LOST]))
    result = await db.execute(stmt)
    deals = result.scalars().all()

    all_states = []
    for d in deals:
        if d.methodology_state:
            try:
                all_states.append(json.loads(d.methodology_state))
            except Exception:
                pass

    agg = MethodologyEngine.aggregate_team_stats(all_states)
    meddpicc_dims = FRAMEWORK_DEFINITIONS.get("meddpicc", {}).get("dimensions", {})

    dim_stats = []
    for dim_key, avg_val in agg.get("dimension_averages", {}).items():
        label = meddpicc_dims.get(dim_key, {}).get("label", dim_key)
        dim_stats.append(MethodologyDimStat(dimension=dim_key, label=label, avg_pct=avg_val))
    dim_stats.sort(key=lambda x: x.avg_pct)

    weakest = agg.get("weakest")
    return MethodologyOverview(
        avg_score=agg.get("avg_score", 0),
        total_deals=agg.get("total_deals", 0),
        dimension_stats=dim_stats,
        weakest=weakest,
    )


@router.get("/cockpit/feed", response_model=List[EventItem])
async def cockpit_feed(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CockpitEvent).order_by(desc(CockpitEvent.created_at)).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    items = []
    for ev in events:
        payload = None
        try:
            if ev.payload:
                payload = json.loads(ev.payload)
        except Exception:
            pass
        items.append(EventItem(
            id=ev.id,
            event_type=ev.event_type,
            payload=payload,
            created_at=str(ev.created_at) if ev.created_at else "",
        ))
    return items
