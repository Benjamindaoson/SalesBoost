"""
Knowledge Governance Models
"""
import hashlib
from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TimestampMixin


class KnowledgeAsset(Base, TimestampMixin, SoftDeleteMixin):
    """知识资产（逻辑文档）"""
    __tablename__ = "knowledge_assets"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    
    # 来源类型：script(话术), sop, objection(异议), faq, benefit(权益)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 当前活跃版本 ID
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # 租户隔离 (Part C)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    
    # 关联
    versions: Mapped[List["KnowledgeVersion"]] = relationship(
        "KnowledgeVersion",
        back_populates="asset",
        lazy="selectin",
        order_by="desc(KnowledgeVersion.version_number)"
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeAsset(id={self.id}, title={self.title})>"


class KnowledgeVersion(Base, TimestampMixin):
    """知识版本（物理内容）"""
    __tablename__ = "knowledge_versions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_assets.id"),
        nullable=False,
        index=True
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # 变更说明
    commit_message: Mapped[str] = mapped_column(String(200), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # 关联
    asset: Mapped["KnowledgeAsset"] = relationship("KnowledgeAsset", back_populates="versions")
    
    @staticmethod
    def calculate_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def __repr__(self) -> str:
        return f"<KnowledgeVersion(id={self.id}, v={self.version_number})>"
