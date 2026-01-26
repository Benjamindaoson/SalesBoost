"""
Model gateway schemas.
"""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENAI = "openai"
    QWEN = "qwen"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"
    MOCK = "mock"


class AgentType(str, Enum):
    INTENT_GATE = "intent_gate"
    RAG = "rag"
    COMPLIANCE = "compliance"
    NPC = "npc"
    COACH = "coach"
    SESSION_DIRECTOR = "session_director"
    RETRIEVER = "retriever"
    NPC_GENERATOR = "npc_generator"
    COACH_GENERATOR = "coach_generator"
    EVALUATOR = "evaluator"
    ADOPTION_TRACKER = "adoption_tracker"
    STRATEGY = "strategy"
    GUARD = "guard"


class LatencyMode(str, Enum):
    FAST = "fast"
    SLOW = "slow"


class RoutingContext(BaseModel):
    agent_type: AgentType
    turn_importance: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(default="low")
    budget_remaining: float = Field(..., ge=0.0)
    latency_mode: LatencyMode
    retrieval_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    turn_number: int = Field(..., ge=1)
    session_id: str
    budget_authorized: bool = False


class ModelCall(BaseModel):
    call_id: str
    agent_type: AgentType
    provider: ProviderType
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: str


class BudgetConfig(BaseModel):
    per_turn_budget: float = Field(default=0.05)
    per_session_budget: float = Field(default=1.0)
    fast_path_budget: float = Field(default=0.02)
    slow_path_budget: float = Field(default=0.03)


class ModelConfig(BaseModel):
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: float = 30.0


class RoutingDecision(BaseModel):
    provider: ProviderType
    model: str
    reason: str
    estimated_cost: float
    estimated_latency_ms: float
    fallback_provider: Optional[ProviderType] = None
    fallback_model: Optional[str] = None
