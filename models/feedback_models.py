"""
轻量复盘反馈模型
"""
from datetime import datetime
from typing import Dict, List

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class SessionFeedback(Base, TimestampMixin):
    """会话轻量复盘反馈"""
    __tablename__ = "session_feedbacks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # 反馈项（JSON存储，最多3条）
    feedback_items: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)
    
    # 会话统计
    total_turns: Mapped[int] = mapped_column(nullable=False)
    
    # 生成时间
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    def __repr__(self) -> str:
        return f"<SessionFeedback(id={self.id}, session_id={self.session_id}, items={len(self.feedback_items)})>"

