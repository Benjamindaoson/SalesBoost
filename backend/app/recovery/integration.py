"""Recovery integration layer.

Adapters can connect ProductionCoordinator failures to recovery policies.
"""
from .policy import FailureType, RecoveryPolicyEngine


class RecoveryIntegration:
    def __init__(self):
        self.engine = RecoveryPolicyEngine()

    def handle_failure(self, failure_type: str):
        try:
            kind = FailureType(failure_type)
        except ValueError:
            kind = FailureType.UNKNOWN
        return self.engine.recover(kind)
