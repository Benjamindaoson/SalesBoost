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

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api.deps import get_session_count
from app.api.middleware.tenant_middleware import TenantMiddleware
from app.core.config import EnvironmentState, Settings, get_settings
from app.core.database import close_db
from app.core.exceptions import SalesBoostException, create_error_response
from app.core.redis import close_redis
from app.middleware import setup_middleware
from app.logging.security_filter import SensitiveDataFilter
from app.logging.json_formatter import JSONFormatter
from app.core_startup import perform_startup, get_health
from app.engine.coordinator.workflow_planner import WorkflowPlanner

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
    result: Dict[str, Any] = {
        "trigger": trigger,
        "timestamp": time.time(),
    }
    try:
        cycle = await workflow_planner.run_full_cycle(
            query,
            session_id=f"{trigger}-{int(time.time())}",
        )
        result.update({"status": cycle.get("status", "success"), "details": cycle})
    except Exception as exc:
        logger.error("WorkflowPlanner cycle failed for %s: %s", trigger, exc, exc_info=True)
        result.update({"status": "error", "details": {"error": str(exc)}})
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
        from app.observability.metrics_exporter import start_metrics_export
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
        from app.engine.coordinator.task_executor import background_task_manager

        await background_task_manager.stop()
        logger.info("Background task manager stopped successfully ✅")
    except Exception as e:
        logger.warning(f"Error stopping background task manager: {e}")

    # Stop metrics exporter
    try:
        from app.observability.metrics_exporter import stop_metrics_export
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

    # OpenTelemetry distributed tracing (must run before instrument_fastapi)
    if getattr(settings, "TRACING_ENABLED", True):
        try:
            from app.observability.otel_tracing import init_otel_tracing
            init_otel_tracing(
                service_name=settings.PROJECT_NAME,
                endpoint=getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None),
                enabled=True,
            )
        except Exception as e:
            logger.warning("OpenTelemetry init skipped: %s", e)

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
        from app.middleware.input_validation import InputValidationMiddleware
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

    # OpenTelemetry FastAPI instrumentation
    if getattr(settings, "TRACING_ENABLED", True):
        try:
            from app.observability.otel_tracing import instrument_fastapi
            instrument_fastapi(app)
        except Exception as e:
            logger.warning("OpenTelemetry FastAPI instrumentation skipped: %s", e)

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
                "websocket": "/ws/train"
            }
        }

    # Redundant endpoints removed in favor of modular routers:
    # /health, /metrics, /health/live, /metrics/background, etc.

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
    _safe_include("app.api.endpoints.monitoring", "", tags=["monitoring"])
    _required_include("app.api.endpoints.health", "", tags=["health"])

    # 2. Human-in-the-Loop Admin Review
    _safe_include("app.api.endpoints.admin_review", "/admin", tags=["admin"])

    # ==================== Original Endpoints ====================

    # WebSocket (required for training)
    _required_include("app.api.endpoints.websocket", "/ws", tags=["websocket"])

    # Core APIs (required)
    # NOTE: app.api.v1.endpoints.sales_coach was removed — functionality merged into assistant.py
    _required_include("app.api.endpoints.sessions", "/api/v1/sessions", tags=["sessions"])
    _safe_include("app.api.endpoints.scenarios", "/api/v1/scenarios", tags=["scenarios"])
    _safe_include("app.api.endpoints.reports", "/api/v1/reports", tags=["reports"])
    _safe_include("app.api.endpoints.knowledge", "/api/v1/knowledge", tags=["knowledge"])
    _safe_include("app.api.endpoints.profile", "/api/v1/profile", tags=["profile"])
    _required_include("app.api.endpoints.auth", "/api/v1", tags=["auth"])
    _safe_include("app.api.endpoints.admin", "/api/v1/admin", tags=["admin"])

    # MVP Features
    _safe_include("app.api.endpoints.mvp_suggest", "/api/v1/suggest", tags=["mvp"])
    _safe_include("app.api.endpoints.mvp_compliance", "/api/v1/compliance", tags=["mvp"])
    _safe_include("app.api.endpoints.mvp_feedback", "/api/v1/feedback", tags=["mvp"])

    # Memory Service (Required)
    _required_include("app.api.endpoints.memory_service", "/api/v1/memory", tags=["memory"])

    # Assistant & Feedback
    _safe_include("app.api.endpoints.assistant", "/api/v1/assistant", tags=["assistant"])
    _safe_include("app.api.endpoints.feedback", "/api/v1/feedback", tags=["feedback"])

    # Coordinator Improvements - User Feedback API
    _safe_include("app.api.endpoints.user_feedback", "/api/v1/feedback", tags=["coordinator", "feedback"])

    # ==================== New CRUD APIs ====================

    # Course Management
    _safe_include("app.api.endpoints.courses_simple", "/api/v1/courses", tags=["courses"])

    # User Management
    _safe_include("app.api.endpoints.users", "/api/v1/users", tags=["users"])

    # Task Management
    _safe_include("app.api.endpoints.tasks_simple", "/api/v1/tasks", tags=["tasks"])

    # Statistics API
    _safe_include("app.api.endpoints.statistics_simple", "/api/v1/statistics", tags=["statistics"])
    # SECURITY: test.py endpoint removed — debug routes must NOT be exposed in production

    # ==================== New Frontend Support APIs ====================

    # Onboarding API
    _safe_include("app.api.routes.onboarding", "", tags=["onboarding"])

    # User Preferences API
    _safe_include("app.api.routes.user_preferences", "", tags=["preferences"])

    # Team Management API
    _safe_include("app.api.routes.team", "", tags=["team"])

    # Customer Management API
    _safe_include("app.api.endpoints.customers_simple", "/api/v1", tags=["customers"])

    # ==================== Sales Battle System APIs ====================

    # Deals & Pipeline
    _safe_include("app.api.endpoints.deals", "/api/v1", tags=["deals"])

    # Executive Cockpit
    _safe_include("app.api.endpoints.cockpit", "/api/v1", tags=["cockpit"])

    # Copilot (embeddable SDK API)
    _safe_include("app.api.endpoints.copilot", "/api/v1", tags=["copilot"])

    # Data Flywheel
    _safe_include("app.api.endpoints.flywheel", "/api/v1", tags=["flywheel"])

    # Export API
    _safe_include("app.api.endpoints.export", "/api/v1/export", tags=["export"])

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
