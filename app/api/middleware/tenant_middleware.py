"""
多租户中间件
从请求中提取租户信息并注入上下文
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import contextvars

# 定义上下文变量
tenant_context = contextvars.ContextVar("tenant_id", default=None)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 尝试从 Header 获取
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # 2. 尝试从 Auth Token 获取 (如果 AuthMiddleware 已经运行并解析了 User)
        if not tenant_id and hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "tenant_id"):
                tenant_id = user.tenant_id
        
        # 3. 设置上下文
        token = tenant_context.set(tenant_id)
        
        try:
            # 注入到 request.state 供后续使用
            request.state.tenant_id = tenant_id
            response = await call_next(request)
            return response
        finally:
            tenant_context.reset(token)

def get_current_tenant_id():
    """获取当前上下文中的 Tenant ID"""
    return tenant_context.get()
