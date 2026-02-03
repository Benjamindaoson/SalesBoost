"""
配置类 Models
Course, ScenarioConfig, CustomerPersona
"""
from typing import List

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class Course(Base, TimestampMixin, SoftDeleteMixin):
    """课程配置"""
    __tablename__ = "courses"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 课程元数据
    tags: Mapped[dict] = mapped_column(JSON, default=list)
    prerequisites: Mapped[dict] = mapped_column(JSON, default=list)
    learning_objectives: Mapped[dict] = mapped_column(JSON, default=list)
    
    # 关联
    scenarios: Mapped[List["ScenarioConfig"]] = relationship(
        "ScenarioConfig",
        back_populates="course",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, name={self.name})>"


class ScenarioConfig(Base, TimestampMixin, SoftDeleteMixin):
    """场景配置"""
    __tablename__ = "scenario_configs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 场景设定
    scenario_background: Mapped[str] = mapped_column(Text, nullable=True)
    sales_goal: Mapped[str] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # FSM 配置
    stage_configs: Mapped[dict] = mapped_column(JSON, default=dict)
    max_turns: Mapped[int] = mapped_column(Integer, default=20)
    
    # 难度配置
    difficulty_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    customer_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    
    # P1: Level System
    required_level: Mapped[int] = mapped_column(Integer, default=1)
    prerequisite_skills: Mapped[dict] = mapped_column(JSON, default=dict) # e.g. {"reframe_value": 0.6}
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关联
    course: Mapped["Course"] = relationship("Course", back_populates="scenarios")
    personas: Mapped[List["CustomerPersona"]] = relationship(
        "CustomerPersona",
        back_populates="scenario",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<ScenarioConfig(id={self.id}, name={self.name})>"


class CustomerPersona(Base, TimestampMixin, SoftDeleteMixin):
    """客户人设配置"""
    __tablename__ = "customer_personas"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scenario_configs.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 基本信息
    occupation: Mapped[str] = mapped_column(String(100), nullable=True)
    age_range: Mapped[str] = mapped_column(String(20), nullable=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=True)
    
    # 性格特征
    personality_traits: Mapped[str] = mapped_column(Text, nullable=True)
    communication_style: Mapped[str] = mapped_column(String(100), nullable=True)
    decision_style: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # 购买相关
    buying_motivation: Mapped[str] = mapped_column(Text, nullable=True)
    main_concerns: Mapped[str] = mapped_column(Text, nullable=True)
    budget_sensitivity: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # 情绪配置
    initial_mood: Mapped[float] = mapped_column(Float, default=0.5)
    mood_volatility: Mapped[float] = mapped_column(Float, default=0.3)
    
    # 难度配置
    difficulty_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    objection_frequency: Mapped[float] = mapped_column(Float, default=0.3)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关联
    scenario: Mapped["ScenarioConfig"] = relationship(
        "ScenarioConfig",
        back_populates="personas",
    )
    
    def __repr__(self) -> str:
        return f"<CustomerPersona(id={self.id}, name={self.name})>"
