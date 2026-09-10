"""Pydantic v2 Request/Response schemas for all API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)
    customer_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatStreamEvent(BaseModel):
    event: str  # "token" | "reasoning" | "guard" | "fsm_change" | "reward" | "done" | "error"
    data: dict[str, Any]


# ── Sessions ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    customer_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    status: str | None = None
    metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    id: str
    customer_id: str | None
    agent_id: str | None
    current_stage: str
    stage_history: list[dict[str, Any]]
    strategy_version: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Knowledge ─────────────────────────────────────────────────────────────────

class KnowledgeChunkResponse(BaseModel):
    id: str
    document_name: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class RetrievalTestRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalTestResponse(BaseModel):
    results: list[dict[str, Any]]
    latency_ms: float


# ── Prompt Registry ───────────────────────────────────────────────────────────

class PromptTemplateCreate(BaseModel):
    name: str
    template: str
    variables: list[str] = Field(default_factory=list)
    description: str | None = None


class PromptTemplateUpdate(BaseModel):
    template: str | None = None
    variables: list[str] | None = None
    description: str | None = None
    traffic_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = None


class PromptTemplateResponse(BaseModel):
    id: str
    name: str
    version: int
    template: str
    variables: list[str]
    description: str | None
    avg_reward: float
    traffic_weight: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Flywheel / Preference Pairs ───────────────────────────────────────────────

class PreferencePairResponse(BaseModel):
    id: str
    session_id: str
    turn_index: int
    user_message: str
    chosen_response: str
    rejected_response: str
    reward_scores: dict[str, Any]
    metadata: dict[str, Any] = Field(alias="metadata_")
    exported: bool
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class FlywheelStatusResponse(BaseModel):
    total_preference_pairs: int
    exported_pairs: int
    pending_pairs: int
    last_apo_cycle: datetime | None
    avg_reward_last_100: float | None
    reward_trend: str  # "improving" | "declining" | "stable"


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvaluationRecordResponse(BaseModel):
    id: str
    session_id: str
    level: str
    turn_index: int | None
    scores: dict[str, Any]
    metadata: dict[str, Any] = Field(alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SessionEvaluationSummary(BaseModel):
    session_id: str
    total_turns: int
    stages_traversed: list[str]
    avg_reward: float
    conversion_signal: float
    stage_advancement_rate: float
    guard_intervention_count: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
