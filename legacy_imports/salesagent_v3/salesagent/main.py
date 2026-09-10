"""FastAPI application entrypoint for SalesAgent V3 Engine."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from salesagent.core.settings import settings
from salesagent.models.schemas import HealthResponse
from salesagent.utils.exceptions import SalesAgentError
from salesagent.utils.telemetry import setup_telemetry
from salesagent.dependencies import get_redis, get_db, close_db_engine, close_redis, _engine, AsyncSessionLocal
from salesagent.middleware.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from salesagent.observability.middleware import PrometheusMiddleware

log = structlog.get_logger()

_streams_consumer: Any | None = None


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _streams_consumer
    # Startup
    log.info("SalesAgent V3 starting up", version=settings.app_version)
    setup_telemetry()

    # Initialize distributed tracing
    from salesagent.observability.tracing import setup_tracing
    setup_tracing(app)
    log.info("Distributed tracing initialized")

    # Initialize error tracking
    from salesagent.observability.error_tracking import setup_sentry
    setup_sentry()
    if settings.sentry_dsn:
        log.info("Sentry error tracking initialized")

    # Test DB connection
    try:
        async with _engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        log.info("Database connected successfully")
    except Exception:
        # DB might not be available in dev without Docker
        log.warning("Database connection not available — running in limited mode")

    # Test Redis connection
    try:
        redis = await get_redis()
        await redis.ping()
        log.info("Redis connected successfully")

        # Start Redis Streams consumer
        from salesagent.flywheel.collector import StreamsConsumer
        async with AsyncSessionLocal() as db_session:
            _streams_consumer = StreamsConsumer(redis=redis, db=db_session)
            asyncio.create_task(_streams_consumer.start())
            log.info("Redis Streams consumer started")

        # Start WeChat workers
        from salesagent.integrations.workers import start_workers
        _wechat_workers = await start_workers()
        log.info("WeChat workers started")
    except Exception:
        log.warning("Redis not available — memory features disabled")

    log.info("SalesAgent V3 ready", host=settings.host, port=settings.port)
    yield

    # Shutdown
    if _streams_consumer:
        await _streams_consumer.stop()
        log.info("Redis Streams consumer stopped")
    await close_db_engine()
    await close_redis()
    log.info("SalesAgent V3 shutdown complete")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Autonomous Sales Agent Engine — Multi-Agent Decision System",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add Prometheus metrics middleware
    app.add_middleware(PrometheusMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ───────────────────────────────────────────
    @app.exception_handler(SalesAgentError)
    async def salesagent_exception_handler(request: Request, exc: SalesAgentError) -> JSONResponse:
        log.error("SalesAgent error", error_code=exc.error_code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": str(exc)},
        )

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        services: dict[str, str] = {}

        # Check DB
        try:
            async with _engine.begin() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            services["postgres"] = "healthy"
        except Exception:
            services["postgres"] = "unavailable"

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            services["redis"] = "healthy"
        except Exception:
            services["redis"] = "unavailable"

        services["mock_llm"] = "enabled" if settings.mock_llm else "disabled"
        services["shadow_mode"] = "enabled" if settings.shadow_mode_enabled else "disabled"

        return HealthResponse(
            status="ok",
            version=settings.app_version,
            services=services,
        )

    # ── Prometheus metrics endpoint ───────────────────────────────────────
    @app.get("/metrics", tags=["system"])
    async def metrics() -> Any:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── Mount routers ─────────────────────────────────────────────────────
    from salesagent.api.auth import router as auth_router
    from salesagent.api.sessions import router as sessions_router
    from salesagent.api.chat import router as chat_router
    from salesagent.api.knowledge import router as knowledge_router
    from salesagent.api.evaluation import router as evaluation_router
    from salesagent.api.prompts import router as prompts_router
    from salesagent.api.flywheel import router as flywheel_router
    from salesagent.api.analytics import router as analytics_router
    from salesagent.api.wechat import router as wechat_router
    from salesagent.api.onboarding import router as onboarding_router

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
    app.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])
    app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
    app.include_router(flywheel_router, prefix="/flywheel", tags=["flywheel"])
    app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
    app.include_router(wechat_router, prefix="/channels", tags=["channels"])
    app.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])

    return app


app = create_app()
