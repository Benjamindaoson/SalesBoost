"""Unit tests for FSM state transitions."""
from __future__ import annotations

import pytest

from salesagent.core.constants import SaleStage, StageSignal
from salesagent.fsm.sales_fsm import SalesFSM
from salesagent.utils.exceptions import InvalidTransitionError


def test_fsm_initialization():
    """Test FSM initialization."""
    fsm = SalesFSM(session_id="test_session_001")
    assert fsm.session_id == "test_session_001"
    assert fsm.current_stage == SaleStage.ICEBREAK
    assert len(fsm.history) == 0


@pytest.mark.asyncio
async def test_fsm_valid_transition():
    """Test valid FSM transition."""
    fsm = SalesFSM(session_id="test_session_002")

    # ICEBREAK → DISCOVERY
    new_stage = await fsm.advance(signal=StageSignal.RAPPORT_ESTABLISHED)
    assert new_stage == SaleStage.DISCOVERY
    assert fsm.current_stage == SaleStage.DISCOVERY
    assert len(fsm.history) == 1
    assert fsm.history[0]["from"] == "ICEBREAK"
    assert fsm.history[0]["to"] == "DISCOVERY"


@pytest.mark.asyncio
async def test_fsm_invalid_transition():
    """Test invalid FSM transition raises error."""
    fsm = SalesFSM(session_id="test_session_003")

    # Cannot go directly from ICEBREAK to CLOSING
    with pytest.raises(InvalidTransitionError):
        await fsm.advance(signal=StageSignal.DEAL_CLOSED)


@pytest.mark.asyncio
async def test_fsm_stay_signal():
    """Test STAY signal keeps current stage."""
    fsm = SalesFSM(session_id="test_session_004")

    new_stage = await fsm.advance(signal=StageSignal.STAY)
    assert new_stage == SaleStage.ICEBREAK
    assert fsm.current_stage == SaleStage.ICEBREAK
    assert len(fsm.history) == 0


@pytest.mark.asyncio
async def test_fsm_rollback():
    """Test FSM rollback to previous stage."""
    fsm = SalesFSM(session_id="test_session_005")

    # Advance to DISCOVERY
    await fsm.advance(signal=StageSignal.RAPPORT_ESTABLISHED)
    assert fsm.current_stage == SaleStage.DISCOVERY

    # Advance to PROPOSAL
    await fsm.advance(signal=StageSignal.NEEDS_IDENTIFIED)
    assert fsm.current_stage == SaleStage.PROPOSAL

    # Rollback to DISCOVERY
    new_stage = await fsm.rollback(target_stage=SaleStage.DISCOVERY)
    assert new_stage == SaleStage.DISCOVERY
    assert fsm.current_stage == SaleStage.DISCOVERY
    assert len(fsm.history) == 3  # 2 advances + 1 rollback


@pytest.mark.asyncio
async def test_fsm_full_flow():
    """Test complete FSM flow from ICEBREAK to CLOSING."""
    fsm = SalesFSM(session_id="test_session_006")

    # ICEBREAK → DISCOVERY
    await fsm.advance(signal=StageSignal.RAPPORT_ESTABLISHED)
    assert fsm.current_stage == SaleStage.DISCOVERY

    # DISCOVERY → PROPOSAL
    await fsm.advance(signal=StageSignal.NEEDS_IDENTIFIED)
    assert fsm.current_stage == SaleStage.PROPOSAL

    # PROPOSAL → CLOSING
    await fsm.advance(signal=StageSignal.HIGH_INTENT_DETECTED)
    assert fsm.current_stage == SaleStage.CLOSING

    assert len(fsm.history) == 3
