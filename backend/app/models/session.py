"""
Session Model

Represents training sessions (user attempts at tasks).
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship

from .base import BaseModel


class SessionStatus(str, PyEnum):
    """Session status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Session(BaseModel):
    """
    Session model.

    Attributes:
        id: Primary key
        user_id: Foreign key to user
        task_id: Foreign key to task
        status: Session status
        score: Final score (0-100)
        duration_seconds: Session duration in seconds
        started_at: Session start timestamp
        completed_at: Session completion timestamp
        sales_state: Current sales FSM state
        customer_interest: Customer interest level (0-1)
        objections_raised: Number of objections raised
        objections_resolved: Number of objections resolved
        turns_count: Number of conversation turns
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "sessions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    score = Column(Float)  # 0-100
    duration_seconds = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Sales-specific fields
    sales_state = Column(String(50))  # opening, discovery, pitch, objection, closing
    customer_interest = Column(Float)  # 0-1
    objections_raised = Column(Integer, default=0)
    objections_resolved = Column(Integer, default=0)
    turns_count = Column(Integer, default=0)

    # Metadata
    metadata = Column(Text)  # JSON

    # Relationships
    user = relationship("User", back_populates="sessions")
    task = relationship("Task", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, task_id={self.task_id}, status={self.status})>"
