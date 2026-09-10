"""Deterministic transition rules — Zero LLM dependency."""
from __future__ import annotations

from salesagent.core.constants import SaleStage, StageSignal
from salesagent.utils.exceptions import InvalidTransitionError

# ── Transition table (Streamlined for macro lifecycle) ─────────────────────────

_TRANSITIONS: dict[tuple[SaleStage, StageSignal], SaleStage] = {
    # ICEBREAK
    (SaleStage.ICEBREAK, StageSignal.RAPPORT_ESTABLISHED): SaleStage.DISCOVERY,

    # DISCOVERY
    (SaleStage.DISCOVERY, StageSignal.NEEDS_IDENTIFIED): SaleStage.PROPOSAL,
    (SaleStage.DISCOVERY, StageSignal.HIGH_INTENT_DETECTED): SaleStage.PROPOSAL,

    # PROPOSAL (Now handles objections within stage context via Strategist Agent)
    (SaleStage.PROPOSAL, StageSignal.HIGH_INTENT_DETECTED): SaleStage.CLOSING,
    (SaleStage.PROPOSAL, StageSignal.OBJECTION_OVERCOME): SaleStage.CLOSING,

    # CLOSING
    (SaleStage.CLOSING, StageSignal.DEAL_CLOSED): SaleStage.CLOSING, # terminal loop
    (SaleStage.CLOSING, StageSignal.SESSION_ENDED): SaleStage.CLOSING, # terminal loop

    # Universal back-transition: new need surfaced → back to DISCOVERY
    (SaleStage.PROPOSAL, StageSignal.NEW_NEED_SURFACED): SaleStage.DISCOVERY,
    (SaleStage.CLOSING, StageSignal.NEW_NEED_SURFACED): SaleStage.DISCOVERY,
}

def can_transition(current: SaleStage, signal: StageSignal) -> bool:
    if signal == StageSignal.STAY:
        return False
    return (current, signal) in _TRANSITIONS

def get_next_stage(current: SaleStage, signal: StageSignal) -> SaleStage:
    if signal == StageSignal.STAY:
        return current
    key = (current, signal)
    if key not in _TRANSITIONS:
        raise InvalidTransitionError(
            message=f"No transition defined: {current.value} + {signal.value}",
        )
    return _TRANSITIONS[key]
