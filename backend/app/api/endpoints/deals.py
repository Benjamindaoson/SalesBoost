"""
Deals & Pipeline API

CRUD for deals, encounters, methodology state management, and pipeline/funnel views.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db_session
from ...models.deal import Deal, DealStage, Encounter, EncounterType, CockpitEvent
from ...services.methodology_engine import (
    MethodologyEngine,
    MethodologyState,
    FRAMEWORK_DEFINITIONS,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["deals"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DealCreate(BaseModel):
    customer_name: str
    customer_company: Optional[str] = None
    customer_title: Optional[str] = None
    customer_info: Optional[str] = None
    amount: float = 0
    stage: str = DealStage.LEAD
    methodology_framework: str = "meddpicc"
    expected_close_date: Optional[str] = None


class DealUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_company: Optional[str] = None
    customer_title: Optional[str] = None
    customer_info: Optional[str] = None
    amount: Optional[float] = None
    stage: Optional[str] = None
    expected_close_date: Optional[str] = None
    close_reason: Optional[str] = None


class DimensionUpdate(BaseModel):
    dimension: str
    status: str  # unknown / partial / confirmed
    evidence: str = ""


class EncounterCreate(BaseModel):
    encounter_type: str  # prep / live / review
    session_id: Optional[int] = None
    summary: Optional[str] = None
    action_items: Optional[str] = None


class DealResponse(BaseModel):
    id: int
    tenant_id: str
    owner_id: int
    customer_name: str
    customer_company: Optional[str] = None
    customer_title: Optional[str] = None
    customer_info: Optional[str] = None
    amount: float
    stage: str
    methodology_framework: str
    methodology_state: Optional[dict] = None
    methodology_score: float
    expected_close_date: Optional[str] = None
    close_reason: Optional[str] = None
    encounter_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EncounterResponse(BaseModel):
    id: int
    deal_id: int
    session_id: Optional[int] = None
    encounter_type: str
    summary: Optional[str] = None
    methodology_before: Optional[dict] = None
    methodology_after: Optional[dict] = None
    action_items: Optional[str] = None
    created_at: Optional[str] = None


class FunnelResponse(BaseModel):
    stage: str
    count: int
    total_amount: float


class PrepPromptResponse(BaseModel):
    prompt: str
    methodology_state: dict
    gaps: list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deal_to_response(deal: Deal) -> DealResponse:
    ms = None
    if deal.methodology_state:
        try:
            ms = json.loads(deal.methodology_state)
        except Exception:
            ms = None
    enc_count = len(deal.encounters) if deal.encounters else 0
    return DealResponse(
        id=deal.id,
        tenant_id=deal.tenant_id or "",
        owner_id=deal.owner_id,
        customer_name=deal.customer_name,
        customer_company=deal.customer_company,
        customer_title=deal.customer_title,
        customer_info=deal.customer_info,
        amount=deal.amount or 0,
        stage=deal.stage.value if hasattr(deal.stage, "value") else str(deal.stage),
        methodology_framework=deal.methodology_framework or "meddpicc",
        methodology_state=ms,
        methodology_score=deal.methodology_score or 0,
        expected_close_date=str(deal.expected_close_date) if deal.expected_close_date else None,
        close_reason=deal.close_reason,
        encounter_count=enc_count,
        created_at=str(deal.created_at) if deal.created_at else None,
        updated_at=str(deal.updated_at) if deal.updated_at else None,
    )


def _encounter_to_response(enc: Encounter) -> EncounterResponse:
    mb = None
    ma = None
    try:
        if enc.methodology_before:
            mb = json.loads(enc.methodology_before)
        if enc.methodology_after:
            ma = json.loads(enc.methodology_after)
    except Exception:
        pass
    return EncounterResponse(
        id=enc.id,
        deal_id=enc.deal_id,
        session_id=enc.session_id,
        encounter_type=enc.encounter_type.value if hasattr(enc.encounter_type, "value") else str(enc.encounter_type),
        summary=enc.summary,
        methodology_before=mb,
        methodology_after=ma,
        action_items=enc.action_items,
        created_at=str(enc.created_at) if enc.created_at else None,
    )


# ---------------------------------------------------------------------------
# Deal CRUD
# ---------------------------------------------------------------------------

@router.post("/deals", response_model=DealResponse)
async def create_deal(
    body: DealCreate,
    db: AsyncSession = Depends(get_db_session),
):
    state = MethodologyEngine.create_state(body.methodology_framework)
    deal = Deal(
        tenant_id="default",
        owner_id=1,
        customer_name=body.customer_name,
        customer_company=body.customer_company,
        customer_title=body.customer_title,
        customer_info=body.customer_info,
        amount=body.amount,
        stage=body.stage,
        methodology_framework=body.methodology_framework,
        methodology_state=state.to_json(),
        methodology_score=state.overall_score,
        expected_close_date=datetime.fromisoformat(body.expected_close_date) if body.expected_close_date else None,
    )
    db.add(deal)
    await db.flush()

    event = CockpitEvent(
        tenant_id=deal.tenant_id,
        user_id=deal.owner_id,
        event_type="deal_created",
        deal_id=deal.id,
        payload=json.dumps({"customer_name": deal.customer_name, "stage": body.stage}, ensure_ascii=False),
    )
    db.add(event)
    await db.flush()

    return _deal_to_response(deal)


@router.get("/deals", response_model=List[DealResponse])
async def list_deals(
    stage: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(Deal).options(selectinload(Deal.encounters)).order_by(Deal.updated_at.desc())
    if stage:
        stmt = stmt.where(Deal.stage == stage)
    result = await db.execute(stmt)
    deals = result.scalars().all()
    return [_deal_to_response(d) for d in deals]


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).options(selectinload(Deal.encounters)).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal_to_response(deal)


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(deal_id: int, body: DealUpdate, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).options(selectinload(Deal.encounters)).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    old_stage = deal.stage

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "expected_close_date" and value:
            value = datetime.fromisoformat(value)
        setattr(deal, field, value)

    if body.stage and body.stage != (old_stage.value if hasattr(old_stage, "value") else old_stage):
        event = CockpitEvent(
            tenant_id=deal.tenant_id,
            user_id=deal.owner_id,
            event_type="stage_changed",
            deal_id=deal.id,
            payload=json.dumps({
                "from": old_stage.value if hasattr(old_stage, "value") else str(old_stage),
                "to": body.stage,
                "customer_name": deal.customer_name,
            }, ensure_ascii=False),
        )
        db.add(event)

    await db.flush()
    return _deal_to_response(deal)


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: int, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await db.delete(deal)
    await db.flush()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Methodology State
# ---------------------------------------------------------------------------

@router.get("/deals/{deal_id}/methodology")
async def get_methodology(deal_id: int, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    state = MethodologyState.from_json(deal.methodology_state or "")
    defn = FRAMEWORK_DEFINITIONS.get(state.framework, {})
    return {
        "framework": state.framework,
        "framework_label": defn.get("label", state.framework),
        "dimensions": state.to_dict()["dimensions"],
        "overall_score": state.overall_score,
        "next_focus": state.next_focus,
        "gaps": state.gap_analysis(),
    }


@router.put("/deals/{deal_id}/methodology/dimensions")
async def update_methodology_dimension(
    deal_id: int,
    body: DimensionUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(Deal).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    state = MethodologyState.from_json(deal.methodology_state or "")
    state.update_dimension(body.dimension, body.status, body.evidence)

    deal.methodology_state = state.to_json()
    deal.methodology_score = state.overall_score

    suggested_stage = MethodologyEngine.suggest_stage_from_score(state.overall_score)

    event = CockpitEvent(
        tenant_id=deal.tenant_id,
        user_id=deal.owner_id,
        event_type="methodology_updated",
        deal_id=deal.id,
        payload=json.dumps({
            "dimension": body.dimension,
            "status": body.status,
            "score": state.overall_score,
            "customer_name": deal.customer_name,
        }, ensure_ascii=False),
    )
    db.add(event)
    await db.flush()

    return {
        "ok": True,
        "overall_score": state.overall_score,
        "next_focus": state.next_focus,
        "suggested_stage": suggested_stage,
    }


@router.get("/deals/{deal_id}/prep-prompt", response_model=PrepPromptResponse)
async def get_prep_prompt(deal_id: int, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Deal).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    state = MethodologyState.from_json(deal.methodology_state or "")
    prompt = MethodologyEngine.generate_prep_prompt(state, deal.customer_info or "")
    return PrepPromptResponse(
        prompt=prompt,
        methodology_state=state.to_dict(),
        gaps=state.gap_analysis(),
    )


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------

@router.post("/deals/{deal_id}/encounters", response_model=EncounterResponse)
async def create_encounter(
    deal_id: int,
    body: EncounterCreate,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(Deal).where(Deal.id == deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    enc = Encounter(
        deal_id=deal_id,
        session_id=body.session_id,
        encounter_type=body.encounter_type,
        summary=body.summary,
        methodology_before=deal.methodology_state,
        action_items=body.action_items,
    )
    db.add(enc)

    event = CockpitEvent(
        tenant_id=deal.tenant_id,
        user_id=deal.owner_id,
        event_type="encounter_completed",
        deal_id=deal.id,
        payload=json.dumps({
            "encounter_type": body.encounter_type,
            "customer_name": deal.customer_name,
        }, ensure_ascii=False),
    )
    db.add(event)
    await db.flush()

    return _encounter_to_response(enc)


@router.get("/deals/{deal_id}/encounters", response_model=List[EncounterResponse])
async def list_encounters(deal_id: int, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Encounter).where(Encounter.deal_id == deal_id).order_by(Encounter.created_at.desc())
    result = await db.execute(stmt)
    encounters = result.scalars().all()
    return [_encounter_to_response(e) for e in encounters]


# ---------------------------------------------------------------------------
# Pipeline / Funnel
# ---------------------------------------------------------------------------

@router.get("/pipeline/funnel", response_model=List[FunnelResponse])
async def get_funnel(db: AsyncSession = Depends(get_db_session)):
    stmt = (
        select(
            Deal.stage,
            func.count(Deal.id).label("count"),
            func.coalesce(func.sum(Deal.amount), 0).label("total_amount"),
        )
        .where(Deal.stage.notin_(["closed_won", "closed_lost"]))
        .group_by(Deal.stage)
    )
    result = await db.execute(stmt)
    rows = result.all()

    stage_order = ["lead", "qualified", "proposal", "negotiation"]
    funnel = {s: FunnelResponse(stage=s, count=0, total_amount=0) for s in stage_order}

    for row in rows:
        stage_val = row[0].value if hasattr(row[0], "value") else str(row[0])
        if stage_val in funnel:
            funnel[stage_val] = FunnelResponse(stage=stage_val, count=row[1], total_amount=float(row[2]))

    return [funnel[s] for s in stage_order]


# ---------------------------------------------------------------------------
# Methodology Frameworks Reference
# ---------------------------------------------------------------------------

@router.get("/methodology/frameworks")
async def list_frameworks():
    return MethodologyEngine.list_frameworks()


@router.get("/methodology/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    defn = FRAMEWORK_DEFINITIONS.get(framework_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Framework not found")
    return defn
