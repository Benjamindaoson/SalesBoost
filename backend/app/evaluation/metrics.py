"""Evaluation metrics for autonomous sales agents."""


def intent_accuracy(expected: str, predicted: str) -> float:
    return 1.0 if expected == predicted else 0.0


def stage_accuracy(expected: str, predicted: str) -> float:
    return 1.0 if expected == predicted else 0.0


def tool_selection_accuracy(expected: list[str], selected: list[str]) -> float:
    if not expected:
        return 1.0
    return len(set(expected) & set(selected)) / len(expected)


def recovery_success(recovered: bool) -> float:
    return 1.0 if recovered else 0.0
