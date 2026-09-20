"""Evaluation data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationCase:
    """A deterministic agent evaluation scenario."""

    case_id: str
    category: str
    user_message: str
    expected_intent: str | None = None
    expected_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Evaluation output with measurable dimensions."""

    case_id: str
    passed: bool
    metrics: dict[str, float] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
