"""
Configuration models for scenarios, courses, and customer personas.

These ORM models map to tables from the multi-tenant migration schema
(scenario_configs, courses, customer_personas) with String UUID primary keys.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel as PydanticBase
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

# Use same Base as app.models for table registration
from .base import Base

# ---------------------------------------------------------------------------
# Pydantic schemas (for validation / simple use cases)
# ---------------------------------------------------------------------------


class CustomerPersonaSchema(PydanticBase):
    """Lightweight schema for persona-like data (tests, validation)."""

    name: str
    occupation: str
    personality_traits: str
    pain_points: Optional[str] = None
    goals: Optional[str] = None


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models (multi-tenant schema with String UUID ids)
# ---------------------------------------------------------------------------


class Course(Base):
    """
    Course model (multi-tenant schema).
    Maps to 'mt_courses' table - used by websocket, admin, scenarios.
    Separate from app.models.course (Integer id) to avoid schema conflict.
    """

    __tablename__ = "mt_courses"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), index=True, nullable=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    product_category = Column(String(100), nullable=False)
    difficulty_level = Column(String(20), nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    tags = Column(Text, nullable=True)  # JSON stored as text
    prerequisites = Column(Text, nullable=True)
    learning_objectives = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class ScenarioConfig(Base):
    """
    Scenario configuration model.
    Maps to 'scenario_configs' table.
    """

    __tablename__ = "scenario_configs"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), index=True, nullable=True)
    course_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    product_category = Column(String(100), nullable=False)
    scenario_background = Column(Text, nullable=True)
    sales_goal = Column(Text, nullable=True)
    success_criteria = Column(Text, nullable=True)  # JSON as text
    stage_configs = Column(Text, nullable=True)  # JSON as text
    max_turns = Column(Integer, nullable=False, default=10)
    difficulty_level = Column(String(20), nullable=False)
    customer_difficulty = Column(Float, nullable=True, default=0.5)
    required_level = Column(Integer, nullable=True, default=1)
    prerequisite_skills = Column(Text, nullable=True)  # JSON as text
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class CustomerPersona(Base):
    """
    Customer persona model (NPC profiles for training).
    Maps to 'customer_personas' table.
    """

    __tablename__ = "customer_personas"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), index=True, nullable=True)
    scenario_id = Column(String(36), index=True, nullable=True)  # nullable for admin-created personas
    name = Column(String(100), nullable=False)
    occupation = Column(String(100), nullable=True)
    age_range = Column(String(20), nullable=True)
    gender = Column(String(10), nullable=True)
    personality_traits = Column(Text, nullable=True)
    communication_style = Column(String(100), nullable=True)
    decision_style = Column(String(100), nullable=True)
    buying_motivation = Column(Text, nullable=True)
    main_concerns = Column(Text, nullable=True)
    budget_sensitivity = Column(String(50), nullable=True)
    initial_mood = Column(Float, nullable=True, default=0.5)
    mood_volatility = Column(Float, nullable=True, default=0.3)
    difficulty_level = Column(String(20), nullable=True, default="medium")
    objection_frequency = Column(Float, nullable=True, default=0.3)
    is_active = Column(Boolean, nullable=True, default=True)
    tags = Column(Text, nullable=True)  # JSON as text, for admin personas
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class Session(Base):
    """
    Session model (multi-tenant schema).
    Maps to 'mt_sessions' - used by websocket when session_id is UUID string.
    """

    __tablename__ = "mt_sessions"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), index=True, nullable=True)
    user_id = Column(String(36), nullable=False, index=True)
    course_id = Column(String(36), nullable=False, index=True)
    scenario_id = Column(String(36), nullable=False, index=True)
    persona_id = Column(String(36), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=False)
    total_turns = Column(Integer, nullable=False, default=0)
    total_duration_seconds = Column(Integer, nullable=False, default=0)
    final_score = Column(Float, nullable=True)
    final_stage = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SessionState(Base):
    """
    Session state model (FSM state for training sessions).
    Maps to 'session_states' table from migration 40070aac3057.
    """

    __tablename__ = "session_states"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, unique=True, index=True)
    current_stage = Column(String(50), nullable=False)
    stage_history = Column(Text, nullable=True)  # JSON as text
    slot_values = Column(Text, nullable=True)  # JSON as text
    stage_coverages = Column(Text, nullable=True)  # JSON as text
    goal_achieved = Column(Text, nullable=True)  # JSON as text
    npc_mood = Column(Float, nullable=False, default=0.5)
    turn_count = Column(Integer, nullable=False, default=0)
    context_snapshot = Column(Text, nullable=True)  # JSON as text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Backward compatibility: CustomerPersonaSchema as alias for tests that use Pydantic
__all__ = [
    "Course",
    "ScenarioConfig",
    "CustomerPersona",
    "CustomerPersonaSchema",
    "Session",
    "SessionState",
]
