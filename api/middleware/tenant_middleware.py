"""
多租户中间件
从请求中提取租户信息并注入上下文
"""
import contextvars

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from typing import Optional

from api.auth_utils import get_current_user_from_token
from core.config import EnvironmentState, get_settings
from core.database import get_db_session

# 定义上下文变量
tenant_context = contextvars.ContextVar("tenant_id", default=None)
settings = get_settings()


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""
        public_prefixes = (
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/v1/auth",
        )
        if path.startswith(public_prefixes):
            return await call_next(request)

        header_tenant = request.headers.get("X-Tenant-ID")
        token = _extract_bearer_token(request)
        tenant_id = None
        user = None

        # Prefer token-derived tenant in all environments.
        if token:
            try:
                async for db in get_db_session():
                    user = await get_current_user_from_token(token, db)
                    break
            except Exception:
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication token"})

        if user:
            request.state.user = user
            tenant_id = getattr(user, "tenant_id", None)
            if header_tenant and user.role != "admin" and header_tenant != tenant_id:
                return JSONResponse(status_code=403, content={"detail": "Tenant mismatch"})
        else:
            # Only allow header-based tenant in non-production environments.
            if header_tenant and settings.ENV_STATE != EnvironmentState.PRODUCTION:
                tenant_id = header_tenant

        # 3. 设置上下文
        if tenant_id is None:
            return JSONResponse(status_code=401, content={"detail": "Tenant not found"})
        token_ctx = tenant_context.set(tenant_id)

        try:
            # 注入到 request.state 供后续使用
            request.state.tenant_id = tenant_id
            response = await call_next(request)
            return response
        finally:
            tenant_context.reset(token_ctx)

def get_current_tenant_id():
    """获取当前上下文中的 Tenant ID"""
    return tenant_context.get()
