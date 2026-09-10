"""Strategist Agent Node — Generates dynamic plans based on intent analysis."""
from __future__ import annotations

import structlog

from salesagent.core.constants import SaleStage
from salesagent.orchestration.state import AgentState

log = structlog.get_logger()

from salesagent.reasoning.meta_principles import get_applicable_principles

STRATEGY_REFINE_PROMPT = """You are a senior sales strategist expert in Sales Meta-Principles 1.0.
Refine the original strategy plan to strictly adhere to the following activated principles.

META-PRINCIPLES 1.0 (Activated for this turn):
{applicable_principles}

CUSTOMER PERSONA VECTOR:
{persona_vector}

ORIGINAL REASONING PLAN:
{original_plan}

Your Goal:
1. Ensure the "strategy_plan" reflects the core Sales Meta-Principles (Trust, Value Anchor, etc.).
2. Generate "tactical_instructions" that are concrete, Chinese-fluent (native level), and include a Micro-CTA if applicable.
3. If trust is low (<50), ensure NO pushy sales tactics are suggested.

Output JSON with:
{
  "strategy_plan": "refined strategic goal",
  "tactical_instructions": "specific concrete steps for the response generator"
}
"""

async def strategy_node(state: AgentState, gateway: Any) -> AgentState:
    """
    Strategist Agent: Refines the strategy plan using Sales Meta-Principles 1.0.
    """
    reasoning = state.get("reasoning_output")
    if reasoning is None:
        return state

    # 1. Get Customer Persona context
    persona = state.get("customer_profile", {}).get("persona_vector", {})
    if not persona:
        # Fallback to default persona if not found
        persona = {
            "trust_score": 50,
            "urgency": 50,
            "friction_points": [],
            "intent_cluster": "unknown"
        }

    # 2. Filter applicable Meta-Principles using the logic in meta_principles.py
    applicable = get_applicable_principles(persona)
    principles_text = "\n".join([f"- {mp['name']}: {mp['description']}" for mp in applicable])

    # 3. Call Claude 3.5 Sonnet to refine strategy
    try:
        raw_refined = await gateway.complete(
            task="strategy", # Maps to Claude 3.5 Sonnet
            system=STRATEGY_REFINE_PROMPT.format(
                applicable_principles=principles_text,
                persona_vector=json.dumps(persona, ensure_ascii=False),
                original_plan=reasoning.strategy_plan
            ),
            user=f"Refine strategy for session {state.get('session_id')}. User message: {state.get('user_message')}",
            response_format="json"
        )

        refined_data = json.loads(raw_refined)
        state["strategy_plan"] = refined_data.get("strategy_plan", reasoning.strategy_plan)
        state["tactical_instructions"] = refined_data.get("tactical_instructions", reasoning.tactical_instructions)

    except Exception as e:
        log.error("StrategyNode: Failed to refine strategy", error=str(e))
        state["strategy_plan"] = reasoning.strategy_plan
        state["tactical_instructions"] = reasoning.tactical_instructions

    log.info(
        "StrategyNode Trace",
        session_id=state.get("session_id"),
        principles=[mp["id"] for mp in applicable]
    )

    return state

import json
from typing import Any
