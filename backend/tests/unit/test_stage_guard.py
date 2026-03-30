"""Tests for FSM stage transition guard."""
import pytest
from app.agents.conversation.intent_routing import (
    SalesStage,
    VALID_TRANSITIONS,
    validate_stage_transition,
)


def test_valid_forward_opening_to_discovery():
    ok, err = validate_stage_transition(SalesStage.OPENING, SalesStage.DISCOVERY)
    assert ok is True
    assert err is None


def test_valid_same_stage():
    ok, err = validate_stage_transition(SalesStage.DISCOVERY, SalesStage.DISCOVERY)
    assert ok is True
    assert err is None


def test_invalid_skip_opening_to_closing():
    ok, err = validate_stage_transition(SalesStage.OPENING, SalesStage.CLOSING)
    assert ok is False
    assert "INVALID_TRANSITION" in err
    assert "closing" in err


def test_invalid_backward_pitch_to_opening():
    ok, err = validate_stage_transition(SalesStage.PITCH, SalesStage.OPENING)
    assert ok is False
    assert "INVALID_TRANSITION" in err


def test_none_current_always_valid():
    """First message has no prior stage — any initial stage is allowed."""
    ok, err = validate_stage_transition(None, SalesStage.OPENING)
    assert ok is True
    assert err is None


def test_objection_can_go_back_to_pitch():
    """Objection handling can return to pitch — valid sales pattern."""
    ok, err = validate_stage_transition(SalesStage.OBJECTION_HANDLING, SalesStage.PITCH)
    assert ok is True


def test_completed_is_terminal():
    """Completed stage cannot transition to any other stage."""
    ok, err = validate_stage_transition(SalesStage.COMPLETED, SalesStage.OPENING)
    assert ok is False


def test_valid_transitions_covers_all_stages():
    """Every SalesStage must appear as a key in VALID_TRANSITIONS."""
    for stage in SalesStage:
        assert stage in VALID_TRANSITIONS, f"{stage} missing from VALID_TRANSITIONS"
