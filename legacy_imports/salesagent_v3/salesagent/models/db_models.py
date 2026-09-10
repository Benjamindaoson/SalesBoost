"""SQLAlchemy async ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Sessions ─────────────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    customer_id: Mapped[str] = mapped_column(String(255), index=True, nullable=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=True)
    current_stage: Mapped[str] = mapped_column(String(50), default="ICEBREAK")
    stage_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    is_waiting_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    pending_human_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    status: Mapped[str] = mapped_column(String(50), default="active") # active, closed, failed| converted
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    memory_entities: Mapped[list["MemoryEntity"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    preference_pairs: Mapped[list["PreferencePair"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# ── Messages ─────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reward_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    guard_events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="messages")


# ── Memory Entities ───────────────────────────────────────────────────────────

class MemoryEntity(Base):
    __tablename__ = "memory_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))  # name | budget | pain_point | …
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="memory_entities")


# ── Prompt Templates ─────────────────────────────────────────────────────────

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    template: Mapped[str] = mapped_column(Text)
    variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    avg_reward: Mapped[float] = mapped_column(Float, default=0.0)
    traffic_weight: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | shadow | retired
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── Knowledge Chunks ─────────────────────────────────────────────────────────

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    document_name: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str] = mapped_column(String(36), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    minio_key: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Preference Pairs (DPO Data) ──────────────────────────────────────────────

class PreferencePair(Base):
    __tablename__ = "preference_pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_message: Mapped[str] = mapped_column(Text)
    chosen_response: Mapped[str] = mapped_column(Text)
    rejected_response: Mapped[str] = mapped_column(Text)
    reward_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    exported: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="preference_pairs")


# ── Evaluation Records ────────────────────────────────────────────────────────

class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    level: Mapped[str] = mapped_column(String(20))  # token | turn | session | cohort
    turn_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Guard Events ─────────────────────────────────────────────────────────────

class GuardEvent(Base):
    __tablename__ = "guard_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    risk_type: Mapped[str] = mapped_column(String(50))
    original_sentence: Mapped[str] = mapped_column(Text)
    rewritten_sentence: Mapped[str] = mapped_column(Text, nullable=True)
    rule_matched: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
