"""
Conversation Management Module

Phase 3B: Sales Personality & Conversation Strategy
"""

from .sales_fsm import (
    SalesState,
    TransitionTrigger,
    StateTransition,
    ConversationContext,
    SalesConversationFSM
)

from .sales_methodology import (
    SPINQuestionType,
    SPINQuestion,
    FABStatement,
    SPINQuestionBank,
    FABTemplateManager,
    PromptManager
)

from .intent_routing import (
    UserIntent,
    IntentAnalysis,
    IntentRouter,
    ActionRouter
)

__all__ = [
    # FSM
    "SalesState",
    "TransitionTrigger",
    "StateTransition",
    "ConversationContext",
    "SalesConversationFSM",
    # Methodology
    "SPINQuestionType",
    "SPINQuestion",
    "FABStatement",
    "SPINQuestionBank",
    "FABTemplateManager",
    "PromptManager",
    # Intent Routing
    "UserIntent",
    "IntentAnalysis",
    "IntentRouter",
    "ActionRouter"
]
