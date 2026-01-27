from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMCallContext:
    session_id: str
    turn_number: int
    latency_mode: str = "fast"
    turn_importance: float = 0.5
    risk_level: str = "low"
    budget_remaining: float = 1.0
    retrieval_confidence: Optional[float] = None
    trace_id: Optional[str] = None
    prompt_version: Optional[str] = None
    budget_authorized: bool = False
