"""Flywheel API — preference pairs, DPO export, APO trigger."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db
from salesagent.models.db_models import PreferencePair
from salesagent.models.schemas import FlywheelStatusResponse, PreferencePairResponse
from salesagent.auth.dependencies import get_current_user
from salesagent.auth.permissions import require_admin

router = APIRouter()


@router.get("/status", response_model=FlywheelStatusResponse)
async def flywheel_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FlywheelStatusResponse:
    from sqlalchemy import case

    total = await db.scalar(select(func.count(PreferencePair.id))) or 0
    exported = await db.scalar(
        select(func.count(PreferencePair.id)).where(PreferencePair.exported == True)  # noqa: E712
    ) or 0

    return FlywheelStatusResponse(
        total_preference_pairs=total,
        exported_pairs=exported,
        pending_pairs=total - exported,
        last_apo_cycle=None,
        avg_reward_last_100=None,
        reward_trend="stable",
    )


@router.get("/preference-pairs", response_model=list[PreferencePairResponse])
async def list_preference_pairs(
    limit: int = 20,
    offset: int = 0,
    exported: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PreferencePairResponse]:
    q = select(PreferencePair).order_by(PreferencePair.created_at.desc()).limit(limit).offset(offset)
    if exported is not None:
        q = q.where(PreferencePair.exported == exported)
    result = await db.execute(q)
    return [PreferencePairResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/export-dpo")
async def export_dpo(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),  # Admin only
) -> Response:
    """Export all preference pairs as JSONL for DPO training."""
    result = await db.execute(
        select(PreferencePair).where(PreferencePair.exported == False)  # noqa: E712
    )
    pairs = result.scalars().all()

    lines = []
    for p in pairs:
        lines.append(json.dumps({
            "prompt": p.user_message,
            "chosen": p.chosen_response,
            "rejected": p.rejected_response,
            "reward_scores": p.reward_scores,
            "metadata": p.metadata_,
        }, ensure_ascii=False))
        p.exported = True

    await db.commit()

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="dpo_pairs_{datetime.now().strftime("%Y%m%d")}.jsonl"'},
    )


@router.post("/apo-cycle")
async def trigger_apo_cycle(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),  # Admin only
) -> dict:
    """Manually trigger an APO optimization cycle."""
    from salesagent.flywheel.apo_engine import APOEngine
    from salesagent.llm.gateway import ModelGateway
    gateway = ModelGateway()
    await gateway.initialize()
    engine = APOEngine(db=db, gateway=gateway)
    result = await engine.run_cycle()
    return {"status": "ok", "result": result}
