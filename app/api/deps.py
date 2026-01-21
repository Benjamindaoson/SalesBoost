"""
API Dependencies - 依赖注入
遵循 FastAPI 的 Depends 模式，实现 Clean Architecture 的依赖倒置
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prompt_service import PromptService
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models.base import User


# 全局服务实例（延迟初始化）
_settings: Optional[Settings] = None
_prompt_service: Optional[PromptService] = None


def get_settings_dependency() -> Settings:
    """获取配置依赖"""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_prompt_service(
    settings: Settings = Depends(get_settings_dependency)
) -> PromptService:
    """获取提示词服务依赖"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService(settings=settings)
    return _prompt_service


# 会话管理
_session_states: dict = {}


def get_session_state(session_id: str) -> dict:
    """获取会话状态"""
    if session_id not in _session_states:
        from app.schemas.state import create_initial_state
        _session_states[session_id] = create_initial_state()
    return _session_states[session_id]


def update_session_state(session_id: str, new_state: dict) -> None:
    """更新会话状态"""
    _session_states[session_id] = new_state


def clear_session_state(session_id: str) -> None:
    """清除会话状态"""
    if session_id in _session_states:
        del _session_states[session_id]


def get_session_count() -> int:
    """获取活跃会话数量"""
    return len(_session_states)


async def cleanup_expired_sessions():
    """清理过期会话（未来扩展）"""
    # TODO: 实现基于时间的会话清理
    pass


# 数据库会话依赖
async def get_db(db: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    """获取数据库会话"""
    return db


# 请求上下文
async def get_request_context(request: Request) -> dict:
    """获取请求上下文信息"""
    return {
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "path": request.url.path,
        "method": request.method
    }


def get_current_active_user() -> User:
    """Fallback current user dependency for API routes."""
    return User()

