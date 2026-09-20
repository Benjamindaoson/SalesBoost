from app.engine.coordinator.recovery_hooks import RecoveryExecutionMixin


class DummyCoordinator(RecoveryExecutionMixin):
    pass


def test_tool_failure_recovery():
    coordinator = DummyCoordinator()
    result = coordinator.handle_execution_failure(
        TimeoutError("tool timeout"),
        "session-1",
        1,
        {},
    )

    assert result["failure_type"] == "tool_failure"
    assert result["action"] == "retry_tool"


def test_memory_failure_recovery():
    coordinator = DummyCoordinator()
    result = coordinator.handle_execution_failure(
        MemoryError("memory unavailable"),
        "session-1",
        2,
        {},
    )

    assert result["failure_type"] == "memory_failure"
    assert result["action"] == "continue_without_memory"


def test_unknown_failure_escalates():
    coordinator = DummyCoordinator()
    result = coordinator.handle_execution_failure(
        RuntimeError("unknown"),
        "session-1",
        3,
        {},
    )

    assert result["action"] == "human_escalation"
