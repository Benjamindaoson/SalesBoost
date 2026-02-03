from enum import Enum
from pydantic import BaseModel
from typing import Optional

class SalesStage(str, Enum):
    """
    Standard Sales Stages
    """
    OPENING = "opening"
    DISCOVERY = "discovery"
    SOLUTION = "solution"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    FOLLOW_UP = "follow_up"
    NEEDS_DISCOVERY = "needs_discovery"

class FSMState(BaseModel):
    current_stage: SalesStage
    turn_count: int = 0
    npc_mood: float = 0.5
    context_snapshot: Optional[dict] = None
