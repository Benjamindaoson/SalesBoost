"""
Runtime Models - Compatibility layer

This module provides backward compatibility for code that imports from runtime_models.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# Import actual models
from .session import Session, SessionStatus
from .message import Message
from .evaluation import Evaluation

# Aliases for backward compatibility
SessionState = SessionStatus
EvaluationLog = Evaluation

class RuntimeConfig(BaseModel):
    """Runtime configuration model"""
    id: Optional[str] = None
    config_type: str = "default"
    settings: Dict[str, Any] = {}

class WorkflowState(BaseModel):
    """Workflow state model"""
    id: Optional[str] = None
    state_type: str = "default"
    data: Dict[str, Any] = {}

class AgentContext(BaseModel):
    """Agent context model"""
    id: Optional[str] = None
    context_type: str = "default"
    metadata: Dict[str, Any] = {}

__all__ = [
    "RuntimeConfig", "WorkflowState", "AgentContext",
    "Session", "SessionStatus", "SessionState",
    "Message", "Evaluation", "EvaluationLog"
]
