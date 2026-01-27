"""
SalesBoost FastAPI Application - Clean Architecture Entry Point

这是整个应用的入口点，遵循 Clean Architecture 原则：
- 只负责应用初始化和中间件配置
- 不包含任何业务逻辑
- 通过依赖注入的方式提供服务

架构层级：
├── main.py (入口层) - 应用启动、路由配置、中间件
├── api/ (接口层) - WebSocket 端点、依赖注入
├── services/ (业务逻辑层) - FSM 状态机、提示词管理
├── agents/ (智能体编排层) - LLM 节点、图构建
├── schemas/ (数据传输层) - 请求响应模型定义
└── core/ (基础设施层) - 配置管理、LLM 客户端、异常处理
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from api.deps import get_session_count
from api.middleware.tenant_middleware import TenantMiddleware
from core.config import Settings, get_settings
from core.database import close_db, init_db
from core.exceptions import SalesBoostException, create_error_response
from core.redis import close_redis, get_redis
from app.middleware import setup_middleware

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    遵循 FastAPI 的 lifespan 事件模式
    """
    # 启动事件
    logger.info("SalesBoost application starting...")
    logger.info("Initializing services and connections...")

    # 初始化数据库
    # Database initialization
    try:
        from core.database import engine
        from models.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

        await init_db()
        logger.info("Database initialized successfully")

        # Data retention cleanup (best-effort)
        try:
            from core.retention import run_retention_cleanup

            deleted = await run_retention_cleanup()
            if deleted:
                logger.info("Retention cleanup deleted %s rows", deleted)
        except Exception as e:
            logger.warning("Retention cleanup failed: %s", e)
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    try:
        await get_redis()
        logger.info("Redis initialized successfully ✅")
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}. Using in-memory fallback ⚠️")

    # 初始化 LLM 系统
    try:
        from core.llm import initialize_llm_system

        await initialize_llm_system()
        logger.info("LLM system initialized successfully ✅")
    except Exception as e:
        logger.warning(f"LLM system initialization failed: {e}. Running in mock mode ⚠️")

    # 初始化成本控制系统
    try:
        logger.info("Initializing AI cost control system...")
        # cost_optimized_caller is already initialized as a global instance
        logger.info("AI cost control system initialized successfully ✅")
    except Exception as e:
        logger.warning(f"Cost control system initialization failed: {e}. Using fallback ⚠️")

    # 初始化状态恢复系统
    try:
        logger.info("Initializing state recovery system...")
        from app.engine.state.recovery import state_recovery_service

        await state_recovery_service.initialize()
        logger.info("State recovery system initialized successfully ✅")
    except Exception as e:
        logger.warning(f"State recovery system initialization failed: {e}. Recovery features disabled ⚠️")

    # 启动后台任务
    try:
        logger.info("Starting background task manager...")
        from app.engine.coordinator.task_executor import background_task_manager

        await background_task_manager.start()
        logger.info("Background task manager started successfully ✅")
    except Exception as e:
        logger.warning(f"Background task manager failed to start: {e}. ⚠️")

    # 启动性能指标收集
    try:
        logger.info("Starting performance metrics collector...")
        from app.observability.metrics.business_metrics import performance_metrics_collector

        await performance_metrics_collector.initialize()
        logger.info("Performance metrics collector started successfully ✅")
    except Exception as e:
        logger.warning(f"Performance metrics collector failed to start: {e}. ⚠️")

    # 启动性能指标收集
    yield

    # 关闭事件
    logger.info("SalesBoost application shutting down...")
    logger.info("Cleaning up resources...")

    # 停止后台任务
    try:
        from app.engine.coordinator.task_executor import background_task_manager

        await background_task_manager.stop()
        logger.info("Background task manager stopped successfully ✅")
    except Exception as e:
        logger.warning(f"Error stopping background task manager: {e}")

    await close_db()
    await close_redis()


def create_application(settings: Settings = None) -> FastAPI:
    """
    创建 FastAPI 应用实例
    应用工厂模式，支持测试和配置注入

    Args:
        settings: 配置对象，默认使用全局配置

    Returns:
        配置好的 FastAPI 应用实例
    """
    if settings is None:
        settings = get_settings()

    # 初始化 Sentry
    if os.getenv("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
        )
        logger.info("Sentry initialized")

    # 创建应用实例
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # 配置中间件 - 使用我们的综合中间件系统
    setup_middleware(app)

    # 注册多租户中间件 (必须在 AuthMiddleware 之后，但在业务逻辑之前)
    # 由于 BaseHTTPMiddleware 的执行顺序，后添加的先执行
    # 我们希望 TenantMiddleware 在 Auth 解析出 User 之后执行，或者直接从 Header 解析
    # 这里简单添加到中间件栈中
    app.add_middleware(TenantMiddleware)

    # 配置路由
    _configure_routes(app)

    # 配置异常处理器
    _configure_exception_handlers(app)

    logger.info(f"FastAPI application created: {settings.PROJECT_NAME} v{settings.VERSION}")
    return app


def _configure_routes(app: FastAPI) -> None:
    """Configure application routes."""

    @app.get("/health")
    async def health_check():
        session_count = get_session_count()
        return {
            "status": "healthy",
            "version": app.version,
            "active_sessions": session_count,
            "debug_mode": app.debug,
        }

    @app.get("/metrics/cost")
    async def cost_metrics():
        try:
            from app.infra.gateway.cost_control import cost_optimized_caller

            return {
                "status": "healthy",
                "cost_optimization_enabled": True,
                "active_budgets": len(cost_optimized_caller.budget_manager.session_budgets),
                "total_cost_records": len(cost_optimized_caller.budget_manager.cost_tracking),
                "available_models": len(cost_optimized_caller.smart_router.available_models),
                "timestamp": time.time(),
            }
        except Exception as e:
            return {
                "status": "error",
                "cost_optimization_enabled": False,
                "error": str(e),
                "timestamp": time.time(),
            }

    @app.get("/metrics/background")
    async def background_metrics():
        try:
            from app.engine.coordinator.task_executor import background_task_manager

            status = background_task_manager.get_task_status()
            return {"status": "healthy", "background_tasks": status, "timestamp": time.time()}
        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": time.time()}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        now = int(time.time())
        lines = [
            "# HELP salesboost_up Application up indicator",
            "# TYPE salesboost_up gauge",
            "salesboost_up 1",
            "# HELP salesboost_timestamp_seconds Current server timestamp",
            "# TYPE salesboost_timestamp_seconds gauge",
            f"salesboost_timestamp_seconds {now}",
            "# HELP salesboost_active_sessions Active session count",
            "# TYPE salesboost_active_sessions gauge",
            f"salesboost_active_sessions {get_session_count()}",
        ]
        return "\n".join(lines) + "\n"

    _register_api_routes(app)


def _register_api_routes(app: FastAPI) -> None:
    """Register API routers without failing the entire app on a missing module."""
    from importlib import import_module

    def _safe_include(module_path: str, prefix: str) -> None:
        try:
            module = import_module(module_path)
            router = getattr(module, "router")
            app.include_router(router, prefix=prefix)
            logger.info("Router registered: %s -> %s", module_path, prefix)
        except Exception as exc:
            logger.warning("Router skipped: %s (%s)", module_path, exc)

    _safe_include("api.endpoints.websocket", "/ws")
    _safe_include("api.v1.endpoints.sales_coach", "/api/v1")
    _safe_include("api.endpoints.sessions", "/api/v1/sessions")
    _safe_include("api.endpoints.scenarios", "/api/v1/scenarios")
    _safe_include("api.endpoints.reports", "/api/v1/reports")
    _safe_include("api.endpoints.knowledge", "/api/v1/knowledge")
    _safe_include("api.endpoints.profile", "/api/v1/profile")
    _safe_include("api.endpoints.auth", "/api/v1/auth")
    _safe_include("api.endpoints.admin", "/api/v1/admin")
    _safe_include("api.endpoints.mvp_suggest", "/api/v1/suggest")
    _safe_include("api.endpoints.mvp_compliance", "/api/v1/compliance")
    _safe_include("api.endpoints.mvp_feedback", "/api/v1/feedback")
    _safe_include("api.endpoints.assistant", "/api/v1/assistant")
    _safe_include("api.endpoints.feedback", "/api/v1/feedback")


def _configure_exception_handlers(app: FastAPI) -> None:
    """配置异常处理器"""

    @app.exception_handler(SalesBoostException)
    async def salesboost_exception_handler(request: Request, exc: SalesBoostException):
        """处理 SalesBoost 自定义异常"""
        return create_error_response(error_code=exc.error_code, message=exc.message, details=exc.details)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 FastAPI HTTP 异常"""
        return create_error_response(error_code="HTTP_ERROR", message=exc.detail, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return create_error_response(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details=str(exc) if app.debug else "Internal server error",
        )


app = create_application()


def run_server():
    """运行服务器"""
    import uvicorn

    settings = get_settings()
    app = create_application(settings)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
        reload=settings.DEBUG,
        access_log=True,
    )


if __name__ == "__main__":
    run_server()
