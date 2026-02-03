"""
Course Model

Represents training courses.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Enum, Integer, Float
from sqlalchemy.orm import relationship

from .base import BaseModel


class CourseStatus(str, PyEnum):
    """Course status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Course(BaseModel):
    """
    Course model.

    Attributes:
        id: Primary key
        title: Course title
        description: Course description
        status: Course status (draft/published/archived)
        category: Course category (e.g., "sales", "customer_service")
        difficulty: Difficulty level (1-5)
        duration_minutes: Estimated duration in minutes
        thumbnail_url: Course thumbnail image
        instructor_name: Instructor name
        learning_objectives: JSON array of learning objectives
        prerequisites: JSON array of prerequisites
        tags: JSON array of tags
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "courses"

    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT, nullable=False)
    category = Column(String(50), index=True)
    difficulty = Column(Integer, default=1)  # 1-5
    duration_minutes = Column(Integer)
    thumbnail_url = Column(String(255))
    instructor_name = Column(String(100))
    learning_objectives = Column(Text)  # JSON array
    prerequisites = Column(Text)  # JSON array
    tags = Column(Text)  # JSON array

    # Relationships
    tasks = relationship("Task", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, title={self.title}, status={self.status})>"
