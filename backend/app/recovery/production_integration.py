"""Production recovery integration helpers.

Provides a small adapter between agent runtime failures and the
RecoveryPolicyEngine. The adapter is intentionally dependency-free so it can
be injected into ProductionCoordinator without coupling the runtime to a
specific recovery implementation.
"""

from dataclasses import dataclass
from typing import Any, Dict

from .policy import FailureType, RecoveryPolicyEngine


@dataclass
class RecoveryContext:
    agent: str
    state: Dict[str, Any]
    error: Exception


class ProductionRecoveryHandler:
    def __init__(self, policy_engine: RecoveryPolicyEngine | None = None):
        self.policy_engine = policy_engine or RecoveryPolicyEngine()

    def classify_and_recover(self, context: RecoveryContext) -> Dict[str, Any]:
        message = str(context.error).lower()

        if "timeout" in message or "connection" in message:
            failure = FailureType.TOOL_FAILURE
        elif "memory" in message:
            failure = FailureType.MEMORY_FAILURE
        elif "retriev" in message:
            failure = FailureType.RETRIEVAL_FAILURE
        else:
            failure = FailureType.UNKNOWN

        decision = self.policy_engine.decide(failure)
        return {
            "agent": context.agent,
            "failure": failure.value,
            "action": decision.action.value,
            "recoverable": decision.recoverable,
        }
