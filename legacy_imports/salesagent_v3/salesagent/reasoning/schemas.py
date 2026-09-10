"""Reasoning Chain output schema."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PsychologicalRadar(BaseModel):
    """3D Intent Space for Tactical Engine 2.0."""
    trust_score: float = Field(ge=0.0, le=1.0, default=0.5, description="Confidence in the agent/solution")
    urgency_score: float = Field(ge=0.0, le=1.0, default=0.5, description="Need for immediate action")
    friction_intensity: float = Field(ge=0.0, le=1.0, default=0.2, description="Resistance or objection depth")

class CustomerSignals(BaseModel):
    radar: PsychologicalRadar = Field(default_factory=PsychologicalRadar)
    objection_type: str = "none"  # price_sensitivity | timeline | trust | feature_gap | none
    decision_stage: str = "awareness"  # awareness | consideration | evaluation | decision


class RecommendedTactics(BaseModel):
    primary: str = "consultative_questioning"
    secondary: str = "empathy_acknowledgment"
    tone: str = "consultative_not_pushy"
    avoid: list[str] = Field(default_factory=list)


class ReasoningOutput(BaseModel):
    """Structured output of the Sales Reasoning Chain — NOT sent to customers."""

    thinking_chain: str = Field(..., description="Internal monologue of the strategist")
    literal_intent: str = Field(..., description="What the user is explicitly asking")
    hidden_concerns: list[str] = Field(
        default_factory=list,
        description="Implicit concerns inferred from context",
    )
    customer_signals: CustomerSignals = Field(default_factory=CustomerSignals)

    # DSP (Phase 9)
    strategy_plan: str = Field(..., description="High-level strategic goal")
    tactical_instructions: str = Field(..., description="Specific instructions for the response generator")

    tone: str = "consultative_not_pushy"
    avoid: list[str] = Field(default_factory=list)

    stage_signal: str = Field(
        default="stay",
        description="Signal to feed back into FSM (maps to StageSignal enum values)",
    )
    reasoning_trace: str = Field(
        default="",
        description="Human-readable trace of the reasoning process",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)

    @field_validator("stage_signal")
    @classmethod
    def validate_stage_signal(cls, v: str) -> str:
        from salesagent.core.constants import StageSignal
        valid = {s.value for s in StageSignal}
        if v not in valid:
            return StageSignal.STAY.value
        return v


# Default conservative output used when schema validation fails
CONSERVATIVE_REASONING = ReasoningOutput(
    thinking_chain="Schema validation failed, falling back to rapport maintenance.",
    literal_intent="Customer message received",
    hidden_concerns=[],
    customer_signals=CustomerSignals(),
    strategy_plan="Maintain rapport and seek clarification",
    tactical_instructions="Acknowledge the message with empathy and ask an open-ended question to understand their context better.",
    tone="consultative_not_pushy",
    avoid=["hard_close", "discount_offer"],
    stage_signal="stay",
    reasoning_trace="Fallback to conservative strategy due to reasoning parse failure.",
    confidence=0.0,
)

class CustomerPersonaVector(BaseModel):
    """Multi-dimensional vector modeling for Analyzer Node."""
    trust_score: int = Field(ge=0, le=100, description="Based on intimacy and response speed")
    urgency: int = Field(ge=0, le=100, description="Level of urgency to solve the problem")
    friction_points: list[str] = Field(default_factory=list, description="Extracted resistance points (price, tech, etc.)")
    intent_cluster: str = Field(..., description="Current semantic psychological position")
