"""Recovery middleware for ProductionCoordinator integration.

Provides a small dependency-free adapter that can be called from coordinator
exception paths without coupling recovery policy implementation to workflow
engines.
"""

from dataclasses import dataclass
from typing import Any, Dict

from .policy import RecoveryAction, RecoveryPolicyEngine, FailureType


@dataclass
class RecoveryContext:
    session_id: str
    turn_number: int
    error: Exception
    state: Dict[str, Any]


class CoordinatorRecoveryMiddleware:
    """Translate runtime failures into deterministic recovery decisions."""

    def __init__(self, policy_engine: RecoveryPolicyEngine | None = None):
        self.policy_engine = policy_engine or RecoveryPolicyEngine()

    def handle(self, context: RecoveryContext) -> Dict[str, Any]:
        failure_type = self._classify(context.error)
        decision = self.policy_engine.decide(failure_type)

        return {
            "failure_type": failure_type.value,
            "action": decision.action.value,
            "recoverable": decision.recoverable,
            "session_id": context.session_id,
            "turn_number": context.turn_number,
        }

    def _classify(self, error: Exception) -> FailureType:
        name = error.__class__.__name__.lower()
        if "timeout" in name:
            return FailureType.TOOL_FAILURE
        if "memory" in name:
            return FailureType.MEMORY_FAILURE
        return FailureType.UNKNOWN
