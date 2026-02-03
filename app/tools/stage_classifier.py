from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier
from app.infra.gateway.schemas import AgentType
from app.tools.base import BaseTool, ToolInputModel


class StageClassifierInput(ToolInputModel):
    message: Optional[str] = Field(None, description="Latest user message")
    history: Optional[List[Dict[str, str]]] = Field(
        None, description="Conversation history list of role/content dicts"
    )
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Extra context")


class StageClassifierTool(BaseTool):
    name = "stage.classify"
    description = "Classify sales stage from conversation context using AI-powered intent classification."
    args_schema = StageClassifierInput
    allowed_agents = {
        AgentType.COACH.value,
        AgentType.SESSION_DIRECTOR.value,
    }

    def __init__(self) -> None:
        # Upgraded: Use ContextAwareIntentClassifier instead of old IntentGateway
        self._classifier = ContextAwareIntentClassifier()
        super().__init__()

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = payload.get("message") or ""
        history = payload.get("history") or []
        if not message and history:
            message = history[-1].get("content", "")

        # Use upgraded classifier with context awareness
        result = await self._classifier.classify_with_context(
            message=message,
            history=history,
            fsm_state=payload.get("context") or {}
        )
        return {
            "intent": result.intent,
            "confidence": result.confidence,
            "stage": result.stage_suggestion or "unknown",
        }
