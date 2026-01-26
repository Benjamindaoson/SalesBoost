import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.retrieval_control_plane.planner import RetrievalPlanner
from app.services.retrieval_control_plane.executor import PlanExecutor
from app.services.retrieval_control_plane.judge import RetrievalJudge
from app.services.retrieval_protocol.plan import RetrievalPlan
from app.services.retrieval_protocol.evidence import EvidenceItem

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Plan -> Execute -> Judge -> (Refine) pipeline."""

    def __init__(self, executor: PlanExecutor):
        self.planner = RetrievalPlanner()
        self.executor = executor
        self.judge = RetrievalJudge()

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        max_refinements: int = 1,
    ) -> Tuple[List[EvidenceItem], RetrievalPlan, Dict[str, Any]]:
        context = context or {}
        constraints = constraints or {}

        plan = self.planner.plan(query, context=context, constraints=constraints)
        evidence = await self.executor.execute(plan)
        coverage = self.judge.evaluate(plan, evidence)

        refinements = 0
        refined_query = query
        while not coverage.met and refinements < max_refinements:
            refinements += 1
            refined_query = self._refine_query(refined_query, coverage.missing_types)
            logger.info("Retrieval refinement %s: %s", refinements, refined_query)
            plan = self.planner.plan(refined_query, context=context, constraints=constraints)
            evidence = await self.executor.execute(plan)
            coverage = self.judge.evaluate(plan, evidence)

        metadata = {
            "refinements": refinements,
            "coverage_met": coverage.met,
            "missing_types": coverage.missing_types,
            "evidence_count": coverage.evidence_count,
            "final_query": refined_query,
        }
        return evidence, plan, metadata

    def _refine_query(self, query: str, missing_types: List[str]) -> str:
        if not missing_types:
            return query
        suffix = " ".join(missing_types)
        return f"{query} {suffix}".strip()
