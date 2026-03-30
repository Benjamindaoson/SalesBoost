from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SpeakerType(str, Enum):
    SALES = "sales"
    CUSTOMER = "customer"
    NPC = "npc"
    AGENT = "agent"


class RouteDecision(str, Enum):
    COMPLIANCE = "compliance"
    KNOWLEDGE = "knowledge"
    STRATEGY = "strategy"
    FALLBACK = "fallback"


class AdoptType(str, Enum):
    SCRIPT = "script"
    ACTION_LIST = "action_list"


class ComplianceAction(str, Enum):
    REWRITE = "rewrite"
    PASS = "pass"


class ComplianceStatus(str, Enum):
    OK = "ok"
    BLOCKED = "blocked"


class MemoryResponse(BaseModel):
    request_id: str
    status: str = "ok"
    error: Optional[str] = None


class EventWriteRequest(BaseModel):
    event_id: str
    tenant_id: str
    user_id: str
    session_id: str
    channel: Optional[str] = None
    turn_index: Optional[int] = None
    speaker: SpeakerType
    raw_text_ref: Optional[str] = None
    summary: Optional[str] = None
    intent_top1: Optional[str] = None
    intent_topk: List[str] = Field(default_factory=list)
    stage: Optional[str] = None
    objection_type: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    tension: Optional[float] = None
    compliance_flags: List[str] = Field(default_factory=list)
    coach_suggestions_shown: List[str] = Field(default_factory=list)
    coach_suggestions_taken: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventWriteData(BaseModel):
    event_id: str
    stored: List[str] = Field(default_factory=list)


class EventWriteResponse(MemoryResponse):
    data: EventWriteData


class OutcomeWriteRequest(BaseModel):
    session_id: str
    event_id: str
    adopted: bool
    adopt_type: Optional[AdoptType] = None
    stage_before: Optional[str] = None
    stage_after: Optional[str] = None
    eval_scores: Dict[str, Any] = Field(default_factory=dict)
    compliance_result: Optional[str] = None
    final_result: Optional[str] = None


class OutcomeWriteData(BaseModel):
    outcome_id: str
    adopted: bool


class OutcomeWriteResponse(MemoryResponse):
    data: OutcomeWriteData


class PersonaWriteRequest(BaseModel):
    user_id: str
    level: Optional[str] = None
    weakness_tags: List[str] = Field(default_factory=list)
    last_eval_summary: Optional[str] = None
    last_improvements: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    history_stats: Dict[str, Any] = Field(default_factory=dict)


class PersonaWriteData(BaseModel):
    user_id: str
    updated: bool


class PersonaWriteResponse(MemoryResponse):
    data: PersonaWriteData


class KnowledgeWriteRequest(BaseModel):
    knowledge_id: str
    domain: str
    product_id: Optional[str] = None
    structured_content: Dict[str, Any]
    source_ref: Optional[str] = None
    version: str
    effective_from: str
    effective_to: Optional[str] = None
    is_enabled: bool = True
    citation_snippets: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeWriteData(BaseModel):
    knowledge_id: str
    version: str


class KnowledgeWriteResponse(MemoryResponse):
    data: KnowledgeWriteData


class StrategyTriggerCondition(BaseModel):
    intent: Optional[str] = None
    stage: Optional[str] = None
    objection_type: Optional[str] = None
    level: Optional[str] = None
    channel: Optional[str] = None


class StrategyWriteRequest(BaseModel):
    strategy_id: str
    type: str
    trigger_condition: StrategyTriggerCondition
    steps: List[str] = Field(default_factory=list)
    scripts: List[str] = Field(default_factory=list)
    dos_donts: Dict[str, Any] = Field(default_factory=dict)
    evidence_event_ids: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class StrategyWriteData(BaseModel):
    strategy_id: str


class StrategyWriteResponse(MemoryResponse):
    data: StrategyWriteData


class Citation(BaseModel):
    type: str
    id: str
    version: Optional[str] = None
    snippet: Optional[str] = None
    source_ref: Optional[str] = None
    rule_id: Optional[str] = None


class MemoryQueryRequest(BaseModel):
    query: str
    tenant_id: str
    user_id: str
    session_id: str
    intent_hint: Optional[str] = None
    stage: Optional[str] = None
    objection_type: Optional[str] = None
    top_k: int = 5
    require_citations: bool = True
    route_policy: str = "compliance>knowledge>strategy>fallback"


class MemoryQueryHit(BaseModel):
    type: str
    id: str
    score: float
    content: Dict[str, Any]


class MemoryQueryData(BaseModel):
    route_decision: RouteDecision
    hits: List[MemoryQueryHit] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


class MemoryQueryResponse(MemoryResponse):
    data: MemoryQueryData


class ComplianceCheckRequest(BaseModel):
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    candidate_response: str
    citations: List[Citation] = Field(default_factory=list)


class ComplianceHit(BaseModel):
    rule_id: str
    reason: str


class ComplianceCheckData(BaseModel):
    action: ComplianceAction
    hits: List[ComplianceHit] = Field(default_factory=list)
    safe_response: Optional[str] = None


class ComplianceCheckResponse(MemoryResponse):
    status: ComplianceStatus = ComplianceStatus.OK
    data: ComplianceCheckData


class AuditTraceRequest(BaseModel):
    request_id: str


class AuditTraceData(BaseModel):
    input_digest: Optional[str] = None
    route: Optional[str] = None
    retrieved_ids: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    compliance_hits: List[str] = Field(default_factory=list)
    output_digest: Optional[str] = None


class AuditTraceResponse(MemoryResponse):
    data: AuditTraceData
