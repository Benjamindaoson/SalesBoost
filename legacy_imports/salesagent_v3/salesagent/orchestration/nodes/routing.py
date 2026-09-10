"""Routing Node — determines if a Hot Path (direct response) or Cold Path (Agent reasoning) should be taken."""
from __future__ import annotations

import structlog
from typing import Literal

from salesagent.orchestration.state import AgentState
from salesagent.knowledge.retriever import KnowledgeRetriever

log = structlog.get_logger()

async def router_node(
    state: AgentState,
    db: object,
    gateway: object
) -> Literal["hot", "cold"]:
    """
    Router Node:
    - Calls fast_retrieve to check for high-confidence (score > 0.9) matches.
    - If found, marks state as is_hot_path and returns "hot".
    - Otherwise, returns "cold".
    """
    query = state.get("user_message", "")
    session_id = state.get("session_id", "unknown")

    try:
        retriever = KnowledgeRetriever(db=db, gateway=gateway)
        match = await retriever.fast_retrieve(query)

        if match:
            state["is_hot_path"] = True
            state["hot_path_response"] = match.get("content")
            log.info("Hot Path routing triggered", session_id=session_id, score=match.get("score"))
            return "hot"

        state["is_hot_path"] = False
        state["hot_path_response"] = None

        # ── Value-based Routing (P2 Degradation) ───────────────────────────
        from salesagent.core.settings import settings

        is_vip = session_id in settings.vip_customers or state.get("customer_profile", {}).get("segment") == "VIP"

        # Check urgency signal from memory if available
        urgency = state.get("customer_profile", {}).get("signals", {}).get("urgency", 0.5)

        if settings.tiered_routing_enabled and not is_vip and urgency < settings.degradation_urgency_threshold:
            state["use_lite_path"] = True
            log.info("Intelligent Degradation: Using Lite Path for low-urgency user", session_id=session_id, urgency=urgency)
        else:
            state["use_lite_path"] = False
            log.info("Cold Path routing triggered", session_id=session_id, is_vip=is_vip)

        return "cold"

    except Exception as exc:
        log.warning("Router node failed, falling back to Cold Path", error=str(exc))
        state["is_hot_path"] = False
        return "cold"
