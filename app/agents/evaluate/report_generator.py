"""Report generator stub."""
from __future__ import annotations

from datetime import datetime

from schemas.reports import (
    RadarChartData,
    SessionSummary,
    TrainingReport,
)


class ReportService:
    async def generate_report(self, session, messages, include_turn_details: bool = False) -> TrainingReport:
        summary = SessionSummary(
            session_id=session.id,
            user_id=session.user_id,
            scenario_name="",
            persona_name="",
            started_at=session.started_at,
            completed_at=session.completed_at,
            duration_minutes=0,
            total_turns=session.total_turns,
            final_stage=session.final_stage or "unknown",
            completion_rate=0.0,
        )
        return TrainingReport(
            summary=summary,
            overall_score=session.final_score or 0.0,
            radar_chart=RadarChartData(labels=["integrity", "relevance", "correctness", "logic", "compliance"], values=[0, 0, 0, 0, 0]),
            dimension_scores={},
            dimension_feedback={},
            stage_performances=[],
            turn_details=None,
            top_strengths=[],
            top_improvements=[],
            recommended_focus="",
            generated_at=datetime.utcnow(),
        )
