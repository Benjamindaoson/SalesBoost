"""
Base Model

SQLAlchemy declarative base and common mixins.
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class IDMixin:
    """Mixin for auto-incrementing integer ID."""

    id = Column(Integer, primary_key=True, autoincrement=True)


class BaseModel(Base, IDMixin, TimestampMixin):
    """Base model with ID and timestamps."""

    __abstract__ = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(id={self.id})>"
