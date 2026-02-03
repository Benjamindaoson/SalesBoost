"""API dependency helpers."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_schemas import UserSchema
from api.auth_utils import get_current_user_from_token
from core.config import EnvironmentState, Settings, get_settings
from core.database import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> UserSchema:
    return await get_current_user_from_token(token, db)

try:
    from app.brain.coordinator.prompt_manager import PromptService
except Exception:  # pragma: no cover
    PromptService = object  # type: ignore

_settings: Optional[Settings] = None
_prompt_service: Optional[PromptService] = None


def get_settings_dependency() -> Settings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_prompt_service(settings: Settings = Depends(get_settings_dependency)) -> PromptService:
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService(settings=settings)  # type: ignore
    return _prompt_service


# Session state cache (in-memory fallback)
_session_states: dict[str, dict] = {}


def get_session_state(session_id: str) -> dict:
    if session_id not in _session_states:
        from schemas.state import create_initial_state

        _session_states[session_id] = create_initial_state()
    return _session_states[session_id]


def update_session_state(session_id: str, new_state: dict) -> None:
    _session_states[session_id] = new_state


def clear_session_state(session_id: str) -> None:
    _session_states.pop(session_id, None)


def get_session_count() -> int:
    return len(_session_states)


async def cleanup_expired_sessions() -> None:
    # placeholder for future cleanup
    return None


async def get_db(db: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return db


async def get_request_context(request: Request) -> dict:
    return {
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "path": request.url.path,
        "method": request.method,
    }


def require_user(current_user: UserSchema = Depends(get_current_user)) -> UserSchema:
    return current_user


def require_admin(current_user: UserSchema = Depends(get_current_user)) -> UserSchema:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_admin_or_operator(current_user: UserSchema = Depends(get_current_user)) -> UserSchema:
    if current_user.role not in {"admin", "operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return current_user


def require_admin_user(current_user: UserSchema = Depends(get_current_user)) -> UserSchema:
    return require_admin(current_user)


from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, AuditEventPayload

async def audit_access(
    request: Request,
    current_user: UserSchema = Depends(get_current_user),
) -> None:
    settings = get_settings()
    if not settings.AUDIT_LOG_ENABLED:
        return None
    
    # Decoupled Audit: Publish event instead of blocking on DB write
    payload = AuditEventPayload(
        event_id=str(uuid.uuid4()),
        session_id=None,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        reason=f"API Access: {request.method} {request.url.path}",
        severity="info",
        details={
            "query": dict(request.query_params),
            "ip": request.client.host if request.client else None,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Fail-closed in production; best-effort in other environments.
    if settings.ENV_STATE == EnvironmentState.PRODUCTION:
        try:
            await bus.publish(EventType.ACCESS_LOGGED, payload)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit logging failed",
            )
    else:
        try:
            asyncio.create_task(bus.publish(EventType.ACCESS_LOGGED, payload))
        except Exception:
            pass
    return None
