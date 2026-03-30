"""
Task Model

Represents learning tasks within courses.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from .base import BaseModel


class TaskStatus(str, PyEnum):
    """Task status."""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task(BaseModel):
    """
    Task model.

    Attributes:
        id: Primary key
        course_id: Foreign key to course
        title: Task title
        description: Task description
        task_type: Task type (e.g., "conversation", "quiz", "simulation")
        status: Task status
        order: Display order within course
        points: Points awarded for completion
        passing_score: Minimum score to pass (0-100)
        time_limit_minutes: Time limit in minutes (optional)
        instructions: Detailed instructions
        scenario: Training scenario (for conversation tasks)
        customer_profile: Customer profile (for simulation tasks)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "tasks"

    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    task_type = Column(String(50), nullable=False)  # conversation, quiz, simulation
    status = Column(Enum(TaskStatus), default=TaskStatus.LOCKED, nullable=False)
    order = Column(Integer, default=0)
    points = Column(Integer, default=100)
    passing_score = Column(Float, default=70.0)  # 0-100
    time_limit_minutes = Column(Integer)
    instructions = Column(Text)
    scenario = Column(Text)  # JSON
    customer_profile = Column(Text)  # JSON

    # Relationships
    course = relationship("Course", back_populates="tasks")
    sessions = relationship("Session", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, type={self.task_type})>"
