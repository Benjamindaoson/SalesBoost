"""MVP compliance check API."""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_user
from api.auth_schemas import UserSchema as User
from app.agents.roles.compliance_agent import ComplianceAgent
from core.database import get_db_session
from models.compliance_models import ComplianceLog
from schemas.fsm import SalesStage
from schemas.mvp import ComplianceCheckRequest, ComplianceCheckResponse, RiskLevel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mvp/compliance", tags=["mvp"])

compliance_agent = ComplianceAgent()


@router.post("/check", response_model=ComplianceCheckResponse)
async def check_compliance(
    request: ComplianceCheckRequest,
    session_id: Optional[str] = Query(None),
    turn_number: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    try:
        ctx = dict(request.context or {})
        if session_id:
            ctx["session_id"] = session_id
        ctx["user_id"] = current_user.id
        ctx["tenant_id"] = current_user.tenant_id
        compliance_result = await compliance_agent.check(
            message=request.text,
            stage=SalesStage.OBJECTION_HANDLING,
            context=ctx,
        )

        risk_level = RiskLevel.OK
        if compliance_result.risk_level == "BLOCK":
            risk_level = RiskLevel.BLOCK
        elif compliance_result.risk_level == "WARN":
            risk_level = RiskLevel.WARN

        risk_tags = [flag.risk_type for flag in compliance_result.risk_flags]

        reason = None
        if risk_level != RiskLevel.OK:
            reason = "Compliance risk detected"

        if risk_level != RiskLevel.OK and session_id:
            try:
                log_entry = ComplianceLog(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    turn_number=turn_number or 0,
                    original=request.text,
                    rewrite=compliance_result.safe_rewrite,
                    risk_tags=risk_tags,
                    risk_level=risk_level.value,
                    detected_at=datetime.utcnow(),
                )
                db.add(log_entry)
                await db.commit()
            except Exception as e:
                logger.error("Failed to log compliance event: %s", e)

        return ComplianceCheckResponse(
            risk_level=risk_level,
            risk_tags=risk_tags,
            safe_rewrite=compliance_result.safe_rewrite,
            original=request.text,
            reason=reason,
        )

    except Exception as e:
        logger.error("Compliance check failed: %s", e, exc_info=True)
        return ComplianceCheckResponse(
            risk_level=RiskLevel.BLOCK,
            risk_tags=["system_error"],
            safe_rewrite="Compliance system unavailable",
            original=request.text,
            reason="Compliance system unavailable",
        )
