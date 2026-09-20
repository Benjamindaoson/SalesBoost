"""Agent evaluation runner.

Provides a lightweight harness for replaying sales scenarios against
ProductionCoordinator-compatible agents.
"""
from typing import Any, Awaitable, Callable, Iterable

from .models import EvaluationCase, EvaluationResult


class AgentEvaluationRunner:
    def __init__(self, executor: Callable[[EvaluationCase], Awaitable[Any]]):
        self.executor = executor

    async def run_case(self, case: EvaluationCase) -> EvaluationResult:
        try:
            output = await self.executor(case)
            return EvaluationResult(
                case_id=case.case_id,
                passed=True,
                output=output,
            )
        except Exception as exc:
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                error=str(exc),
            )

    async def run(self, cases: Iterable[EvaluationCase]):
        results = []
        for case in cases:
            results.append(await self.run_case(case))
        return results
