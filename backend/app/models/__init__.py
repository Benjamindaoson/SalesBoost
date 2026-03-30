"""
Database Models

SQLAlchemy ORM models for SalesBoost.

Models:
- User: User accounts (students, admins)
- Course: Training courses
- Task: Learning tasks within courses
- Session: Training sessions
- Message: Conversation messages
- Evaluation: Performance evaluations
- Deal: Sales opportunities / pipeline items
- Encounter: Interactions within a deal (prep / live / review)
- CockpitEvent: Event stream for the executive cockpit
"""

from .base import Base
from .user import User, UserRole
from .course import Course, CourseStatus
from .task import Task, TaskStatus
from .session import Session, SessionStatus
from .message import Message, MessageRole
from .evaluation import Evaluation
from .deal import Deal, DealStage, Encounter, EncounterType, CockpitEvent

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Course",
    "CourseStatus",
    "Task",
    "TaskStatus",
    "Session",
    "SessionStatus",
    "Message",
    "MessageRole",
    "Evaluation",
    "Deal",
    "DealStage",
    "Encounter",
    "EncounterType",
    "CockpitEvent",
]
