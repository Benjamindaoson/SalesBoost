from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class CallType(str, Enum):
    FAST_PATH = "fast_path"
    SLOW_PATH = "slow_path"
    INTERNAL = "internal"

class AgentDecision(BaseModel):
    agent_name: str
    action: str
    reasoning: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    model_used: Optional[str] = None
    routing_reason: Optional[str] = None
    downgrade_reason: Optional[str] = None
    budget_remaining: Optional[float] = None
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    prompt_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SecurityEvent(BaseModel):
    event_type: str  # input_injection, output_forbidden, compliance_risk
    action_taken: str # block, rewrite, warn, pass
    rule_id: str
    trigger_point: Optional[str] = None  # pre_generate / post_generate / pre_model_call
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class KnowledgeEvidence(BaseModel):
    evidence_id: str
    source: str
    content_snippet: str
    confidence: float
    is_cited: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ContextLayerInfo(BaseModel):
    name: str
    tokens: int
    truncated: bool = False
    source: Optional[str] = None # e.g., "db", "vector_store", "memory"
    truncation_reason: Optional[str] = None

class ContextManifest(BaseModel):
    layers: List[ContextLayerInfo]
    total_tokens: int
    budget_limit: int
    compression_ratio: float
    manifest_summary: str = "" # A human-readable summary

class TurnTrace(BaseModel):
    trace_id: str
    session_id: str
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Execution Path
    path_taken: CallType
    ttfs_ms: float = 0.0
    ttfs_stop_point: Optional[str] = None  # npc_returned / blocked_before_generate
    total_latency_ms: float = 0.0
    linked_slow_trace_id: Optional[str] = None
    slow_total_ms: Optional[float] = None
    
    # Decisions & Agents
    decisions: List[AgentDecision] = Field(default_factory=list)
    
    # Security & Compliance
    security_events: List[SecurityEvent] = Field(default_factory=list)
    
    # Context
    context_manifest: Optional[ContextManifest] = None
    
    # Knowledge
    evidences: List[KnowledgeEvidence] = Field(default_factory=list)
    
    # Final Outcome
    status: str = "success" # success, partial_failure, blocked, error
    error_detail: Optional[str] = None

class GlobalMetrics(BaseModel):
    total_turns: int = 0
    avg_ttfs_ms: float = 0.0
    total_cost: float = 0.0
    security_incidents: int = 0
    fallback_rate: float = 0.0
