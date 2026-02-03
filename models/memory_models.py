"""
Memory Layer Models
Event Store / Episode / Memory Items / Reflective Rules
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class AgentEventType(str, Enum):
    LLM_CALL = "LLM_CALL"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    RETRIEVAL = "RETRIEVAL"
    DECISION = "DECISION"
    WRITE_MEMORY = "WRITE_MEMORY"
    ERROR = "ERROR"
    METRIC = "METRIC"
    USER_MESSAGE = "USER_MESSAGE"


class MemoryType(str, Enum):
    SEMANTIC = "SEMANTIC"
    REFLECTIVE = "REFLECTIVE"


class MemoryScope(str, Enum):
    GLOBAL = "GLOBAL"
    ORG = "ORG"
    USER = "USER"
    SCENARIO = "SCENARIO"
    KB = "KB"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SHADOW = "SHADOW"
    DEPRECATED = "DEPRECATED"
    DELETED = "DELETED"


class RuleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SHADOW = "SHADOW"


class AgentEvent(Base):
    """Event Store: 可回放的事件序列"""
    __tablename__ = "agent_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    turn_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[AgentEventType] = mapped_column(SQLEnum(AgentEventType), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)

    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    parent_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)


class Episode(Base, TimestampMixin):
    """Episodic Memory 聚合"""
    __tablename__ = "episodes"

    episode_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    persona_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    goal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    score_overall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    start_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    episode_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replay_pointer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class MemoryItem(Base, TimestampMixin):
    """长期记忆元数据层"""
    __tablename__ = "memory_items"

    memory_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_type: Mapped[MemoryType] = mapped_column(SQLEnum(MemoryType), nullable=False, index=True)

    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    scope: Mapped[MemoryScope] = mapped_column(SQLEnum(MemoryScope), nullable=False, index=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    source_episode_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("episodes.episode_id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[MemoryStatus] = mapped_column(SQLEnum(MemoryStatus), default=MemoryStatus.SHADOW)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(50), default="agent")


class ReflectiveRule(Base, TimestampMixin):
    """可执行策略记忆"""
    __tablename__ = "reflective_rules"

    rule_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    scope: Mapped[MemoryScope] = mapped_column(SQLEnum(MemoryScope), nullable=False, index=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    trigger: Mapped[dict] = mapped_column(JSON, default=dict)
    action: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[RuleStatus] = mapped_column(SQLEnum(RuleStatus), default=RuleStatus.SHADOW)
    version: Mapped[int] = mapped_column(Integer, default=1)

    source_episode_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("episodes.episode_id"), nullable=True)
    explain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
