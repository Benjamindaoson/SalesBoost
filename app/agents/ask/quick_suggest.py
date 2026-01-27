"""Quick suggest stub."""
from __future__ import annotations

from schemas.mvp import IntentLabel, QuickSuggestResponse


class QuickSuggestService:
    async def generate_suggest(self, session_id: str, last_user_msg: str, conversation_history=None, fsm_state=None, optional_context=None) -> QuickSuggestResponse:
        return QuickSuggestResponse(
            intent_label=IntentLabel.OTHER,
            suggested_reply="Got it. Could you share more details about your needs?",
            alt_replies=[
                "Could you share your main goal?",
                "Which part matters most to you?",
            ],
            confidence=0.6,
            evidence=None,
        )
