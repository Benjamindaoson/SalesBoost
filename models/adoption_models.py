"""
采纳记录与策略决策 Models
实现「建议采纳 → 能力变化」的因果账本
"""
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class AdoptionStyle(str, Enum):
    """采纳风格"""
    VERBATIM = "verbatim"              # 原封不动采纳
    PARAPHRASED = "paraphrased"        # 改述采纳
    STRATEGY_ONLY = "strategy_only"    # 仅采纳策略思路
    NOT_ADOPTED = "not_adopted"        # 未采纳


class AdoptionRecord(Base, TimestampMixin):
    """
    采纳记录 - 因果账本核心
    记录哪条 Coach 建议被采纳，以及是否带来能力提升
    """
    __tablename__ = "adoption_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # 建议来源
    turn_id: Mapped[int] = mapped_column(Integer, nullable=False)
    suggestion_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    technique_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # 采纳情况
    adopted: Mapped[bool] = mapped_column(Boolean, default=False)
    adoption_style: Mapped[AdoptionStyle] = mapped_column(
        SQLEnum(AdoptionStyle),
        default=AdoptionStyle.NOT_ADOPTED,
    )
    adoption_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 效果观察
    observed_turn_offset: Mapped[int] = mapped_column(Integer, default=1)
    baseline_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    skill_delta: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 统计标记
    is_effective: Mapped[bool] = mapped_column(Boolean, default=False)
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 策略上下文
    stage: Mapped[str] = mapped_column(String(50), nullable=True)
    situation_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    strategy_suggested: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    def __repr__(self) -> str:
        return f"<AdoptionRecord(id={self.id}, adopted={self.adopted}, effective={self.is_effective})>"


class StrategyDecision(Base, TimestampMixin):
    """
    策略决策记录
    记录用户在每个情境下选择的策略 vs 销冠最优策略
    """
    __tablename__ = "strategy_decisions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    turn_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 情境分类
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    situation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    situation_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 策略选择
    strategy_chosen: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    available_strategies: Mapped[dict] = mapped_column(JSON, default=list)
    
    # 最优判断
    is_optimal: Mapped[bool] = mapped_column(Boolean, default=False)
    golden_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    optimality_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 效果评估
    immediate_score: Mapped[float] = mapped_column(Float, default=0.0)
    npc_mood_change: Mapped[float] = mapped_column(Float, default=0.0)
    goal_progress: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<StrategyDecision(stage={self.stage}, chosen={self.strategy_chosen}, optimal={self.is_optimal})>"


class UserStrategyProfile(Base, TimestampMixin):
    """
    用户策略画像
    聚合用户的策略选择模式，用于 Curriculum Planning
    """
    __tablename__ = "user_strategy_profiles"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    
    # 策略偏好统计
    strategy_frequency: Mapped[dict] = mapped_column(JSON, default=dict)
    optimal_rate_by_stage: Mapped[dict] = mapped_column(JSON, default=dict)
    optimal_rate_by_situation: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 与销冠差距
    deviation_patterns: Mapped[dict] = mapped_column(JSON, default=list)
    top_weakness_situations: Mapped[dict] = mapped_column(JSON, default=list)
    
    # 采纳统计
    adoption_rate: Mapped[float] = mapped_column(Float, default=0.0)
    effective_adoption_rate: Mapped[float] = mapped_column(Float, default=0.0)
    most_effective_techniques: Mapped[dict] = mapped_column(JSON, default=list)
    
    # 训练推荐
    recommended_focus: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 训练锁
    locked_curriculum: Mapped[dict] = mapped_column(JSON, default=dict)
    user_override_count: Mapped[int] = mapped_column(Integer, default=0)
    
    def __repr__(self) -> str:
        return f"<UserStrategyProfile(user_id={self.user_id})>"
