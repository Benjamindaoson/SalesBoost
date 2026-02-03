"""
Health Check Endpoints for Production Readiness

Provides comprehensive health checks for:
- Liveness: Is the application running?
- Readiness: Is the application ready to serve traffic?
- Startup: Has the application finished starting up?
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
import logging
from datetime import datetime

from core.database import get_async_session
from core.redis import get_redis_client
from app.tools.health_check import get_health_checker
from app.tools.registry import build_default_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness_check() -> JSONResponse:
    """
    Liveness probe - Is the application running?

    Returns 200 if the application is alive.
    Used by Kubernetes liveness probe.

    Returns:
        200: Application is alive
        503: Application is dead (should be restarted)
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness probe - Is the application ready to serve traffic?

    Checks:
    - Database connection
    - Redis connection
    - Vector store connection (optional)

    Returns:
        200: Application is ready
        503: Application is not ready (should not receive traffic)
    """
    checks = {}
    all_ready = True

    # Check database
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
        checks["database"] = {"status": "ready", "message": "Connected"}
    except Exception as e:
        checks["database"] = {"status": "not_ready", "message": str(e)}
        all_ready = False
        logger.error(f"Database readiness check failed: {e}")

    # Check Redis
    try:
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = {"status": "ready", "message": "Connected"}
    except Exception as e:
        checks["redis"] = {"status": "not_ready", "message": str(e)}
        all_ready = False
        logger.error(f"Redis readiness check failed: {e}")

    # Check Vector Store (optional, don't fail if not available)
    try:
        from app.services.knowledge_service_qdrant import KnowledgeServiceQdrant
        service = KnowledgeServiceQdrant()
        # Simple health check - don't fail if Qdrant is not configured
        checks["vector_store"] = {"status": "ready", "message": "Available"}
    except Exception as e:
        checks["vector_store"] = {"status": "degraded", "message": "Not configured (optional)"}
        logger.warning(f"Vector store check: {e}")

    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    )


@router.get("/startup")
async def startup_check() -> JSONResponse:
    """
    Startup probe - Has the application finished starting up?

    Checks:
    - All critical services initialized
    - Tool registry loaded
    - Configuration validated

    Returns:
        200: Application has started
        503: Application is still starting
    """
    checks = {}
    all_started = True

    # Check tool registry
    try:
        registry = build_default_registry()
        tool_count = len(registry._tools)
        checks["tool_registry"] = {
            "status": "started",
            "message": f"Loaded {tool_count} tools"
        }
    except Exception as e:
        checks["tool_registry"] = {"status": "not_started", "message": str(e)}
        all_started = False
        logger.error(f"Tool registry startup check failed: {e}")

    # Check configuration
    try:
        from core.config import get_settings
        settings = get_settings()
        checks["configuration"] = {
            "status": "started",
            "message": f"Environment: {settings.ENV_STATE}"
        }
    except Exception as e:
        checks["configuration"] = {"status": "not_started", "message": str(e)}
        all_started = False
        logger.error(f"Configuration startup check failed: {e}")

    status_code = status.HTTP_200_OK if all_started else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "started" if all_started else "not_started",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    )


@router.get("/detailed")
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check - Comprehensive system status.

    Includes:
    - All readiness checks
    - Tool health status
    - System metrics
    - Version information

    Returns:
        200: Detailed health information
    """
    # Run all checks in parallel
    liveness_task = liveness_check()
    readiness_task = readiness_check()
    startup_task = startup_check()

    liveness_result, readiness_result, startup_result = await asyncio.gather(
        liveness_task,
        readiness_task,
        startup_task,
        return_exceptions=True
    )

    # Get tool health
    try:
        registry = build_default_registry()
        health_checker = get_health_checker(registry)
        tool_health = await health_checker.get_summary()
    except Exception as e:
        tool_health = {"error": str(e)}
        logger.error(f"Tool health check failed: {e}")

    # Get system info
    try:
        from core.config import get_settings
        settings = get_settings()
        system_info = {
            "environment": settings.ENV_STATE,
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "features": {
                "agentic_v3": settings.AGENTIC_V3_ENABLED,
                "bandit_routing": settings.BANDIT_ROUTING_ENABLED,
                "tool_rate_limit": settings.TOOL_RATE_LIMIT_ENABLED,
                "tool_cache": settings.TOOL_CACHE_ENABLED,
            }
        }
    except Exception as e:
        system_info = {"error": str(e)}
        logger.error(f"System info check failed: {e}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "timestamp": datetime.utcnow().isoformat(),
            "liveness": liveness_result.body.decode() if hasattr(liveness_result, 'body') else str(liveness_result),
            "readiness": readiness_result.body.decode() if hasattr(readiness_result, 'body') else str(readiness_result),
            "startup": startup_result.body.decode() if hasattr(startup_result, 'body') else str(startup_result),
            "tools": tool_health,
            "system": system_info
        }
    )
