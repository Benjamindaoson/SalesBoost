"""
SQLAlchemy Base Model
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TenantMixin:
    """多租户隔离 Mixin"""
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        doc="租户ID，为空表示系统级/公共资源"
    )


class TimestampMixin:
    """时间戳 Mixin"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """软删除 Mixin"""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# Removed Minimal User model - use models.saas_models.User instead
