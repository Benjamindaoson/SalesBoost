"""AgentState TypedDict — shared state for all LangGraph nodes."""
from __future__ import annotations

from typing import Any, TypedDict

from salesagent.core.constants import SaleStage
from salesagent.reasoning.schemas import ReasoningOutput


class AgentState(TypedDict, total=False):
    """
    Shared state passed through the LangGraph DAG.
    All nodes read from and write to this dict.
    """

    # ── Session context ────────────────────────────────────────────────────
    session_id: str
    turn_index: int
    fsm_stage: SaleStage

    # Hot Path Routing
    is_hot_path: bool
    use_lite_path: bool
    hot_path_response: str | None

    # HITL (V3.1)
    requires_approval: bool
    human_override: str | None

    # DSP & Tactical Engine 2.0
    strategy_plan: str | None           # Dynamically generated intent-based strategy
    few_shot_context: list[str]          # Retrieved gold-standard turns
    intent_radar: dict[str, float]      # {trust, urgency, friction}

    # ── Input ─────────────────────────────────────────────────────────────
    messages: list[dict[str, str]]       # full conversation history
    user_message: str                     # latest user message
    customer_profile: dict[str, Any]     # from Adaptive Memory

    # ── Reasoning output ─────────────────────────────────────────────────
    reasoning_output: ReasoningOutput | None

    # ── Retrieval output ─────────────────────────────────────────────────
    retrieved_docs: list[dict[str, Any]]  # chunks with content + score

    # ── Response generation ──────────────────────────────────────────────
    response_text: str                    # final assembled response
    response_stream_done: bool

    # ── Guard ─────────────────────────────────────────────────────────────
    guard_events: list[dict[str, Any]]   # list of interceptions this turn
    guard_active: bool

    # ── Critic / Reward ───────────────────────────────────────────────────
    reward_scores: dict[str, float]      # 5-dim reward scores
    critic_rationale: str

    # ── Compliance ────────────────────────────────────────────────────────
    compliance_report: dict[str, Any]

    # ── Simulation & MCTS-lite ────────────────────────────────────────────
    candidate_responses: list[dict[str, Any]]  # [{tactic: str, score: float, rationale: str}]
    simulation_history: list[dict[str, Any]]
    winning_candidate: dict[str, Any] | None

    # ── Output for SSE ───────────────────────────────────────────────────
    sse_events: list[dict[str, Any]]     # events to flush to SSE stream
    error: str | None
