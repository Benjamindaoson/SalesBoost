"""
Message Model

Represents conversation messages within sessions.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from .base import BaseModel


class MessageRole(str, PyEnum):
    """Message role."""
    USER = "user"  # Student
    ASSISTANT = "assistant"  # AI agent
    SYSTEM = "system"  # System message
    CUSTOMER = "customer"  # Simulated customer


class Message(BaseModel):
    """
    Message model.

    Attributes:
        id: Primary key
        session_id: Foreign key to session
        role: Message role (user/assistant/system/customer)
        content: Message content
        intent: Detected intent (for user messages)
        emotion: Detected emotion (for customer messages)
        sales_technique: Sales technique used (e.g., "SPIN", "FAB")
        score: Message quality score (0-10)
        feedback: AI coach feedback
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "messages"

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(50))  # product_inquiry, pricing_question, objection, etc.
    emotion = Column(String(50))  # friendly, curious, skeptical, etc.
    sales_technique = Column(String(50))  # SPIN, FAB, etc.
    score = Column(Float)  # 0-10
    feedback = Column(Text)
    metadata = Column(Text)  # JSON

    # Relationships
    session = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role})>"
