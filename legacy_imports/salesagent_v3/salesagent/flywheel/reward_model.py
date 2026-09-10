"""5-dimensional Reward Model."""
from __future__ import annotations

from typing import Any

import structlog

from salesagent.core.constants import REWARD_WEIGHTS, RewardDimension

log = structlog.get_logger()


class RewardModel:
    """
    Computes the 5-dimensional reward score for a turn.
    Dimensions:
        task_progress     — Did FSM advance? (0.25 weight)
        response_quality  — Critic Agent score (0.20 weight)
        compliance        — Guard events penalty (0.15 weight)
        user_engagement   — Response length + speed proxy (0.15 weight)
        conversion_signal — Final outcome backfill (0.25 weight)
    """

    async def score(
        self,
        fsm_advanced: bool = False,
        critic_quality_score: float = 0.5,
        guard_event_count: int = 0,
        user_message_length: int = 50,
        conversion_signal: float = 0.0,
    ) -> dict[str, float]:
        scores: dict[str, float] = {}

        # task_progress: 1.0 if FSM advanced, else 0.3
        scores[RewardDimension.TASK_PROGRESS] = 1.0 if fsm_advanced else 0.3

        # response_quality: from Critic Agent
        scores[RewardDimension.RESPONSE_QUALITY] = max(0.0, min(1.0, critic_quality_score))

        # compliance: penalize per guard event
        compliance_score = max(0.0, 1.0 - (0.25 * guard_event_count))
        scores[RewardDimension.COMPLIANCE] = compliance_score

        # user_engagement: heuristic from message length
        engagement = min(1.0, user_message_length / 200.0)
        scores[RewardDimension.USER_ENGAGEMENT] = engagement

        # conversion_signal: set later when outcome known (backfill)
        scores[RewardDimension.CONVERSION_SIGNAL] = conversion_signal

        # weighted aggregate
        total = sum(
            scores[dim] * REWARD_WEIGHTS[dim]
            for dim in RewardDimension
            if dim in scores
        )
        scores["aggregate"] = round(total, 4)

        return scores

    def backfill_conversion(
        self, scores: dict[str, float], converted: bool
    ) -> dict[str, float]:
        """Update conversion_signal after final outcome is known."""
        scores[RewardDimension.CONVERSION_SIGNAL] = 1.0 if converted else 0.0
        total = sum(
            scores.get(dim, 0.0) * REWARD_WEIGHTS[dim]
            for dim in RewardDimension
        )
        scores["aggregate"] = round(total, 4)
        return scores
