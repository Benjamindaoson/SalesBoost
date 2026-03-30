"""
Memory Service Models - Compatibility layer

This module provides SQLAlchemy ORM models for the Memory Service.
Includes MemoryAudit, MemoryEvent, MemoryKnowledge, MemoryOutcome, MemoryPersona, and MemoryStrategyUnit.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, String, Text, ForeignKey, Index, UniqueConstraint
)
from pydantic import BaseModel

from .base import Base


class MemoryEvent(Base):
    """SQLAlchemy ORM model for persisting conversation memory events."""
    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    channel = Column(String(32), nullable=True)
    turn_index = Column(Integer, nullable=True)
    speaker = Column(String(32), nullable=True)

    # Content fields
    raw_text_ref = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # Intent / classification
    intent_top1 = Column(String(128), nullable=True)
    intent_topk = Column(JSON, nullable=True)   # list[dict]

    # Sales context
    stage = Column(String(64), nullable=True)
    objection_type = Column(String(64), nullable=True)
    entities = Column(JSON, nullable=True)

    # Sentiment / risk
    sentiment = Column(Float, nullable=True)
    tension = Column(Float, nullable=True)
    compliance_flags = Column(JSON, nullable=True)

    # Coach signals
    coach_suggestions_shown = Column(JSON, nullable=True)
    coach_suggestions_taken = Column(JSON, nullable=True)

    # Arbitrary metadata
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<MemoryEvent(event_id={self.event_id}, session={self.session_id})>"


class MemoryAudit(Base):
    """SQLAlchemy ORM model for memory access auditing."""
    __tablename__ = "memory_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    
    input_digest = Column(String(128), nullable=True)
    route = Column(String(64), nullable=True)
    retrieved_ids = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    compliance_hits = Column(JSON, nullable=True)
    output_digest = Column(String(128), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MemoryKnowledge(Base):
    """SQLAlchemy ORM model for persisted knowledge units."""
    __tablename__ = "memory_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    knowledge_id = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    
    domain = Column(String(64), nullable=True)
    product_id = Column(String(64), nullable=True)
    structured_content = Column(JSON, nullable=True)
    source_ref = Column(String(256), nullable=True)
    
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    is_enabled = Column(Boolean, default=True)
    citation_snippets = Column(JSON, nullable=True)
    
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'knowledge_id', 'version', name='_tenant_knowledge_version_uc'),)


class MemoryOutcome(Base):
    """SQLAlchemy ORM model for session outcomes."""
    __tablename__ = "memory_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outcome_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    
    adopted = Column(Boolean, default=False)
    adopt_type = Column(String(32), nullable=True)
    stage_before = Column(String(64), nullable=True)
    stage_after = Column(String(64), nullable=True)
    
    eval_scores = Column(JSON, nullable=True)
    compliance_result = Column(JSON, nullable=True)
    final_result = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MemoryPersona(Base):
    """SQLAlchemy ORM model for user personas and skill profiles."""
    __tablename__ = "memory_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    
    level = Column(String(32), nullable=True)
    weakness_tags = Column(JSON, nullable=True)
    last_eval_summary = Column(Text, nullable=True)
    last_improvements = Column(JSON, nullable=True)
    next_actions = Column(JSON, nullable=True)
    history_stats = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryStrategyUnit(Base):
    """SQLAlchemy ORM model for sales strategy units."""
    __tablename__ = "memory_strategy_units"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    strategy_id = Column(String(64), nullable=False, index=True)
    
    type = Column(String(64), nullable=True)
    trigger_intent = Column(String(128), nullable=True)
    trigger_stage = Column(String(64), nullable=True)
    trigger_objection_type = Column(String(64), nullable=True)
    trigger_level = Column(String(32), nullable=True)
    trigger_condition = Column(JSON, nullable=True)
    
    steps = Column(JSON, nullable=True)
    scripts = Column(JSON, nullable=True)
    dos_donts = Column(JSON, nullable=True)
    evidence_event_ids = Column(JSON, nullable=True)
    
    stats = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, default=True)
    
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryStrategyUnitPydantic(BaseModel):
    """Memory strategy unit model (Pydantic schema)."""
    id: Optional[str] = None
    strategy_type: str = "default"
    config: Dict[str, Any] = {}

# Keep the original name for backward compatibility in imports if needed
MemoryStrategyUnitSchema = MemoryStrategyUnitPydantic


__all__ = [
    "MemoryAudit",
    "MemoryEvent",
    "MemoryKnowledge",
    "MemoryOutcome",
    "MemoryPersona",
    "MemoryStrategyUnit",
    "MemoryStrategyUnitPydantic",
]
