"""Sales coach agent stub."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    OPENING = "opening"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    CLOSING = "closing"


@dataclass
class ComplianceRisk:
    risk_level: str
    sensitive_words: list[str]
    warning_message: str


@dataclass
class CoachAdvice:
    phase: Phase
    detected_phase: Phase
    phase_transition_detected: bool
    customer_intent: str
    action_advice: str
    script_example: str
    compliance_risk: Optional[ComplianceRisk] = None


class SalesCoachAgent:
    async def get_advice(self, history, session_id: str, current_context=None, turn_number: int = 0) -> CoachAdvice:
        return CoachAdvice(
            phase=Phase.DISCOVERY,
            detected_phase=Phase.DISCOVERY,
            phase_transition_detected=False,
            customer_intent="general_inquiry",
            action_advice="Ask a clarifying question.",
            script_example="Could you share more details about your situation?",
            compliance_risk=None,
        )
