"""Reasoning Node — the first and most critical node in the DAG."""
from __future__ import annotations

import structlog
from opentelemetry import trace

from salesagent.orchestration.state import AgentState
from salesagent.reasoning.chain import SalesReasoningChain

log = structlog.get_logger()
tracer = trace.get_tracer(__name__)


async def reasoning_node(state: AgentState, gateway: object, redis: object = None) -> AgentState:
    """
    Run the Sales Reasoning Chain before any response is generated.
    Output is stored in state['reasoning_output'] for all downstream nodes.
    """
    with tracer.start_as_current_span("reasoning_node") as span:
        span.set_attribute("session_id", state.get("session_id", ""))
        span.set_attribute("fsm_stage", state["fsm_stage"].value)

        chain = SalesReasoningChain(gateway=gateway, redis=redis)
        try:
            result = await chain.run(
                messages=state.get("messages", []),
                fsm_stage=state["fsm_stage"],
                customer_profile=state.get("customer_profile", {}),
                session_id=state.get("session_id", ""),
                use_lite=state.get("use_lite_path", False),
            )
            state["reasoning_output"] = result

            span.set_attribute("stage_signal", result.stage_signal)
            span.set_attribute("primary_tactic", result.recommended_tactics.primary)
            span.set_attribute("confidence", result.confidence)

            log.info(
                "Reasoning complete",
                session_id=state.get("session_id"),
                stage_signal=result.stage_signal,
                primary_tactic=result.recommended_tactics.primary,
                confidence=result.confidence,
            )
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))

            log.error("Reasoning node failed", error=str(exc))
            from salesagent.reasoning.schemas import CONSERVATIVE_REASONING
            state["reasoning_output"] = CONSERVATIVE_REASONING
            state["error"] = f"reasoning_failed: {exc}"

        return state
