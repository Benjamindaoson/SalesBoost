"""Strategy analyzer stub."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StrategyProfile:
    optimal_rate_by_situation: dict
    top_weakness_situations: list
    adoption_rate: float
    effective_adoption_rate: float
    recommended_focus: str


class StrategyAnalyzer:
    async def update_user_profile(self, db, user_id: str) -> StrategyProfile:
        return StrategyProfile(
            optimal_rate_by_situation={},
            top_weakness_situations=[],
            adoption_rate=0.0,
            effective_adoption_rate=0.0,
            recommended_focus="",
        )

    async def get_strategy_deviation_stats(self, db, user_id: str, limit: int = 20) -> list:
        return []
