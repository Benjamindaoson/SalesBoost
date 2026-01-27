"""
Evaluation Configuration Models
"""
from sqlalchemy import JSON, Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, SoftDeleteMixin, TimestampMixin


class EvaluationDimension(Base, TimestampMixin, SoftDeleteMixin):
    """评估维度配置"""
    __tablename__ = "evaluation_dimensions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 权重配置
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    
    # 适用范围
    applicable_stages: Mapped[dict] = mapped_column(JSON, default=list) # List[str]
    
    # 评分标准 (给 LLM 的 Prompt)
    criteria_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def __repr__(self) -> str:
        return f"<EvaluationDimension(id={self.id}, name={self.name})>"
