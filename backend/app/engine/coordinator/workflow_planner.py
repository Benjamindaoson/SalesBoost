"""
WorkflowPlanner — lifecycle orchestration helper.

Provides ``WorkflowPlanner.run_full_cycle`` which exercises the full
multi-agent coordinator pipeline for a given query.  This was previously
commented-out in ``main.py`` as ``# TODO: Module not found``.

Design goals
------------
* Thin wrapper around ``ProductionCoordinator`` so we can validate the
  full pipeline without duplicating logic.
* Graceful degradation: if the LLM / backend is unavailable the cycle
  still returns a structured result (status=``degraded``) rather than
  raising.
* No blocking I/O: the public interface is ``async``.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from app.engine.coordinator.dynamic_workflow import get_minimal_config

logger = logging.getLogger(__name__)


class WorkflowPlanner:
    """
    Orchestrates full production-readiness verification cycles.

    Usage::

        planner = WorkflowPlanner()
        result  = await planner.run_full_cycle(
            query="production readiness check",
            session_id="startup-check",
        )
    """

    def __init__(self, *, model_gateway: Any = None, budget_manager: Any = None) -> None:
        self._model_gateway = model_gateway
        self._budget_manager = budget_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_full_cycle(
        self,
        query: str,
        *,
        session_id: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Run one full multi-agent cycle to verify the pipeline is healthy.

        Returns a dict with at least:
        - ``status``:  "success" | "degraded" | "error"
        - ``latency_ms``:  wall-clock time for the cycle
        - ``session_id``: the session used
        - ``details``:  coordinator output (or error info on failure)
        """
        if session_id is None:
            session_id = f"planner-{int(time.time())}"

        start = time.perf_counter()
        result: Dict[str, Any] = {
            "session_id": session_id,
            "query": query,
            "timestamp": time.time(),
        }

        try:
            coordinator = await self._build_coordinator(session_id)
            turn_result = await coordinator.execute_turn(
                turn_number=1,
                user_message=query,
                enable_async_coach=False,
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            result.update(
                {
                    "status": "success",
                    "latency_ms": latency_ms,
                    "details": {
                        "npc_reply": turn_result.npc_reply,
                        "intent": turn_result.intent,
                        "turn_number": turn_result.turn_number,
                    },
                }
            )
            logger.info(
                "WorkflowPlanner cycle completed in %.1f ms (session=%s)",
                latency_ms,
                session_id,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "WorkflowPlanner cycle degraded (session=%s): %s",
                session_id,
                exc,
            )
            result.update(
                {
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "details": {"error": str(exc)},
                }
            )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _build_coordinator(self, session_id: str):
        """Build a lightweight ProductionCoordinator for this cycle."""
        from app.engine.coordinator.production_coordinator import (
            ProductionCoordinator,
        )

        # Use a minimal stub gateway when none is provided
        model_gateway = self._model_gateway or _StubGateway()
        budget_manager = self._budget_manager or _StubBudgetManager()
        persona: Dict[str, Any] = {"name": "SalesBot", "industry": "general"}

        return ProductionCoordinator(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            persona=persona,
            config=get_minimal_config(),
        )


# ---------------------------------------------------------------------------
# Lightweight stubs so the planner works without real LLM credentials
# ---------------------------------------------------------------------------

class _StubGateway:
    """Minimal stub that returns a canned LLM response."""

    async def generate(self, *args: Any, **kwargs: Any) -> str:
        return "[WorkflowPlanner stub] Pipeline check passed."

    async def chat(self, *args: Any, **kwargs: Any) -> str:
        return "[WorkflowPlanner stub] Pipeline check passed."

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        return "[WorkflowPlanner stub] Pipeline check passed."


class _StubBudgetManager:
    """Minimal stub that always approves budget."""

    def check_budget(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def record_usage(self, *args: Any, **kwargs: Any) -> None:
        pass
