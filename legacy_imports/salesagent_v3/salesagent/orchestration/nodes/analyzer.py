"""Analyzer Node — performs multi-dimensional vector modeling of the customer persona."""
from __future__ import annotations

import json
import structlog
from pydantic import ValidationError

from salesagent.orchestration.state import AgentState
from salesagent.reasoning.schemas import CustomerPersonaVector
from salesagent.core.settings import settings

log = structlog.get_logger()

ANALYZER_SYSTEM_PROMPT = """You are a senior sales psychologist. Your task is to analyze the conversation and model the customer's state into a structured persona vector.

DIMENSIONS:
1. trust_score (0-100): How much does the customer trust the agent? Consider rapport, intimacy, and response speed.
2. urgency (0-100): How much is the customer in a hurry to solve their problem?
3. friction_points: Extract specific resistance points (e.g., pricing, technical doubts, decision authority).
4. intent_cluster: A brief label for the customer's current semantic and psychological position (e.g., "skeptical_researcher", "ready_to_buy", "frustrated_user").

Output MUST be a valid JSON object matching the CustomerPersonaVector schema.
"""

async def analyzer_node(state: AgentState, gateway: object) -> AgentState:
    """
    Analyzer Node: Uses GPT-4o-mini to model customer persona based on context.
    """
    session_id = state.get("session_id", "unknown")

    # ── Prepare context ───────────────────────────────────────────────────
    messages = state.get("messages", [])
    history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages[-10:]])
    user_message = state.get("user_message", "")

    prompt_user = f"Context History:\n{history_text}\n\nLatest User Message: {user_message}"

    # ── Call Gateway ──────────────────────────────────────────────────────
    try:
        if settings.mock_llm:
            # Provide a realistic mock for the analyzer
            raw_output = json.dumps({
                "trust_score": 65,
                "urgency": 40,
                "friction_points": ["price_sensitivity"],
                "intent_cluster": "informed_evaluator"
            })
        else:
            raw_output = await gateway.complete( # type: ignore[attr-defined]
                task="analyzer",
                system=ANALYZER_SYSTEM_PROMPT,
                user=prompt_user,
                session_id=session_id,
                response_format="json"
            )

        # ── Parse and Validate ──────────────────────────────────────────────
        data = json.loads(raw_output)
        vector = CustomerPersonaVector(**data)

        # ── Update State ──────────────────────────────────────────────────
        # We can store it in customer_profile or as a new first-class field
        # The PRD/User request suggests it's a "dimension modeling"
        # We'll put it in customer_profile for now, consistent with Adaptive Memory
        if "customer_profile" not in state or state["customer_profile"] is None:
            state["customer_profile"] = {}

        state["customer_profile"]["persona_vector"] = vector.model_dump()

        # Also sync to intent_radar if needed by downstream nodes
        state["intent_radar"] = {
            "trust": vector.trust_score / 100.0,
            "urgency": vector.urgency / 100.0,
            "friction": 1.0 if vector.friction_points else 0.0 # simplified mapping
        }

        log.info(
            "Customer persona analyzed",
            session_id=session_id,
            trust=vector.trust_score,
            urgency=vector.urgency,
            intent=vector.intent_cluster
        )

    except (json.JSONDecodeError, ValidationError) as e:
        log.error("Failed to parse analyzer output", error=str(e), session_id=session_id)
        # Fallback to default if failed
        if "customer_profile" not in state or state["customer_profile"] is None:
            state["customer_profile"] = {}
        state["customer_profile"]["persona_vector"] = {
            "trust_score": 50,
            "urgency": 50,
            "friction_points": [],
            "intent_cluster": "unknown"
        }

    return state
