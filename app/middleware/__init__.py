"""
API Middleware Collection - API中间件集合
包含认证、限流、监控、日志等中间件
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """请求限流中间件"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 允许的请求数
        self.period = period  # 时间窗口(秒)
        self.clients = {}  # 简单内存存储，生产环境应使用Redis

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # 清理过期记录
        self._cleanup_expired_records(current_time)

        # 检查并更新请求计数
        if client_ip in self.clients:
            requests = self.clients[client_ip]["requests"]
            # 检查时间窗口内的请求数
            window_start = current_time - self.period
            recent_requests = [req_time for req_time in requests if req_time > window_start]

            if len(recent_requests) >= self.calls:
                return self._rate_limit_response()

            recent_requests.append(current_time)
            self.clients[client_ip]["requests"] = recent_requests
        else:
            self.clients[client_ip] = {"requests": [current_time]}

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_expired_records(self, current_time: float):
        """清理过期记录"""
        window_start = current_time - self.period
        for client_ip in list(self.clients.keys()):
            requests = self.clients[client_ip]["requests"]
            self.clients[client_ip]["requests"] = [req_time for req_time in requests if req_time > window_start]
            if not self.clients[client_ip]["requests"]:
                del self.clients[client_ip]

    def _rate_limit_response(self) -> JSONResponse:
        """返回限流响应"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {self.calls} per {self.period}s",
            },
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if settings.ENV_STATE == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        start_time = time.time()

        # 记录请求信息
        logger.info(
            f"Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        response = await call_next(request)

        # 记录响应信息
        process_time = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
            },
        )

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件"""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 默认10MB
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # 检查Content-Length头
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content={"error": "Request entity too large"}
            )

        response = await call_next(request)
        return response


def setup_middleware(app):
    """设置所有中间件"""

    # 1. 安全头中间件 (最先执行)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. CORS中间件
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
    except Exception as e:
        logger.warning(f"CORS middleware setup failed: {e}")

    # 3. 请求大小限制
    app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)

    # 4. 限流中间件 (每用户100请求/分钟)
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)

    # 5. 日志中间件
    app.add_middleware(LoggingMiddleware)

    logger.info("All middleware has been set up successfully")


# 导出中间件类
__all__ = [
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "LoggingMiddleware",
    "RequestSizeMiddleware",
    "setup_middleware",
]
