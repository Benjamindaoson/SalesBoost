"""Micro feedback stub."""
from __future__ import annotations

from schemas.mvp import MicroFeedbackItem, MicroFeedbackResponse


class MicroFeedbackService:
    async def generate_feedback(self, session_id: str, db=None) -> MicroFeedbackResponse:
        items = [
            MicroFeedbackItem(
                title="Clarify the need",
                what_happened="The user's need was not specific.",
                better_move="Ask a clarifying question first.",
                copyable_phrase="Could you share your main pain point?",
            )
        ]
        return MicroFeedbackResponse(feedback_items=items, session_id=session_id, total_turns=0)
