"""
SaaS 核心模型
Tenant, User, Subscription, AuditLog
"""
from typing import List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    """租户（企业/组织）"""
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True) # 用于子域名或URL
    
    # 配置
    settings: Mapped[dict] = mapped_column(JSON, default=dict) # e.g. {"theme": "blue", "allow_guest": false}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关联
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="tenant")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name})>"

class User(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """用户（学员/管理员）"""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # tenant_id from TenantMixin
    
    username: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    role: Mapped[str] = mapped_column(String(20), default="student") # admin, operator, student
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关联
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

class Subscription(Base, TimestampMixin):
    """订阅/计费"""
    __tablename__ = "subscriptions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    
    plan_name: Mapped[str] = mapped_column(String(50)) # basic, pro, enterprise
    status: Mapped[str] = mapped_column(String(20)) # active, expired, cancelled
    
    # 限制
    max_users: Mapped[int] = mapped_column(Integer, default=5)
    max_training_minutes: Mapped[int] = mapped_column(Integer, default=1000)
    
    start_date: Mapped[Optional[str]] = mapped_column(String(30)) # ISO format
    end_date: Mapped[Optional[str]] = mapped_column(String(30))
    
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")

class AuditLog(Base, TimestampMixin, TenantMixin):
    """审计日志"""
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # tenant_id from TenantMixin
    
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(50)) # create_course, delete_user
    resource_type: Mapped[str] = mapped_column(String(50)) # course, user
    resource_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    details: Mapped[dict] = mapped_column(JSON, default=dict) # changed fields, old/new values
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
