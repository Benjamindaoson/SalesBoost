"""Sales Coach API."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from api.deps import require_user
from api.auth_schemas import UserSchema as User
from api.auth_utils import get_current_user_from_token
from api.v1.schemas import CoachProcessRequest, CoachProcessResponse
from app.agents.ask.coach_agent import SalesCoachAgent
from core.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coach", tags=["coach"])
_coach_agent: Optional[SalesCoachAgent] = None


def _get_agent() -> SalesCoachAgent:
    global _coach_agent
    if _coach_agent is None:
        _coach_agent = SalesCoachAgent()
    return _coach_agent


def _advice_to_response(advice: Any) -> CoachProcessResponse:
    risk = None
    if advice.compliance_risk:
        risk = {
            "risk_level": advice.compliance_risk.risk_level,
            "sensitive_words": advice.compliance_risk.sensitive_words,
            "warning_message": advice.compliance_risk.warning_message,
        }
    return CoachProcessResponse(
        success=True,
        phase=advice.phase.value,
        detected_phase=advice.detected_phase.value,
        phase_transition_detected=advice.phase_transition_detected,
        customer_intent=advice.customer_intent,
        action_advice=advice.action_advice,
        script_example=advice.script_example,
        compliance_risk=risk,
    )


@router.post("/process", response_model=CoachProcessResponse)
async def coach_process(
    req: CoachProcessRequest,
    current_user: User = Depends(require_user),
) -> CoachProcessResponse:
    try:
        agent = _get_agent()
        history = list(req.history)
        if req.text_stream:
            history.append({"role": "sales", "content": req.text_stream})

        advice = await agent.get_advice(
            history=history,
            session_id=req.session_id,
            current_context=req.current_context,
            turn_number=req.turn_number,
        )
        return _advice_to_response(advice)
    except Exception as e:
        logger.exception("coach process error: %s", e)
        raise HTTPException(status_code=500, detail="Coach process failed")


@router.websocket("/ws/{session_id}")
async def coach_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        token = None
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            await websocket.close(code=4401, reason="Unauthorized")
            return
        async for db in get_db_session():
            await get_current_user_from_token(token, db)
            break

        await websocket.send_json({"type": "connected", "session_id": session_id})
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type == "transcript_chunk":
                await websocket.send_json({"type": "ack", "message": "transcript_chunk received"})
                continue
            if msg_type == "close":
                break
            await websocket.send_json({"type": "error", "message": f"unknown type: {msg_type}"})
    except WebSocketDisconnect:
        logger.info("coach ws disconnect: %s", session_id)
    except Exception as e:
        logger.exception("coach ws error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": "internal error"})
        except Exception:
            pass
