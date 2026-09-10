"""Evaluation — multi-level pipeline."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select

from salesagent.core.constants import RewardDimension
from salesagent.models.db_models import EvaluationRecord, Message, Session


class SessionEvaluator:
    """Evaluates an entire session after it concludes."""

    def __init__(self, db: Any) -> None:
        self.db = db

    async def evaluate(self, session_id: str) -> dict[str, Any]:
        """Aggregate turn-level rewards and generate session summary report."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return {"error": "session not found"}

        # 1. Aggregate from all messages
        result = await self.db.execute(
            select(Message.reward_scores, Message.guard_events)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_index)
        )
        turns = result.all()

        if not turns:
            return {"status": "no data"}

        total_turns = len(turns)
        total_guard_events = sum(len(t.guard_events or []) for t in turns)

        # Average dimensions
        sums = {dim.value: 0.0 for dim in RewardDimension}
        sums["aggregate"] = 0.0
        count = 0

        for t in turns:
            scores = t.reward_scores or {}
            if "aggregate" in scores:
                for k, v in scores.items():
                    sums[k] = sums.get(k, 0.0) + float(v)
                count += 1

        averages = {k: round(v / count, 4) for k, v in sums.items()} if count > 0 else {}

        # 2. Extract final FSM stage
        final_stage = session.stage_history[-1] if session.stage_history else "unknown"

        report = {
            "session_id": session_id,
            "total_turns": total_turns,
            "final_stage": final_stage,
            "total_guard_events": total_guard_events,
            "average_scores": averages,
            "conversion": session.status in ("DEAL_CLOSED", "success"),
        }

        # 3. Store in EvaluationRecord
        record = EvaluationRecord(
            session_id=session_id,
            level="session",
            scores=averages,
            metadata_=report,
        )
        self.db.add(record)
        await self.db.commit()

        return report
