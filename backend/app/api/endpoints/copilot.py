"""
Copilot API
===========
Real-time sales assistance API.

Pipeline: Intent Recognition → Stage Inference → Strategy Generation
Powered by LiveAssistEngine (single LLM call + MEDDPICC context + rep weakness profile).

Endpoints:
  POST /copilot/suggest  — Live call assistance
  POST /copilot/prep     — Pre-call battle prep
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...core.config import settings
from ...models.deal import Deal
from ...services.methodology_engine import (
    MethodologyEngine,
    MethodologyState,
)
from ...services.live_assist_engine import LiveAssistEngine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["copilot"])

# Singleton engine (reuses ModelGateway connection pool)
_engine = LiveAssistEngine()


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class CopilotSuggestRequest(BaseModel):
    deal_id: Optional[int] = None
    customer_message: str
    context: Optional[Dict[str, Any]] = None
    methodology: str = "meddpicc"
    mode: str = "live"          # live | prep
    user_id: Optional[str] = None  # Passed by frontend from JWT claims


class Suggestion(BaseModel):
    content: str
    tactic: str
    confidence: float
    rationale: str = ""         # NEW: AI explanation for why this tactic


class CopilotSuggestResponse(BaseModel):
    # Core suggestions
    suggestions: List[Suggestion]

    # Stage info
    detected_stage: str = "discovery"
    stage_confidence: float = 0.5    # NEW: model confidence in stage detection

    # Intent info (NEW)
    intent_type: str = "UNKNOWN"
    intent_confidence: float = 0.0
    intent_reasoning: str = ""       # Chain-of-thought visible in UI

    # Methodology
    methodology_context: Optional[Dict[str, Any]] = None
    detected_dimensions: List[str] = []
    methodology_gaps: List[str] = []   # NEW: MEDDPICC dimensions to address

    # Personalization flag (NEW)
    personalized: bool = False


class CopilotPrepRequest(BaseModel):
    deal_id: int


class CopilotPrepResponse(BaseModel):
    battle_plan: str
    methodology_state: Dict[str, Any]
    key_gaps: List[Dict[str, Any]]
    talking_points: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/copilot/suggest", response_model=CopilotSuggestResponse)
async def copilot_suggest(
    body: CopilotSuggestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Live Assist: analyze a customer utterance and return real-time action suggestions.

    Pipeline:
      1. Resolve user_id from request (JWT token or body field)
      2. Load MEDDPICC methodology state from Deal (if deal_id provided)
      3. Run 3-stage AI decision chain via LiveAssistEngine
      4. Return enriched response with intent, stage, and ranked suggestions
    """
    # ------------------------------------------------------------------
    # 1. Resolve user_id for personalization
    # ------------------------------------------------------------------
    user_id: Optional[str] = body.user_id
    if not user_id:
        # Try to extract from JWT claims attached by auth middleware
        token_data = getattr(request.state, "user", None)
        if token_data:
            user_id = str(getattr(token_data, "id", None) or getattr(token_data, "user_id", None))

    # ------------------------------------------------------------------
    # 2. Load methodology state from Deal (for MEDDPICC context)
    # ------------------------------------------------------------------
    methodology_state: Optional[MethodologyState] = None
    if body.deal_id:
        stmt = select(Deal).where(Deal.id == body.deal_id)
        result = await db.execute(stmt)
        deal = result.scalar_one_or_none()
        if deal and deal.methodology_state:
            methodology_state = MethodologyState.from_json(deal.methodology_state)

    # ------------------------------------------------------------------
    # 3. Run AI decision chain
    # ------------------------------------------------------------------
    analysis = await _engine.analyze(
        customer_message=body.customer_message,
        user_id=user_id,
        methodology_state=methodology_state,
        session_id=f"live-{body.deal_id or 'no-deal'}",
        enable_llm=settings.ENABLE_LLM_INTENT,
    )

    # ------------------------------------------------------------------
    # 4. Build response
    # ------------------------------------------------------------------
    api_data = LiveAssistEngine.to_api_response(analysis)

    return CopilotSuggestResponse(
        suggestions=[
            Suggestion(
                content=s["content"],
                tactic=s["tactic"],
                confidence=s["confidence"],
                rationale=s["rationale"],
            )
            for s in api_data["suggestions"]
        ],
        detected_stage=api_data["detected_stage"],
        stage_confidence=api_data["stage_confidence"],
        intent_type=api_data["intent_type"],
        intent_confidence=api_data["intent_confidence"],
        intent_reasoning=api_data["intent_reasoning"],
        methodology_context=MethodologyEngine.generate_live_coaching_context(methodology_state) if methodology_state else None,
        detected_dimensions=api_data["methodology_gaps"],
        methodology_gaps=api_data["methodology_gaps"],
        personalized=api_data["personalized"],
    )


@router.post("/copilot/prep", response_model=CopilotPrepResponse)
async def copilot_prep(
    body: CopilotPrepRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Pre-call battle prep: generate a structured preparation plan from MEDDPICC state."""
    stmt = select(Deal).where(Deal.id == body.deal_id)
    result = await db.execute(stmt)
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    state = MethodologyState.from_json(deal.methodology_state or "")
    battle_plan = MethodologyEngine.generate_prep_prompt(state, deal.customer_info or "")
    gaps = state.gap_analysis()

    talking_points = [
        g["probe_questions"][0]
        for g in gaps[:3]
        if g.get("probe_questions")
    ]

    return CopilotPrepResponse(
        battle_plan=battle_plan,
        methodology_state=state.to_dict(),
        key_gaps=gaps[:5],
        talking_points=talking_points,
    )
