"""Memory evaluation utilities for Autonomous Sales Agent.

Checks whether stored memories are retrieved and used correctly.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryEvaluationCase:
    case_id: str
    initial_memory: dict[str, Any]
    later_query: str
    expected_facts: list[str]


@dataclass
class MemoryEvaluationResult:
    case_id: str
    retrieved: list[str]
    passed: bool


def evaluate_memory(case: MemoryEvaluationCase, retrieved_memory: list[str]) -> MemoryEvaluationResult:
    matched = all(fact in " ".join(retrieved_memory) for fact in case.expected_facts)
    return MemoryEvaluationResult(
        case_id=case.case_id,
        retrieved=retrieved_memory,
        passed=matched,
    )
