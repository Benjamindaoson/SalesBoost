"""
User Model

Represents user accounts (students, admins, teachers).
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, String, Enum, Boolean, Integer
from sqlalchemy.orm import relationship

from .base import BaseModel


class UserRole(str, PyEnum):
    """User roles."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(BaseModel):
    """
    User model.

    Attributes:
        id: Primary key
        username: Unique username
        email: Email address
        password_hash: Hashed password
        role: User role (admin/teacher/student)
        full_name: Full name
        is_active: Account active status
        avatar_url: Profile picture URL
        phone: Phone number
        organization: Organization/company
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    avatar_url = Column(String(255))
    phone = Column(String(20))
    organization = Column(String(100))

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
