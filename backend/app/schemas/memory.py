from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryScope(str, Enum):
    GLOBAL = "GLOBAL"
    ORG = "ORG"
    USER = "USER"
    SCENARIO = "SCENARIO"
    KB = "KB"


class MemoryType(str, Enum):
    SEMANTIC = "SEMANTIC"
    REFLECTIVE = "REFLECTIVE"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SHADOW = "SHADOW"
    DEPRECATED = "DEPRECATED"
    DELETED = "DELETED"


class MemorySnippet(BaseModel):
    memory_id: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    scope: MemoryScope
    scope_id: Optional[str] = None
    source_episode_id: Optional[str] = None


class ReflectiveAction(BaseModel):
    rule_id: str
    trigger: Dict[str, Any]
    action: Dict[str, Any]
    priority: int
    scope: MemoryScope
    scope_id: Optional[str] = None
    explain: Optional[str] = None


class MemoryContext(BaseModel):
    semantic_snippets: List[MemorySnippet] = Field(default_factory=list)
    reflective_actions: List[ReflectiveAction] = Field(default_factory=list)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)


class TurnState(BaseModel):
    tenant_id: Optional[str] = None
    user_id: str
    session_id: str
    turn_id: int
    scenario_id: Optional[str] = None
    persona_id: Optional[str] = None
    stage: Optional[str] = None
    user_message: str
    npc_reply: Optional[str] = None
    trace_id: Optional[str] = None


class MemoryCandidate(BaseModel):
    memory_type: MemoryType
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    scope: MemoryScope = MemoryScope.GLOBAL
    scope_id: Optional[str] = None
    source_episode_id: Optional[str] = None
    created_by: str = "agent"
    status: MemoryStatus = MemoryStatus.SHADOW
    reflective_trigger: Optional[Dict[str, Any]] = None
    reflective_action: Optional[Dict[str, Any]] = None
    explain: Optional[str] = None
