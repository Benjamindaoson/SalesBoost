"""Failure classification and recovery policy engine."""
from dataclasses import dataclass
from enum import Enum


class FailureType(str, Enum):
    TOOL_FAILURE = "tool_failure"
    RETRIEVAL_FAILURE = "retrieval_failure"
    MEMORY_FAILURE = "memory_failure"
    STATE_DRIFT = "state_drift"
    UNKNOWN = "unknown"


@dataclass
class RecoveryDecision:
    action: str
    retry: bool = False
    require_human: bool = False


class RecoveryPolicyEngine:
    """Maps execution failures to deterministic recovery actions."""

    def decide(self, failure: FailureType) -> RecoveryDecision:
        policies = {
            FailureType.TOOL_FAILURE: RecoveryDecision("retry_tool", retry=True),
            FailureType.RETRIEVAL_FAILURE: RecoveryDecision("fallback_with_disclosure"),
            FailureType.MEMORY_FAILURE: RecoveryDecision("continue_without_memory"),
            FailureType.STATE_DRIFT: RecoveryDecision("replan", retry=True),
            FailureType.UNKNOWN: RecoveryDecision("human_escalation", require_human=True),
        }
        return policies.get(failure, policies[FailureType.UNKNOWN])
