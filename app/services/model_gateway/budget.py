"""
Budget manager for model gateway.
"""
import logging
from typing import Dict, Optional

from app.services.model_gateway.schemas import BudgetConfig, ModelCall

logger = logging.getLogger(__name__)


class BudgetManager:
    """Budget manager enforcing session/turn limits."""

    def __init__(self, config: Optional[BudgetConfig] = None) -> None:
        self.config = config or BudgetConfig()
        self.session_budgets: Dict[str, float] = {}
        self.turn_budgets: Dict[str, float] = {}
        self.authorized_sessions: set[str] = set()

    def initialize_session(self, session_id: str) -> None:
        self.session_budgets[session_id] = 0.0
        self.turn_budgets[session_id] = 0.0
        self.authorized_sessions.add(session_id)
        logger.info(
            "Session budget initialized: %s, budget=$%.2f",
            session_id,
            self.config.per_session_budget,
        )

    def is_authorized(self, session_id: str) -> bool:
        return session_id in self.authorized_sessions

    def check_budget(self, session_id: str, estimated_cost: float, path: str = "fast") -> tuple[bool, float]:
        session_spent = self.session_budgets.get(session_id, 0.0)
        turn_spent = self.turn_budgets.get(session_id, 0.0)

        session_remaining = self.config.per_session_budget - session_spent
        if session_remaining < estimated_cost:
            logger.warning(
                "Session budget insufficient: %s, remaining=$%.4f, needed=$%.4f",
                session_id,
                session_remaining,
                estimated_cost,
            )
            return False, session_remaining

        path_budget = self.config.fast_path_budget if path == "fast" else self.config.slow_path_budget
        turn_remaining = path_budget - turn_spent
        if turn_remaining < estimated_cost:
            logger.warning(
                "Turn budget insufficient: %s, remaining=$%.4f, needed=$%.4f",
                session_id,
                turn_remaining,
                estimated_cost,
            )
            return False, turn_remaining

        return True, min(session_remaining, turn_remaining)

    def deduct_budget(self, session_id: str, cost: float, path: str = "fast") -> None:
        if session_id not in self.session_budgets:
            self.initialize_session(session_id)
        self.session_budgets[session_id] += cost
        self.turn_budgets[session_id] += cost
        logger.debug(
            "Budget deducted: %s, cost=$%.4f, session_spent=$%.4f, turn_spent=$%.4f",
            session_id,
            cost,
            self.session_budgets[session_id],
            self.turn_budgets[session_id],
        )

    def reset_turn_budget(self, session_id: str) -> None:
        self.turn_budgets[session_id] = 0.0

    def get_remaining_budget(self, session_id: str) -> float:
        session_spent = self.session_budgets.get(session_id, 0.0)
        return self.config.per_session_budget - session_spent

    def record_call(self, call: ModelCall) -> None:
        logger.info(
            "Model call: %s -> %s/%s, cost=$%.4f, latency=%.0fms",
            call.agent_type,
            call.provider,
            call.model,
            call.cost_usd,
            call.latency_ms,
        )
