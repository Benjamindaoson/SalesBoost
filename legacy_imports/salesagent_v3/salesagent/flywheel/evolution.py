"""Self-Evolution Loop."""
from __future__ import annotations

import json
from typing import Any

import structlog

log = structlog.get_logger()


class SelfEvolutionLoop:
    """
    Runs asynchronously after a session ends (e.g. DEAL_CLOSED or SESSION_ENDED).
    1. Extracts full conversation history
    2. Uses Critic Agent to review the entire trajectory
    3. Identifies effective/ineffective strategies
    4. Generates suggestions for the Prompt Registry / APO
    """

    def __init__(self, db: Any, gateway: Any) -> None:
        self.db = db
        self.gateway = gateway

    async def run(self, session_id: str) -> dict[str, Any]:
        """Run post-session reflection."""
        from sqlalchemy import select
        from salesagent.models.db_models import Message, Session

        # Load session and outcome
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return {"status": "error", "message": "Session not found"}

        # Load all messages
        result = await self.db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.turn_index)
        )
        messages = result.scalars().all()

        if len(messages) < 4:
            return {"status": "skipped", "message": "Conversation too short"}

        transcript = "\n".join(f"[{m.role}]: {m.content}" for m in messages)

        # Run review LLM
        from salesagent.reasoning.prompts import EVOLUTION_REVIEW_PROMPT
        prompt = EVOLUTION_REVIEW_PROMPT.format(
            conversation=transcript,
            outcome=session.status,
            stages=json.dumps(session.stage_history),
        )

        try:
            raw = await self.gateway.complete(
                task="evolution_review",
                system="You are an elite sales manager conducting a post-mortem review.",
                user=prompt,
                response_format="json_object",
            )
            review = json.loads(raw)

            # Store review in session metadata
            session.metadata_ = {**(session.metadata_ or {}), "evolution_review": review}
            await self.db.commit()

            log.info("Evolution loop completed", session_id=session_id)
            return {"status": "success", "review": review}

        except Exception as exc:
            log.warning("Evolution review failed", session_id=session_id, error=str(exc))
            return {"status": "error", "message": str(exc)}
