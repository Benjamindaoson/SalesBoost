from __future__ import annotations

from enum import Enum


class SaleStage(str, Enum):
    """Sales funnel macro-stages managed by the deterministic FSM."""
    ICEBREAK = "ICEBREAK"
    DISCOVERY = "DISCOVERY"
    PROPOSAL = "PROPOSAL"
    CLOSING = "CLOSING"


class StageSignal(str, Enum):
    """Structured signals emitted by the Reasoning Chain to drive FSM transitions."""
    # ICEBREAK → DISCOVERY
    RAPPORT_ESTABLISHED = "rapport_established"
    # DISCOVERY → PROPOSAL
    NEEDS_IDENTIFIED = "needs_identified"
    # PROPOSAL → OBJECTION
    OBJECTION_RAISED = "objection_raised"
    # PROPOSAL → CLOSE
    HIGH_INTENT_DETECTED = "high_intent_detected"
    # OBJECTION → PROPOSAL
    OBJECTION_RESOLVED = "objection_resolved"
    # OBJECTION → CLOSE
    OBJECTION_OVERCOME = "objection_overcome"
    # Any stage → DISCOVERY (backtrack)
    NEW_NEED_SURFACED = "new_need_surfaced"
    # → FOLLOWUP
    SESSION_ENDED = "session_ended"
    DEAL_CLOSED = "deal_closed"
    # Stay in current stage
    STAY = "stay"


class GuardRiskType(str, Enum):
    """Risk categories detected by the Streaming Guard."""
    FALSE_PROMISE = "false_promise"
    PRICE_LEAK = "price_leak"
    COMPETITOR_DEFAMATION = "competitor_defamation"
    SENSITIVE_INFO = "sensitive_info"
    UNAUTHORIZED_COMMITMENT = "unauthorized_commitment"


class RewardDimension(str, Enum):
    TASK_PROGRESS = "task_progress"
    RESPONSE_QUALITY = "response_quality"
    COMPLIANCE = "compliance"
    USER_ENGAGEMENT = "user_engagement"
    CONVERSION_SIGNAL = "conversion_signal"


# Reward dimension weights (must sum to 1.0)
REWARD_WEIGHTS: dict[str, float] = {
    RewardDimension.TASK_PROGRESS: 0.25,
    RewardDimension.RESPONSE_QUALITY: 0.20,
    RewardDimension.COMPLIANCE: 0.15,
    RewardDimension.USER_ENGAGEMENT: 0.15,
    RewardDimension.CONVERSION_SIGNAL: 0.25,
}

# Memory half-life by entity type (seconds)
MEMORY_HALF_LIFE: dict[str, float] = {
    "name": float("inf"),
    "company": float("inf"),
    "budget": 7 * 24 * 3600,       # 7 days
    "timeline": 3 * 24 * 3600,     # 3 days
    "pain_point": 14 * 24 * 3600,  # 14 days
    "preference": 30 * 24 * 3600,  # 30 days
    "emotion": 1 * 24 * 3600,      # 1 day
    "default": 7 * 24 * 3600,      # 7 days
}

# Tactic taxonomy
TACTICS = [
    "value_reframe",
    "social_proof",
    "scarcity_urgency",
    "consultative_questioning",
    "empathy_acknowledgment",
    "feature_benefit_bridge",
    "roi_calculation",
    "competitive_differentiation",
    "trial_close",
    "future_pacing",
]

# Redis Streams keys
REDIS_STREAM_FSM_EVENTS = "stream:fsm_events"
REDIS_STREAM_GUARD_EVENTS = "stream:guard_events"
REDIS_STREAM_FLYWHEEL = "stream:flywheel"

# Prompt template names
PROMPT_REASONING = "reasoning_chain"
PROMPT_RESPONSE_BASE = "response_base"
PROMPT_GUARD_REWRITE = "guard_rewrite"
PROMPT_CRITIC = "critic_scoring"
PROMPT_SELFRAG = "selfrag_filter"
PROMPT_SYNTHETIC_DIALOGUE = "synthetic_dialogue"
PROMPT_APO_VARIANT = "apo_variant_generator"
PROMPT_EVOLUTION_REVIEW = "evolution_strategy_review"
