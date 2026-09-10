"""FSM: Deterministic Sales Funnel State Machine - Macro Lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from salesagent.core.constants import SaleStage, StageSignal

@dataclass
class StageConfig:
    """Configuration for a single FSM stage."""
    stage: SaleStage
    display_name: str
    description: str
    exit_signals: list[StageSignal]
    allowed_back_transitions: list[SaleStage] = field(default_factory=list)

# ── Stage configurations (Streamlined for DSP) ────────────────────────────────

STAGE_CONFIGS: dict[SaleStage, StageConfig] = {
    SaleStage.ICEBREAK: StageConfig(
        stage=SaleStage.ICEBREAK,
        display_name="Rapport & Context",
        description="Establish trust and gather initial customer background.",
        exit_signals=[StageSignal.RAPPORT_ESTABLISHED],
        allowed_back_transitions=[],
    ),
    SaleStage.DISCOVERY: StageConfig(
        stage=SaleStage.DISCOVERY,
        display_name="Qualification & Needs",
        description="Deep dive into customer pain points, budget, and business needs.",
        exit_signals=[StageSignal.NEEDS_IDENTIFIED, StageSignal.HIGH_INTENT_DETECTED],
        allowed_back_transitions=[SaleStage.ICEBREAK],
    ),
    SaleStage.PROPOSAL: StageConfig(
        stage=SaleStage.PROPOSAL,
        display_name="Value Alignment",
        description="Propose solution, address concerns, and align value to needs.",
        exit_signals=[
            StageSignal.OBJECTION_RAISED,
            StageSignal.HIGH_INTENT_DETECTED,
            StageSignal.OBJECTION_RESOLVED,
            StageSignal.OBJECTION_OVERCOME,
        ],
        allowed_back_transitions=[SaleStage.DISCOVERY],
    ),
    SaleStage.CLOSING: StageConfig(
        stage=SaleStage.CLOSING,
        display_name="Decision & Commitment",
        description="Finalize agreement and drive to close.",
        exit_signals=[StageSignal.DEAL_CLOSED, StageSignal.SESSION_ENDED],
        allowed_back_transitions=[SaleStage.PROPOSAL, SaleStage.DISCOVERY],
    ),
}
