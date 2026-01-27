"""
运行时 Models
Session, Message, SessionState
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Session(Base, TimestampMixin):
    """训练会话"""
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    persona_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # 会话状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        index=True,
    )  # active, completed, abandoned, timeout
    
    # 时间信息
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # 统计信息
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # 最终评分
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 关联
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="session",
        lazy="selectin",
        order_by="Message.turn_number",
    )
    state: Mapped[Optional["SessionState"]] = relationship(
        "SessionState",
        back_populates="session",
        uselist=False,
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Message(Base, TimestampMixin):
    """对话消息"""
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
    
    # 消息内容
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, npc, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="committed", index=True)
    
    # 阶段信息
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Agent 输出（JSON 存储）
    intent_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    npc_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    coach_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    evaluator_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rag_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    compliance_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 评分快照
    turn_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 元数据
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 关联
    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, turn={self.turn_number}, role={self.role})>"


class SessionState(Base, TimestampMixin):
    """会话状态快照"""
    __tablename__ = "session_states"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # FSM 状态
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_history: Mapped[dict] = mapped_column(JSON, default=list)
    
    # Slot 状态
    slot_values: Mapped[dict] = mapped_column(JSON, default=dict)
    stage_coverages: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 目标状态
    goal_achieved: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # NPC 状态
    npc_mood: Mapped[float] = mapped_column(Float, default=0.5)
    
    # 轮次
    turn_count: Mapped[int] = mapped_column(Integer, default=0)

    # Context snapshot
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 关联
    session: Mapped["Session"] = relationship("Session", back_populates="state")
    
    def __repr__(self) -> str:
        return f"<SessionState(session_id={self.session_id}, stage={self.current_stage})>"


class EvaluationLog(Base, TimestampMixin):
    """评估日志 (Flattened for Analytics)"""
    __tablename__ = "evaluation_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 评分
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    dimension_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 关联
    session: Mapped["Session"] = relationship("Session")
