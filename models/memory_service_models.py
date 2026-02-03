"""Memory service storage models."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy import ForeignKey
from sqlalchemy import JSON as SAJSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

JSONB = postgresql.JSONB().with_variant(SAJSON(), "sqlite")
ARRAY_TEXT = postgresql.ARRAY(Text()).with_variant(SAJSON(), "sqlite")


class MemoryEvent(Base):
    __tablename__ = "memory_event"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    turn_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_text_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intent_top1: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    intent_topk: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    objection_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entities: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    sentiment: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tension: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    compliance_flags: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    coach_suggestions_shown: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    coach_suggestions_taken: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoryOutcome(Base):
    __tablename__ = "memory_outcome"

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(128), ForeignKey("memory_event.event_id"), nullable=False, index=True)
    adopted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    adopt_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    stage_before: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stage_after: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    eval_scores: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    compliance_result: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    final_result: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoryPersona(Base):
    __tablename__ = "memory_persona"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    weakness_tags: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    last_eval_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_improvements: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    next_actions: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    history_stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemoryKnowledge(Base):
    __tablename__ = "memory_knowledge"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    knowledge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    structured_content: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    citation_snippets: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    
    # Decay & Reactivation fields
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    decay_score: Mapped[float] = mapped_column(Float, default=1.0)
    
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemoryStrategyUnit(Base):
    __tablename__ = "memory_strategy_unit"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    trigger_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trigger_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trigger_objection_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trigger_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    trigger_condition: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    steps: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    scripts: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    dos_donts: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    evidence_event_ids: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Decay & Reactivation fields
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    decay_score: Mapped[float] = mapped_column(Float, default=1.0)
    
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemoryAudit(Base):
    __tablename__ = "memory_audit"

    request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_digest: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    retrieved_ids: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    compliance_hits: Mapped[List[str]] = mapped_column(ARRAY_TEXT, default=list)
    output_digest: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
