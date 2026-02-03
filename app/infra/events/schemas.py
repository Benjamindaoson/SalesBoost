from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class EventType(str, Enum):
    # Session Events
    SESSION_STARTED = "session.started"
    SESSION_RESUMED = "session.resumed"
    SESSION_SUSPENDED = "session.suspended"
    SESSION_COMPLETED = "session.completed"
    SESSION_TIMEOUT = "session.timeout"
    
    # Workflow Events
    STAGE_TRANSITION = "workflow.stage_transition"
    AGENT_SWITCH = "workflow.agent_switch"
    TURN_COMPLETED = "workflow.turn_completed"
    
    # Audit & Security Events
    SENSITIVE_CONTENT_BLOCKED = "audit.sensitive_content_blocked"
    BUDGET_EXCEEDED = "audit.budget_exceeded"
    COMPLIANCE_VIOLATION = "audit.compliance_violation"
    ACCESS_LOGGED = "audit.access_logged"
    MODEL_LIFECYCLE_DECISION = "audit.model_lifecycle_decision"
    INTENT_CLASSIFICATION = "audit.intent_classification"

    # Knowledge & Search Events
    KNOWLEDGE_UPDATED = "knowledge.updated"

    # Memory Events
    MEMORY_EVENT_RECORDED = "memory.event_recorded"
    MEMORY_OUTCOME_RECORDED = "memory.outcome_recorded"
    
    # Logic & Evaluation Events
    EVALUATION_COMPLETED = "evaluation.completed"
    RETRY_EVALUATION = "evaluation.retry"

    # Traffic & Degradation Events
    REQUEST_DEGRADED = "traffic.request_degraded"

class EventBase(BaseModel):
    event_id: str = Field(..., description="Unique identifier for the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

class SessionEventPayload(EventBase):
    action: str
    metadata: Dict[str, Any] = {}

class WorkflowEventPayload(EventBase):
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    agent_type: Optional[str] = None
    context_snapshot: Dict[str, Any] = {}

class AuditEventPayload(EventBase):
    reason: str
    severity: str = "medium"
    blocked_content: Optional[str] = None
    risk_score: float = 0.0
    details: Dict[str, Any] = {}

class KnowledgeEventPayload(EventBase):
    document_id: str
    content_hash: str
    operation: str = "upsert" # upsert, delete
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}

class EvaluationEventPayload(EventBase):
    evaluation_id: str
    target_content: str
    score: float
    comments: str
    retry_count: int = 0
    correction_prompt: Optional[str] = None


class MemoryOutcomeEventPayload(EventBase):
    outcome_id: str
    event_id: str
    adopted: bool
    adopt_type: Optional[str] = None
    stage_before: Optional[str] = None
    stage_after: Optional[str] = None
    compliance_result: Optional[str] = None
    final_result: Optional[str] = None
    strategy_ids: List[str] = []
    request_id: Optional[str] = None

class MemoryEventPayload(EventBase):
    event_id: str
    tenant_id: str
    user_id: str
    session_id: str
    channel: Optional[str] = None
    turn_index: Optional[int] = None
    speaker: str
    raw_text_ref: Optional[str] = None
    summary: Optional[str] = None
    intent_top1: Optional[str] = None
    intent_topk: List[str] = []
    stage: Optional[str] = None
    objection_type: Optional[str] = None
    entities: List[str] = []
    sentiment: Optional[str] = None
    tension: Optional[float] = None
    compliance_flags: List[str] = []
    coach_suggestions_shown: List[str] = []
    coach_suggestions_taken: List[str] = []
    metadata: Dict[str, Any] = {}

class EventEnvelope(BaseModel):
    type: EventType
    payload: Any
