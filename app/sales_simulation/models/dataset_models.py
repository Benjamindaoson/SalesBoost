"""
数据集数据库模型
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PreferencePairRecord(Base, TimestampMixin):
    """偏好对记录"""
    __tablename__ = "preference_pairs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # 偏好对
    chosen_trajectory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rejected_trajectory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # 上下文
    context: Mapped[str] = mapped_column(Text, nullable=False)
    chosen_response: Mapped[str] = mapped_column(Text, nullable=False)
    rejected_response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 质量差异
    score_delta: Mapped[float] = mapped_column(Float, nullable=False)
    quality_delta: Mapped[float] = mapped_column(Float, nullable=False)
    
    # 偏好原因
    preference_reason: Mapped[str] = mapped_column(Text, nullable=False)
    preference_dimensions: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SFTSampleRecord(Base, TimestampMixin):
    """SFT 样本记录"""
    __tablename__ = "sft_samples"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trajectory_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 训练数据
    context: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 质量标签
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_positive_example: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # 标注信息
    annotator: Mapped[str] = mapped_column(String(50), default="auto")
    annotation_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    # 标签
    tags_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)




