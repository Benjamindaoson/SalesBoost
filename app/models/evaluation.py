"""
Evaluation Model

Represents performance evaluations for sessions.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from .base import BaseModel


class Evaluation(BaseModel):
    """
    Evaluation model.

    Attributes:
        id: Primary key
        session_id: Foreign key to session
        user_id: Foreign key to user
        overall_score: Overall score (0-10)
        methodology_score: Methodology score (0-10)
        objection_handling_score: Objection handling score (0-10)
        goal_orientation_score: Goal orientation score (0-10)
        empathy_score: Empathy score (0-10)
        clarity_score: Clarity score (0-10)
        strengths: List of strengths (JSON array)
        weaknesses: List of weaknesses (JSON array)
        suggestions: List of improvement suggestions (JSON array)
        detailed_feedback: Detailed feedback text
        evaluator: Evaluator (e.g., "ai_coach", "human_teacher")
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "evaluations"

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Scores (0-10)
    overall_score = Column(Float, nullable=False)
    methodology_score = Column(Float)
    objection_handling_score = Column(Float)
    goal_orientation_score = Column(Float)
    empathy_score = Column(Float)
    clarity_score = Column(Float)

    # Feedback
    strengths = Column(Text)  # JSON array
    weaknesses = Column(Text)  # JSON array
    suggestions = Column(Text)  # JSON array
    detailed_feedback = Column(Text)

    # Metadata
    evaluator = Column(String(50))  # ai_coach, human_teacher
    metadata = Column(Text)  # JSON

    # Relationships
    session = relationship("Session", back_populates="evaluations")
    user = relationship("User", back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<Evaluation(id={self.id}, session_id={self.session_id}, overall_score={self.overall_score})>"
