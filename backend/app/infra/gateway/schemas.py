from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

class AgentType(str, Enum):
    INTENT_GATE = "intent_gate"
    NPC = "npc"
    NPC_GENERATOR = "npc_generator"
    COACH = "coach"
    COACH_GENERATOR = "coach_generator"
    EVALUATOR = "evaluator"
    RAG = "rag"
    RETRIEVER = "retriever"
    COMPLIANCE = "compliance"
    SESSION_DIRECTOR = "session_director"
    ADOPTION_TRACKER = "adoption_tracker"
    STRATEGY = "strategy"
    SDR = "sdr"  # AI Sales Development Representative (Autonomous)

class LatencyMode(str, Enum):
    FAST = "fast"
    SLOW = "slow"

@dataclass
class RoutingContext:
    agent_type: AgentType
    turn_importance: float
    risk_level: str
    budget_remaining: float
    latency_mode: LatencyMode
    retrieval_confidence: Optional[float]
    turn_number: int
    session_id: str
    budget_authorized: bool

@dataclass
class ModelConfig:
    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000

@dataclass
class ModelCall:
    prompt: str
    system_prompt: Optional[str] = None
    config: Optional[ModelConfig] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_mode: Optional[str] = None  # "prompt" | "function_calling" | "auto"
    tool_choice: Optional[Any] = None
