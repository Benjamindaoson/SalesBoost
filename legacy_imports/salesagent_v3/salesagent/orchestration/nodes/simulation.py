"""Simulation Node — MCTS-lite response evaluation and selection."""
from __future__ import annotations

import structlog
import json
from typing import Any
from salesagent.orchestration.state import AgentState
from salesagent.core.settings import settings

log = structlog.get_logger()

CANDIDATE_GEN_PROMPT = """You are a sales tactician. Based on the strategy plan and customer persona, generate 3 distinct tactical instructions (Best-of-3) for the response generator.

STRATEGY PLAN: {strategy_plan}
CUSTOMER PERSONA: {persona_vector}

Generate 3 candidates:
1. Empathy: Focus on rapport and emotional resonance.
2. Professional: Focus on expertise and technical value.
3. Push: Focus on urgency and prescriptive guidance.

Output JSON:
{{
  "candidates": [
    {{"type": "empathy", "tactic": "..."}},
    {{"type": "professional", "tactic": "..."}},
    {{"type": "push", "tactic": "..."}}
  ]
}}
"""

SIMULATION_CRITIC_PROMPT = """You are simulating the customer persona below. Evaluate 3 potential sales tactics and predict your response to each.

CUSTOMER PERSONA: {persona_vector}

TACTICS:
{tactics}

For each tactic, provide:
1. Predicted Customer Response: How you would feel/respond.
2. Win Rate (0.0-1.0): Probability this moves you to the next action/stage.
3. Rationale: Why you feel this way.

Output JSON:
{{
  "evaluations": [
    {{"type": "...", "win_rate": 0.0, "rationale": "..."}},
    ...
  ]
}}
"""

async def simulation_node(state: AgentState, gateway: Any) -> AgentState:
    """
    Simulation Node (MCTS-lite):
    1. Generates 3 candidate tactics (Empathy, Professional, Push).
    2. Simulates potential outcomes with a Critic agent.
    3. Selects the winning tactic based on predicted win rate.
    """
    session_id = state.get("session_id", "unknown")
    strategy_plan = state.get("strategy_plan", "")
    persona = state.get("customer_profile", {}).get("persona_vector", {})

    # 1. Generate 3 Candidates
    try:
        raw_candidates = await gateway.complete(
            task="simulation",
            system=CANDIDATE_GEN_PROMPT.format(
                strategy_plan=strategy_plan,
                persona_vector=json.dumps(persona, ensure_ascii=False)
            ),
            user="Generate 3 tactical candidates",
            response_format="json"
        )
        candidates_data = json.loads(raw_candidates)
        candidates = candidates_data.get("candidates", [])

        # 2. Simulate & Review with Critic
        tactics_text = "\n".join([f"- {c['type'].upper()}: {c['tactic']}" for c in candidates])
        raw_evals = await gateway.complete(
            task="critic",
            system=SIMULATION_CRITIC_PROMPT.format(
                persona_vector=json.dumps(persona, ensure_ascii=False),
                tactics=tactics_text
            ),
            user="Evaluate these tactics",
            response_format="json"
        )
        evaluations_data = json.loads(raw_evals)
        evaluations = evaluations_data.get("evaluations", [])

        # 3. Winning Strategy Selection
        score_map = {e["type"]: e["win_rate"] for e in evaluations}
        winning_type = max(score_map, key=score_map.get) if score_map else "professional"

        winner = next((c for c in candidates if c["type"] == winning_type), candidates[0] if candidates else {"tactic": "Error: no candidates"})

        state["winning_candidate"] = {
            "type": winning_type,
            "tactic": winner.get("tactic"),
            "score": score_map.get(winning_type, 0.0),
            "rationale": next((e.get("rationale") for e in evaluations if e["type"] == winning_type), "No rationale provided")
        }

        # Update tactical instructions for the response node
        state["tactical_instructions"] = winner.get("tactic")
        state["candidate_responses"] = evaluations # Store for tracing

        log.info(
            "MCTS-lite simulation completed",
            session_id=session_id,
            winner=winning_type,
            score=score_map.get(winning_type)
        )

    except Exception as e:
        log.error("Simulation failed, falling back to original instructions", error=str(e))
        # Fallback: preserve original tactical_instructions from reasoning node if refined one failed
        if "tactical_instructions" not in state or not state["tactical_instructions"]:
            reasoning = state.get("reasoning_output")
            if reasoning:
                state["tactical_instructions"] = reasoning.tactical_instructions

    return state
