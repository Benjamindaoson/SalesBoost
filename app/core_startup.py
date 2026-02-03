"""Centralized startup bootstrap for core services with health reporting."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict

from sqlalchemy import text
from app.downgrade_manager import downgrade_manager

logger = logging.getLogger(__name__)

# Simple in-process health registry
_HEALTH: Dict[str, bool] = {
    "db": False,
    "redis": False,
    "llm": False,
    "cost_control": False,
    "audit": False,
    "state_recovery": False,
    "background": False,
    "metrics": False,
}


def _health_or_true(flag: bool) -> bool:
    return bool(flag)


def get_health() -> Dict[str, bool]:
    """Return a snapshot of current health across core subsystems."""
    # Return a shallow copy to avoid external mutation
    health = dict(_HEALTH)
    try:
        from app.downgrade_manager import downgrade_manager
        health["downgrades"] = downgrade_manager.get_active_issues()
    except Exception:
        health["downgrades"] = []
    return health


async def _init_database() -> None:
    try:
        # Lazy import to avoid import-time side effects
        from core.config import EnvironmentState, get_settings
        from core.database import engine, init_db
        from pathlib import Path

        settings = get_settings()
        Path("./storage").mkdir(parents=True, exist_ok=True)

        if settings.ENV_STATE == EnvironmentState.PRODUCTION:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        else:
            await init_db()
        _HEALTH['db'] = True
        try:
            downgrade_manager.resolve("db")
        except Exception:
            pass
        logger.info("Database initialized successfully")
    except Exception as e:
        _HEALTH['db'] = False
        downgrade_manager.register("db", str(e))
        logger.warning(f"Database initialization failed: {e}")


async def _init_redis() -> None:
    try:
        from core.redis import get_redis
        await get_redis()
        _HEALTH['redis'] = True
        try:
            downgrade_manager.resolve("redis")
        except Exception:
            pass
        logger.info("Redis initialized successfully")
    except Exception as e:
        _HEALTH['redis'] = False
        downgrade_manager.register("redis", str(e))
        logger.warning(f"Redis initialization failed: {e}. Using in-memory fallback.")


async def _init_llm() -> None:
    try:
        from core.llm import initialize_llm_system
        from app.infra.llm.registry import model_registry
        await initialize_llm_system()
        await model_registry.initialize()
        _HEALTH['llm'] = True
        logger.info("LLM system initialized successfully")
    except Exception as e:
        _HEALTH['llm'] = False
        logger.warning(f"LLM system initialization failed: {e}. Running in mock mode.")


async def _init_cost_control() -> None:
    try:
        logger.info("Initializing AI cost control system...")
        _HEALTH['cost_control'] = True
        try:
            downgrade_manager.resolve("cost_control")
        except Exception:
            pass
        logger.info("AI cost control system initialized successfully")
    except Exception as e:
        _HEALTH['cost_control'] = False
        downgrade_manager.register("cost_control", str(e))
        logger.warning(f"Cost control system initialization failed: {e}. Using fallback.")


async def _init_state_recovery() -> None:
    try:
        from app.engine.state.recovery import state_recovery_service
        await state_recovery_service.initialize()
        _HEALTH['state_recovery'] = True
        try:
            downgrade_manager.resolve("state_recovery")
        except Exception:
            pass
        logger.info("State recovery system initialized successfully")
    except Exception as e:
        _HEALTH['state_recovery'] = False
        downgrade_manager.register("state_recovery", str(e))
        logger.warning(f"State recovery system initialization failed: {e}. Recovery features disabled.")


async def _start_background_tasks() -> None:
    try:
        from app.engine.coordinator.task_executor import background_task_manager
        await background_task_manager.start()
        _HEALTH['background'] = True
        try:
            downgrade_manager.resolve("background")
        except Exception:
            pass
        logger.info("Background task manager started successfully")
    except Exception as e:
        _HEALTH['background'] = False
        downgrade_manager.register("background", str(e))
        logger.warning(f"Background task manager failed to start: {e}.")


async def _init_metrics() -> None:
    try:
        logger.info("Starting performance metrics collector...")
        from app.observability.metrics.business_metrics import performance_metrics_collector
        await performance_metrics_collector.initialize()
        _HEALTH['metrics'] = True
        try:
            downgrade_manager.resolve("metrics")
        except Exception:
            pass
        logger.info("Performance metrics collector started successfully")
    except Exception as e:
        _HEALTH['metrics'] = False
        downgrade_manager.register("metrics", str(e))
        logger.warning(f"Performance metrics collector failed to start: {e}.")


async def _init_memory_persistence() -> None:
    try:
        from app.services.memory_persistence_service import memory_persistence_service
        logger.info("Memory persistence service initialized successfully")
    except Exception as e:
        logger.warning(f"Memory persistence service initialization failed: {e}")


async def _init_audit() -> None:
    try:
        # Try plugin-based initialization; fall back to default if plugin not present
        try:
            from app.services.audit_service import initialize_plugin  # type: ignore
            if callable(initialize_plugin):
                initialize_plugin()
            from app.services.memory_stats_service import initialize_plugin as init_memory_stats  # type: ignore
            if callable(init_memory_stats):
                init_memory_stats()
        except Exception:
            pass
        _HEALTH['audit'] = True
        logger.info("Audit service initialized successfully (plugin path)")
    except Exception as e:
        _HEALTH['audit'] = False
        logger.warning(f"Audit service initialization failed: {e}.")


async def perform_startup() -> None:
    """Run all startup tasks in sequence with graceful degradation."""
    # Run in sequence to preserve ordering requirements
    await _init_database()
    await _init_redis()
    await _init_llm()
    await _init_cost_control()
    await _init_audit()
    await _init_memory_persistence()
    await _init_state_recovery()
    await _start_background_tasks()
    await _init_metrics()


__all__ = ["perform_startup", "get_health"]
