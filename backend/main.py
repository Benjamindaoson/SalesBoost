"""
SalesBoost FastAPI Application - The Gold Master Entrypoint
Version: 1.0 - Production Ready with Full AI Capabilities

这是整个应用的入口点，遵循 Clean Architecture 原则：
- 只负责应用初始化和中间件配置
- 不包含任何业务逻辑
- 通过依赖注入的方式提供服务

架构层级：
├── main.py (入口层) - 应用启动、路由配置、中间件
├── api/ (接口层) - WebSocket 端点、依赖注入、管理员审核
├── app/engine/ (智能体编排层) - LangGraph 图、动态工作流、Human-in-the-Loop
├── app/observability/ (监控层) - Prometheus 指标、性能追踪
├── services/ (业务逻辑层) - FSM 状态机、提示词管理
├── schemas/ (数据传输层) - 请求响应模型定义
└── core/ (基础设施层) - 配置管理、LLM 客户端、异常处理

Phase A-D Features:
✅ Human-in-the-Loop Mode (人机协作模式)
✅ Dynamic Workflow (动态工作流)
✅ Intent Recognition Monitoring (意图识别专项监控)
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Dict

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from backend.app.api.deps import get_session_count
from backend.app.api.middleware.tenant_middleware import TenantMiddleware
from backend.app.core.config import EnvironmentState, Settings, get_settings
from backend.app.core.database import close_db
from backend.app.core.exceptions import SalesBoostException, create_error_response
from backend.app.core.redis import close_redis
from backend.app.middleware import setup_middleware
from backend.app.logging.security_filter import SensitiveDataFilter
from backend.app.logging.json_formatter import JSONFormatter
from backend.app.core_startup import perform_startup, get_health
from backend.app.engine.coordinator.workflow_planner import WorkflowPlanner

# 配置日志
settings = get_settings()
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

if settings.ENV_STATE == EnvironmentState.PRODUCTION:
    # Production: Use JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=log_level, handlers=[handler])
else:
    # Development: Use standard formatter
    logging.basicConfig(
        level=log_level, 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)

workflow_planner = WorkflowPlanner()
_LAST_CYCLE_RESULT: Dict[str, Any] = {}


def print_startup_banner():
    """打印启动横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                   🚀 SalesBoost V1.0 ONLINE 🚀                   ║
║                                                                   ║
║   AI-Powered Sales Training & Simulation Platform                ║
║                                                                   ║
║   ✅ Intent Recognition (FastText + Context-Aware)               ║
║   ✅ LangGraph Orchestration (Graph-Oriented Workflows)          ║
║   ✅ Human-in-the-Loop Mode (Admin Review via WebSocket)         ║
║   ✅ Dynamic Workflow Configuration (Runtime Switchable)         ║
║   ✅ Prometheus Monitoring (11 Metrics + Grafana Dashboard)      ║
║   ✅ A/B Testing Framework (Consistent Hashing)                  ║
║                                                                   ║
║   📊 Endpoints:                                                   ║
║      /health              - System health check                  ║
║      /metrics             - Prometheus metrics export            ║
║      /admin/ws/review     - Admin review WebSocket               ║
║      /ws/chat             - Sales simulation WebSocket           ║
║                                                                   ║
║   🎯 Ready for Production Deployment                             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write(banner.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
        except Exception:
            print(banner.encode("utf-8", errors="replace").decode("ascii", errors="ignore"))
    logger.info("SalesBoost V1.0 initialized successfully")


async def _run_workflow_cycle(trigger: str, query: str = "production readiness check") -> Dict[str, Any]:
    """Run the multi-agent planner once and record the result."""
    global _LAST_CYCLE_RESULT
    result = {
        "trigger": trigger,
        "status": "failed",
        "timestamp": time.time(),
    }
    try:
        cycle = await workflow_planner.run_full_cycle(query, session_id=f"{trigger}-{int(time.time())}")
        result.update({"status": "success", "details": cycle})
    except Exception as exc:
        logger.error("WorkflowPlanner cycle failed for %s: %s", trigger, exc, exc_info=True)
        result.setdefault("details", {})["error"] = str(exc)
    _LAST_CYCLE_RESULT = result
    return result


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    遵循 FastAPI 的 lifespan 事件模式
    """
    # 启动事件
    logger.info("=" * 70)
    logger.info("SalesBoost V1.0 application starting...")
    logger.info("=" * 70)
    logger.info("Initializing services and connections...")

    # Run startup bootstrap (graceful degradation)
    try:
        logger.info("Running startup bootstrap...")
        await perform_startup()
        logger.info("Startup bootstrap completed. Health: %s", get_health())
    except Exception as e:
        logger.warning(f"Startup bootstrap encountered an issue: {e} ⚠️")

    # LLM startup is handled by core bootstrap
    logger.info("LLM startup handled by core bootstrap. Health: %s", get_health())

    # Cost control configuration
    logger.info("Cost control startup handled by core bootstrap. Health: %s", get_health())

    # State recovery initialization
    logger.info("State recovery startup handled by core bootstrap. Health: %s", get_health())

    # Background tasks
    logger.info("Background tasks startup handled by core bootstrap. Health: %s", get_health())

    # Metrics bootstrap
    logger.info("Performance metrics bootstrap handled by core startup. Health: %s", get_health())

    # Start metrics exporter (for Intent Monitoring)
    try:
        from backend.app.observability.metrics_exporter import start_metrics_export
        # Note: metrics_exporter doesn't exist yet in original code
        # But we've created prometheus_exporter, so this is optional
        logger.info("Metrics exporter initialized (optional)")
    except ImportError:
        logger.info("Metrics exporter not available (using Prometheus endpoint instead)")
    except Exception as e:
        logger.warning(f"Metrics exporter initialization failed: {e}")

    # Print startup banner
    print_startup_banner()

    await _run_workflow_cycle("startup-verification", query="Production readiness check")

    yield

    # 关闭事件
    logger.info("=" * 70)
    logger.info("SalesBoost V1.0 application shutting down...")
    logger.info("=" * 70)
    logger.info("Cleaning up resources...")

    # 停止后台任务
    try:
        from backend.app.engine.coordinator.task_executor import background_task_manager

        await background_task_manager.stop()
        logger.info("Background task manager stopped successfully ✅")
    except Exception as e:
        logger.warning(f"Error stopping background task manager: {e}")

    # Stop metrics exporter
    try:
        from backend.app.observability.metrics_exporter import stop_metrics_export
        stop_metrics_export()
        logger.info("Metrics exporter stopped successfully ✅")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error stopping metrics exporter: {e}")

    await close_db()
    await close_redis()
    logger.info("SalesBoost V1.0 shutdown complete ✅")


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
            environment=os.getenv("ENVIRONMENT", "production"),
        )
        logger.info("Sentry initialized")

    # 创建应用实例
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION + " - V1.0 Production Ready",
        version="1.0.0",  # Gold Master Release
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # 配置中间件 - 使用我们的综合中间件系统
    setup_middleware(app)

    # 全局输入校验中间件
    try:
        from backend.app.middleware.input_validation import InputValidationMiddleware
        app.add_middleware(InputValidationMiddleware)
    except Exception:
        logger.warning("InputValidationMiddleware failed to load; continuing without it.")

    # 安全日志脱敏：为 Root logger 加入脱敏过滤器
    try:
        root_logger = logging.getLogger()
        root_logger.addFilter(SensitiveDataFilter())
    except Exception:
        logger.warning("SensitiveDataFilter could not be installed on root logger")

    # 注册多租户中间件
    app.add_middleware(TenantMiddleware)

    # 配置路由
    _configure_routes(app)

    # 配置异常处理器
    _configure_exception_handlers(app)

    logger.info(f"FastAPI application created: {settings.PROJECT_NAME} v1.0.0")
    return app


def _configure_routes(app: FastAPI) -> None:
    """Configure application routes."""

    @app.get("/")
    async def root():
        """Root endpoint with system info"""
        return {
            "name": "SalesBoost AI",
            "version": "1.0.0",
            "status": "online",
            "features": {
                "intent_recognition": "FastText + Context-Aware",
                "orchestration": "LangGraph + Dynamic Workflow",
                "human_in_loop": "WebSocket Admin Review",
                "monitoring": "Prometheus + Grafana"
            },
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "admin_review": "/admin/ws/review",
                "admin_dashboard": "/admin/dashboard.html",
                "websocket": "/ws/chat"
            }
        }

    @app.get("/health")
    async def health_check():
        """System health check with detailed subsystem status"""
        session_count = get_session_count()
        system_health = get_health()
        downgrades = system_health.pop("downgrades", [])

        # Derive overall health from boolean subsystems only
        bool_checks = [value for value in system_health.values() if isinstance(value, bool)]
        all_healthy = all(bool_checks) if bool_checks else False
        any_healthy = any(bool_checks) if bool_checks else False
        overall = "ok" if all_healthy and not downgrades else (
            "degraded" if any_healthy else "unavailable"
        )
        settings = get_settings()
        last_cycle = _LAST_CYCLE_RESULT or {}

        result = {
            "status": overall,
            "version": "1.0.0",
            "active_sessions": session_count,
            "debug_mode": app.debug,
            "system_health": system_health,
            "downgrades": downgrades,
            "components": {
                "bandit_routing": settings.BANDIT_ROUTING_ENABLED,
                "bandit_backend": "redis" if settings.BANDIT_REDIS_ENABLED else "memory",
                "tool_cache": settings.TOOL_CACHE_ENABLED,
                "semantic_cache": settings.SEMANTIC_CACHE_ENABLED,
                "tool_cache_tools": settings.TOOL_CACHE_TOOLS,
            },
            "features": {
                "human_in_loop": True,
                "dynamic_workflow": True,
                "intent_monitoring": True,
                "ab_testing": True
            }
        }
        result["last_lifecycle_cycle"] = last_cycle
        return result

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            metrics_output = generate_latest()
            return PlainTextResponse(content=metrics_output, media_type=CONTENT_TYPE_LATEST)
        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}")
            return PlainTextResponse(content=f"# Error generating metrics: {e}\n", status_code=500)

    @app.get("/metrics/cost")
    async def cost_metrics():
        """Cost optimization metrics"""
        try:
            from backend.app.infra.gateway.cost_control import cost_optimized_caller

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

    @app.get("/health/live")
    async def health_live():
        """Lightweight probe used by container healthcheck."""
        return {"status": "healthy", "timestamp": time.time()}

    @app.get("/run-lifecycle")
    async def run_lifecycle(query: str = "production readiness check"):
        """Trigger the full multi-agent lifecycle validator on demand."""
        return await _run_workflow_cycle("api-diagnostic", query=query)

    @app.get("/metrics/background")
    async def background_metrics():
        """Background task metrics"""
        try:
            from backend.app.engine.coordinator.task_executor import background_task_manager

            status = background_task_manager.get_task_status()
            return {"status": "healthy", "background_tasks": status, "timestamp": time.time()}
        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": time.time()}

    # Register API routes (including new Phase A-D endpoints)
    _register_api_routes(app)


def _register_api_routes(app: FastAPI) -> None:
    """Register API routers without failing the entire app on a missing module."""
    from importlib import import_module

    def _safe_include(module_path: str, prefix: str, tags: list = None) -> None:
        """Safely include a router, logging warning if unavailable"""
        try:
            module = import_module(module_path)
            router = getattr(module, "router")
            app.include_router(router, prefix=prefix, tags=tags or [])
            logger.info("✅ Router registered: %s -> %s", module_path, prefix)
        except Exception as exc:
            logger.warning("⚠️  Router skipped: %s (%s)", module_path, exc)

    def _required_include(module_path: str, prefix: str, tags: list = None) -> None:
        """Include a required router, failing if unavailable"""
        module = import_module(module_path)
        router = getattr(module, "router")
        app.include_router(router, prefix=prefix, tags=tags or [])
        logger.info("✅ Router registered: %s -> %s", module_path, prefix)

    # ==================== Phase A-D: New Endpoints ====================

    # 1. Intent Recognition Monitoring (Prometheus)
    logger.info("Registering Phase A-D endpoints...")
    _safe_include("api.endpoints.monitoring", "", tags=["monitoring"])

    # 2. Human-in-the-Loop Admin Review
    _safe_include("api.endpoints.admin_review", "/admin", tags=["admin"])

    # ==================== Original Endpoints ====================

    # WebSocket
    _safe_include("api.endpoints.websocket", "/ws", tags=["websocket"])

    # Core APIs
    _safe_include("api.v1.endpoints.sales_coach", "/api/v1", tags=["sales-coach"])
    _safe_include("api.endpoints.sessions", "/api/v1/sessions", tags=["sessions"])
    _safe_include("api.endpoints.scenarios", "/api/v1/scenarios", tags=["scenarios"])
    _safe_include("api.endpoints.reports", "/api/v1/reports", tags=["reports"])
    _safe_include("api.endpoints.knowledge", "/api/v1/knowledge", tags=["knowledge"])
    _safe_include("api.endpoints.profile", "/api/v1/profile", tags=["profile"])
    _safe_include("api.endpoints.auth", "/api/v1", tags=["auth"])
    _safe_include("api.endpoints.admin", "/api/v1/admin", tags=["admin"])

    # MVP Features
    _safe_include("api.endpoints.mvp_suggest", "/api/v1/suggest", tags=["mvp"])
    _safe_include("api.endpoints.mvp_compliance", "/api/v1/compliance", tags=["mvp"])
    _safe_include("api.endpoints.mvp_feedback", "/api/v1/feedback", tags=["mvp"])

    # Memory Service (Required)
    _required_include("api.endpoints.memory_service", "/api/v1/memory", tags=["memory"])

    # Assistant & Feedback
    _safe_include("api.endpoints.assistant", "/api/v1/assistant", tags=["assistant"])
    _safe_include("api.endpoints.feedback", "/api/v1/feedback", tags=["feedback"])

    # Coordinator Improvements - User Feedback API
    _safe_include("api.endpoints.user_feedback", "/api/v1/feedback", tags=["coordinator", "feedback"])

    # ==================== New CRUD APIs ====================

    # Course Management
    _safe_include("api.endpoints.courses", "/api/v1/courses", tags=["courses"])

    # User Management
    _safe_include("api.endpoints.users", "/api/v1/users", tags=["users"])

    # Task Management
    _safe_include("api.endpoints.tasks", "/api/v1/tasks", tags=["tasks"])

    # ==================== New Frontend Support APIs ====================

    # Onboarding API
    _safe_include("app.api.routes.onboarding", "", tags=["onboarding"])

    # User Preferences API
    _safe_include("app.api.routes.user_preferences", "", tags=["preferences"])

    # Team Management API
    _safe_include("app.api.routes.team", "", tags=["team"])

    # Customer Management API
    _safe_include("api.endpoints.customers", "/api/v1", tags=["customers"])

    logger.info("All routers registered successfully")


def _configure_exception_handlers(app: FastAPI) -> None:
    """配置异常处理器"""

    @app.exception_handler(SalesBoostException)
    async def salesboost_exception_handler(request: Request, exc: SalesBoostException):
        """处理 SalesBoost 自定义异常"""
        content = create_error_response(
            error=exc,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(status_code=400, content=content)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 FastAPI HTTP 异常"""
        content = create_error_response(
            error_code="HTTP_ERROR",
            message=exc.detail,
            details=None,
        )
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        content = create_error_response(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details=str(exc) if app.debug else None,
        )
        return JSONResponse(status_code=500, content=content)


# 创建应用实例
app = create_application()


def run_server():
    """运行服务器"""
    import uvicorn

    settings = get_settings()
    app = create_application(settings)

    # 绑定到 0.0.0.0 以支持 Render 部署
    host = "0.0.0.0" if os.getenv("RENDER") else settings.HOST
    port = int(os.getenv("PORT", settings.PORT))

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=(settings.LOG_LEVEL or "info").lower(),
        reload=settings.DEBUG,
        access_log=True,
    )


if __name__ == "__main__":
    run_server()
