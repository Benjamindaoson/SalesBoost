"""
Standard Coordinator State Definition

This module defines the canonical state structure used across all coordinators.
This ensures consistency and type safety across the orchestration layer.

Design Principles:
1. All coordinators MUST use this standard state
2. All fields are required (use Optional[] for nullable fields)
3. State is append-only (use Annotated[list, add] for accumulation)
4. State schema version is tracked for migrations
"""

from typing import TypedDict, Optional, Annotated, Sequence, Dict, Any, List
from operator import add


class CoordinatorState(TypedDict, total=False):
    """
    Standard state definition for all coordinators

    This TypedDict defines the canonical state structure used in LangGraph workflows.
    All coordinators (Production, Dynamic, LangGraph, etc.) must use this schema.

    Fields:
    -------
    # Input (required for execution)
    user_message: str
        The user's input message for this turn

    session_id: str
        Unique session identifier

    turn_number: int
        Current turn number (1-indexed)

    # Context (conversation state)
    history: Sequence[dict]
        Conversation history [{"role": "user/assistant", "content": "..."}]

    fsm_state: dict
        FSM state snapshot {"current_stage": "discovery", "turn_count": 5, "npc_mood": 0.7}

    persona: dict
        Customer persona configuration {"name": "张总", "occupation": "企业主", ...}

    # Intent Classification Result
    intent: str
        Classified intent (e.g., "price_inquiry", "objection_price")

    confidence: float
        Intent classification confidence (0.0 - 1.0)

    stage_suggestion: str
        Suggested FSM stage transition (optional)

    # NPC Response
    npc_response: str
        Generated NPC response text

    npc_mood: float
        NPC mood after this turn (0.0 - 1.0)

    # Coach Advice
    coach_advice: str
        Sales coaching advice (may be empty if async mode)

    advice_source: str
        Source of advice: "ai" | "fallback" | "error_fallback"

    # Tool Execution
    tool_calls: list
        List of tool calls to execute [{"tool": "knowledge_retriever", "args": {...}}]

    tool_results: list
        Tool execution results [{"tool": "...", "ok": true, "output": {...}}]

    tool_outputs: list
        Canonical tool outputs [{"tool": "...", "ok": true, "result": {...}}]

    # Compliance & Audit
    compliance_result: dict
        Compliance check result {"is_compliant": true, "risk_flags": []}

    risk_score: float
        Compliance risk score (0.0 - 1.0)

    # Tracing & Observability
    trace_log: Annotated[list, add]
        Execution trace (append-only) [{"node": "...", "status": "ok", "source": "policy", "latency_ms": 12.3, "detail": {...}}, ...]

    # Metadata
    state_version: str
        State schema version (for migrations)

    execution_mode: str
        Execution mode: "sync" | "async_coach" | "human_in_loop"

    # Error Handling
    error: Optional[str]
        Error message if execution failed

    error_node: Optional[str]
        Node where error occurred
    """

    # Required fields (inputs)
    user_message: str
    session_id: str
    turn_number: int

    # Context
    history: Sequence[dict]
    fsm_state: dict
    persona: dict

    # Intent
    intent: str
    confidence: float
    stage_suggestion: str

    # NPC
    npc_response: str
    npc_mood: float

    # Coach
    coach_advice: str
    advice_source: str  # NEW: Track advice source (ai/fallback/error_fallback)

    # Tools
    tool_calls: list
    tool_results: list
    tool_outputs: list

    # Reasoning & Routing
    reasoning: dict
    reasoning_source: str
    routing_recommendation: dict
    routing_source: str
    routing_decision: dict
    route_choice: str
    recent_tool_calls: bool
    bandit_decision: dict

    # Compliance
    compliance_result: dict
    risk_score: float

    # Tracing (append-only)
    trace_log: Annotated[list, add]

    # Metadata
    state_version: str
    execution_mode: str

    # Error handling
    error: Optional[str]
    error_node: Optional[str]


# State Schema Version (for migrations)
CURRENT_STATE_VERSION = "2.0.0"

# Execution Modes
class ExecutionMode:
    """Standard execution modes"""
    SYNC = "sync"  # Synchronous (wait for all nodes)
    ASYNC_COACH = "async_coach"  # TTFT optimization (skip coach)
    HUMAN_IN_LOOP = "human_in_loop"  # Admin review enabled


# Default values for optional fields
def create_initial_state(
    user_message: str,
    session_id: str,
    turn_number: int,
    history: List[dict] = None,
    fsm_state: dict = None,
    persona: dict = None,
    execution_mode: str = ExecutionMode.ASYNC_COACH
) -> CoordinatorState:
    """
    Create initial state with default values

    Args:
        user_message: User input
        session_id: Session ID
        turn_number: Turn number
        history: Conversation history (default: empty)
        fsm_state: FSM state (default: empty)
        persona: Persona config (default: empty)
        execution_mode: Execution mode (default: ASYNC_COACH)

    Returns:
        CoordinatorState with default values
    """
    return CoordinatorState(
        # Inputs
        user_message=user_message,
        session_id=session_id,
        turn_number=turn_number,

        # Context
        history=history or [],
        fsm_state=fsm_state or {},
        persona=persona or {},

        # Intent (will be populated)
        intent="",
        confidence=0.0,
        stage_suggestion="",

        # NPC (will be populated)
        npc_response="",
        npc_mood=0.5,

        # Coach (will be populated)
        coach_advice="",
        advice_source="",

        # Tools (will be populated)
        tool_calls=[],
        tool_results=[],
        tool_outputs=[],

        # Reasoning & Routing (will be populated)
        reasoning={},
        reasoning_source="",
        routing_recommendation={},
        routing_source="",
        routing_decision={},
        route_choice="",
        recent_tool_calls=False,
        bandit_decision={},

        # Compliance (will be populated)
        compliance_result={},
        risk_score=0.0,

        # Tracing
        trace_log=[],

        # Metadata
        state_version=CURRENT_STATE_VERSION,
        execution_mode=execution_mode,

        # Error
        error=None,
        error_node=None
    )


def validate_state(state: CoordinatorState) -> bool:
    """
    Validate state structure

    Args:
        state: State to validate

    Returns:
        True if valid, raises ValueError otherwise
    """
    required_fields = ["user_message", "session_id", "turn_number"]

    for field in required_fields:
        if field not in state:
            raise ValueError(f"Missing required field: {field}")

    # Validate state version
    if state.get("state_version") != CURRENT_STATE_VERSION:
        raise ValueError(
            f"State version mismatch: expected {CURRENT_STATE_VERSION}, "
            f"got {state.get('state_version')}"
        )

    return True
