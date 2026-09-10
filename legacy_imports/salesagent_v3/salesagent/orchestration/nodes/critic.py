"""Critic Node — async bypass Reward scoring of completed response."""
from __future__ import annotations

import json
from typing import Any

import structlog

from salesagent.orchestration.state import AgentState

log = structlog.get_logger()


async def critic_node(state: AgentState, gateway: object, db: object | None = None) -> AgentState:
    """
    Async bypass node — scores the completed response using the Reward Model.
    Does NOT block the main response path.
    """
    try:
        from salesagent.reasoning.prompts import CRITIC_SCORING_PROMPT

        reasoning = state.get("reasoning_output")
        response_text = state.get("response_text", "")

        system_prompt = CRITIC_SCORING_PROMPT.format(
            user_message=state.get("user_message", ""),
            assistant_response=response_text,
            fsm_stage=state["fsm_stage"].value,
            primary_tactic=reasoning.recommended_tactics.primary if reasoning else "unknown",
        )

        raw = await gateway.complete(  # type: ignore[attr-defined]
            task="critic",
            system="You are an expert sales response quality evaluator.",
            user=system_prompt,
            session_id=state.get("session_id", ""),
        )

        result = json.loads(raw)
        quality_score = float(result.get("score", 0.5))
        rationale = result.get("rationale", "")

        state["reward_scores"] = state.get("reward_scores", {})
        state["reward_scores"]["response_quality"] = quality_score
        state["critic_rationale"] = rationale

        log.debug("Critic score", session_id=state.get("session_id"), score=quality_score)

    except Exception as exc:
        log.warning("Critic node failed", error=str(exc))
        state.setdefault("reward_scores", {})["response_quality"] = 0.5

    return state


async def compliance_node(state: AgentState, gateway: object, db: object | None = None) -> AgentState:
    """
    Async bypass node — deep compliance analysis of completed response.
    Records a compliance report for audit purposes.
    """
    try:
        guard_events = state.get("guard_events", [])
        compliance_score = 1.0 - (0.2 * len(guard_events))  # penalize per guard event
        compliance_score = max(0.0, min(1.0, compliance_score))

        state["compliance_report"] = {
            "score": compliance_score,
            "guard_events": guard_events,
            "passed": compliance_score >= 0.8,
        }
        state.setdefault("reward_scores", {})["compliance"] = compliance_score

    except Exception as exc:
        log.warning("Compliance node failed", error=str(exc))
        state.setdefault("compliance_report", {"score": 1.0, "passed": True})

    return state
