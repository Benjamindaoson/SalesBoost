"""Curriculum planner stub."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FocusItem:
    focus_situation: str
    focus_strategy: str
    stage: str


@dataclass
class CurriculumPlan:
    next_training_plan: List[FocusItem]
    expected_improvement: float
    reasoning: str


class CurriculumPlanner:
    async def _get_adoption_stats(self, db, user_id: str) -> dict:
        return {"adoption_rate": 0.0, "effective_adoption_rate": 0.0}

    async def generate_curriculum(self, db, user_id: str, max_focus_items: int = 1) -> CurriculumPlan:
        return CurriculumPlan(
            next_training_plan=[FocusItem(focus_situation="general", focus_strategy="probe", stage="opening")],
            expected_improvement=0.1,
            reasoning="stub",
        )
