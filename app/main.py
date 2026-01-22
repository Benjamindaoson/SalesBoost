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
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.exceptions import SalesBoostException, create_error_response
from app.core.database import init_db, close_db
from app.core.redis import get_redis, close_redis
from app.api.deps import get_session_count
from app.api.middleware.tenant_middleware import TenantMiddleware

# API Routers
from app.api.endpoints import websocket as ws_router
from app.api.endpoints import sessions as sessions_router
from app.api.endpoints import scenarios as scenarios_router
from app.api.endpoints import reports as reports_router
from app.api.endpoints import knowledge as knowledge_router
from app.api.endpoints import profile as profile_router
from app.api.endpoints import auth as auth_router
from app.api.endpoints import admin as admin_router
from app.api.endpoints import mvp_suggest as mvp_suggest_router
from app.api.endpoints import mvp_compliance as mvp_compliance_router
from app.api.endpoints import mvp_feedback as mvp_feedback_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    try:
        from app.models.base import Base
        from app.core.database import engine
        async with engine.begin() as conn:
             await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        
        await init_db()
        logger.info("Database initialized successfully ✅")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # 初始化 Redis
    try:
        await get_redis()
        logger.info("Redis initialized successfully ✅")
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}. Using in-memory fallback ⚠️")

    # 初始化 LLM 系统
    try:
        from app.core.llm import initialize_llm_system
        await initialize_llm_system()
        logger.info("LLM system initialized successfully ✅")
    except Exception as e:
        logger.warning(f"LLM system initialization failed: {e}. Running in mock mode ⚠️")

    yield

    # 关闭事件
    logger.info("SalesBoost application shutting down...")
    logger.info("Cleaning up resources...")
    
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

    # 创建应用实例
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan
    )

    # 配置中间件
    _configure_middleware(app, settings)
    
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


def _configure_middleware(app: FastAPI, settings: Settings) -> None:
    """配置中间件"""

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 信任主机中间件（生产环境）
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # 生产环境请设置具体域名
        )


def _configure_routes(app: FastAPI) -> None:
    """配置路由"""

    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查"""
        session_count = get_session_count()

        return {
            "status": "healthy",
            "version": app.version,
            "active_sessions": session_count,
            "debug_mode": app.debug
        }

    # 根路径
    @app.get("/")
    async def root():
        """API 根路径"""
        return {
            "message": f"Welcome to {app.title}",
            "version": app.version,
            "docs": "/docs",
            "health": "/health",
            "websocket": "/ws/train?course_id=xxx&scenario_id=xxx&persona_id=xxx&user_id=xxx"
        }

    # 注册 API 路由
    app.include_router(ws_router.router, tags=["websocket"])
    app.include_router(auth_router.router, prefix="/api/v1", tags=["auth"])
    app.include_router(sessions_router.router, prefix="/api/v1", tags=["sessions"])
    app.include_router(scenarios_router.router, prefix="/api/v1", tags=["scenarios"])
    app.include_router(reports_router.router, prefix="/api/v1", tags=["reports"])
    app.include_router(knowledge_router.router, prefix="/api/v1/knowledge", tags=["knowledge"])
    app.include_router(profile_router.router, prefix="/api/v1/profile", tags=["profile"])
    app.include_router(admin_router.router, prefix="/api/v1", tags=["admin"])
    app.include_router(mvp_suggest_router.router, prefix="/api/v1", tags=["mvp"])
    app.include_router(mvp_compliance_router.router, prefix="/api/v1", tags=["mvp"])
    app.include_router(mvp_feedback_router.router, prefix="/api/v1", tags=["mvp"])


def _configure_exception_handlers(app: FastAPI) -> None:
    """配置异常处理器"""

    @app.exception_handler(SalesBoostException)
    async def salesboost_exception_handler(request: Request, exc: SalesBoostException):
        """处理自定义异常"""
        logger.error(f"SalesBoost exception: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=400,
            content=create_error_response(exc)
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理一般异常"""
        logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error occurred",
                    "details": {"error_type": type(exc).__name__} if app.debug else {}
                }
            }
        )


# 创建全局应用实例
app = create_application()


if __name__ == "__main__":
    # 直接运行时的配置
    import uvicorn
    settings = get_settings()

    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
