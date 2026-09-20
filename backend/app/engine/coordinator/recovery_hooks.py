"""Recovery hooks for ProductionCoordinator runtime integration.

Keeps failure handling isolated from workflow engines.
"""

from typing import Any, Dict

from ...recovery.coordinator_recovery_middleware import (
    CoordinatorRecoveryMiddleware,
    RecoveryContext,
)


class RecoveryExecutionMixin:
    """Reusable recovery execution layer for coordinators."""

    def init_recovery(self) -> None:
        self.recovery_handler = CoordinatorRecoveryMiddleware()

    def handle_execution_failure(
        self,
        error: Exception,
        session_id: str,
        turn_number: int,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not hasattr(self, "recovery_handler"):
            self.init_recovery()

        return self.recovery_handler.handle(
            RecoveryContext(
                session_id=session_id,
                turn_number=turn_number,
                error=error,
                state=state,
            )
        )
