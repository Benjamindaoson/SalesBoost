"""FSM Node — unified FSM state management within LangGraph."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from salesagent.core.constants import StageSignal
from salesagent.orchestration.state import AgentState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from redis.asyncio import Redis

log = structlog.get_logger()


async def fsm_node(
    state: AgentState,
    db: AsyncSession,
    redis: Redis | None = None,
) -> AgentState:
    """
    FSM Node — manages sales stage transitions within LangGraph.

    This node:
    1. Reads the stage_signal from reasoning_output
    2. Advances the FSM state machine
    3. Updates the AgentState with new FSM stage
    4. Persists to DB and emits Redis events

    Benefits:
    - Centralizes FSM logic within the graph
    - Ensures state consistency with LangGraph checkpointing
    - Eliminates manual FSM.advance() calls in chat.py
    """
    from salesagent.fsm.sales_fsm import SalesFSM

    session_id = state.get("session_id")
    reasoning_output = state.get("reasoning_output")

    if not session_id or not reasoning_output:
        log.warning("FSM node: missing session_id or reasoning_output")
        return state

    try:
        # Load FSM from DB
        fsm = await SalesFSM.from_session(session_id, db)

        # Extract stage signal from reasoning output
        signal_str = reasoning_output.stage_signal
        signal = StageSignal(signal_str)

        # Advance FSM
        new_stage = await fsm.advance(signal=signal, db=db, redis=redis)

        # Update state
        state["fsm_stage"] = new_stage

        log.info(
            "FSM node: stage transition",
            session_id=session_id,
            signal=signal.value,
            new_stage=new_stage.value,
        )

    except Exception as exc:
        log.error("FSM node: transition failed", error=str(exc), session_id=session_id)
        # Keep current stage on error

    return state
