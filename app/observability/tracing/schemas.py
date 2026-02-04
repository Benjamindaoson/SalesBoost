from pydantic import BaseModel
from typing import Dict, Any

class AgentDecision(BaseModel):
    agent_name: str
    action: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost: float
    parameters: Dict[str, Any] = {}
