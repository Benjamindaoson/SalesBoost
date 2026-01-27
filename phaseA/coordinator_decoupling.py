from typing import Protocol, Any, Dict


class OrchestratorLike(Protocol):
    def process_turn(self, ctx: Dict[str, Any], input_msg: Any) -> Any:
        ...


class RecoveryLike(Protocol):
    def recover(self, session_id: str) -> Dict[str, Any]:
        ...


class TaskExecutorLike(Protocol):
    def execute(self, task: Dict[str, Any]) -> Any:
        ...


# Minimal decoupled adapters
class PhaseAInterfaces:
    def __init__(self, orchestrator: OrchestratorLike, recovery: RecoveryLike, executor: TaskExecutorLike):
        self.orchestrator = orchestrator
        self.recovery = recovery
        self.executor = executor

    def forward_turn(self, ctx: Dict[str, Any], input_msg: Any) -> Any:
        # Simple pass-through to orchestrator; in real plan, this can route through a contract layer
        return self.orchestrator.process_turn(ctx, input_msg)
