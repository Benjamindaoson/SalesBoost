"""
合规事件日志模型
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ComplianceLog(Base, TimestampMixin):
    """合规事件日志"""
    __tablename__ = "compliance_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
    turn_number: Mapped[int] = mapped_column(nullable=False)
    
    # 原始和改写文本
    original: Mapped[str] = mapped_column(Text, nullable=False)
    rewrite: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 风险信息
    risk_tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # OK/WARN/BLOCK
    
    # 时间戳
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    def __repr__(self) -> str:
        return f"<ComplianceLog(id={self.id}, session_id={self.session_id}, risk_level={self.risk_level})>"

