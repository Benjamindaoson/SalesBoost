"""
NPC Customer Simulator Agent.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from app.agents.roles.base import BaseAgent
from app.core.llm_context import LLMCallContext
from app.models.config_models import CustomerPersona
from app.schemas.agent_outputs import IntentGateOutput, NPCOutput
from app.schemas.fsm import FSMState

logger = logging.getLogger(__name__)


@dataclass
class PersonaProfile:
    name: str
    industry: str
    objection_style: str
    difficulty_level: str


@dataclass
class NPCInternalState:
    mood: float = 0.5
    trust_level: float = 0.3
    patience: int = 3
    hidden_concerns: List[str] = field(default_factory=list)
    last_tactic_detected: Optional[str] = None


class NPCAgent(BaseAgent):
    """NPC simulator with internal state."""

    AGENT_TYPE = "npc"

    def __init__(
        self,
        persona: Optional[CustomerPersona] = None,
        persona_profile: Optional[PersonaProfile] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(temperature=0.7, **kwargs)
        self.persona = persona
        self.persona_profile = persona_profile
        self.internal_state = NPCInternalState()

    def set_persona(self, persona_profile: PersonaProfile) -> None:
        self.persona_profile = persona_profile

    @property
    def system_prompt(self) -> str:
        base_prompt = (
            "You are a simulated customer in a sales training system. Stay in character.\n"
            "[Rules]\n"
            "1. Never provide coaching or sales advice.\n"
            "2. Do not break character.\n"
            "3. Adjust mood based on salesperson performance.\n"
            "4. Reply naturally in 50-150 words.\n\n"
            "[Output Format]\n"
            "1. First, output your response text to the user directly.\n"
            "2. Then, output a separator line: ###METADATA###\n"
            "3. Finally, output the JSON metadata object.\n\n"
            "[Metadata Schema]\n"
            "Return strict JSON with: mood_before, mood_after, mood_change_reason, "
            "expressed_signals, persona_consistency."
        )
        if self.persona and self.persona_profile:
            return (
                base_prompt
                + f"""
[Customer Persona]
- Name: {self.persona.name}
- Industry: {self.persona_profile.industry}
- Objection Style: {self.persona_profile.objection_style}
- Difficulty Level: {self.persona_profile.difficulty_level}
- Role: {self.persona.occupation}
- Traits: {self.persona.personality_traits}
"""
            )
        return base_prompt

    @property
    def output_schema(self) -> Type[BaseModel]:
        return NPCOutput

    async def process(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        fsm_state: Optional[FSMState] = None,
        intent_result: Optional[IntentGateOutput] = None,
        llm_context: Optional[LLMCallContext] = None,
    ) -> NPCOutput:
        self._update_internal_state(user_message, intent_result)
        conversation_history = conversation_history or []
        history_str = self._format_conversation_history(conversation_history)
        user_prompt = self._build_prompt(fsm_state, intent_result, history_str, user_message)

        try:
            output = await self.invoke_with_parser(user_prompt, llm_context=llm_context)
            return output
        except Exception as exc:
            logger.error("NPC process failed: %s", exc)
            return self._create_fallback_response()

    async def process_stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        fsm_state: Optional[FSMState] = None,
        intent_result: Optional[IntentGateOutput] = None,
        llm_context: Optional[LLMCallContext] = None,
    ):
        self._update_internal_state(user_message, intent_result)
        conversation_history = conversation_history or []
        history_str = self._format_conversation_history(conversation_history)
        user_prompt = self._build_prompt(fsm_state, intent_result, history_str, user_message)

        try:
            async for chunk in self.invoke_stream_with_parser(user_prompt, llm_context=llm_context):
                yield chunk
        except Exception as exc:
            logger.error("NPC process stream failed: %s", exc)
            raise exc

    def _build_prompt(self, fsm_state, intent_result, history_str, user_message) -> str:
        return (
            "[Context]\n"
            f"- Stage: {fsm_state.current_stage.value if fsm_state else 'UNKNOWN'}\n"
            f"- Mood: {self.internal_state.mood:.2f} (Internal)\n"
            f"- Trust: {self.internal_state.trust_level:.2f} (Internal)\n"
            f"- Patience: {self.internal_state.patience}\n"
            f"- Last Intent Detected: {intent_result.detected_intent if intent_result else 'None'}\n\n"
            "[History]\n"
            f"{history_str}\n\n"
            "[User Input]\n"
            f"{user_message}\n\n"
            "Generate the customer reply in JSON."
        )

    def _create_fallback_response(self) -> NPCOutput:
        return NPCOutput(
            response="Let me think about that for a moment.",
            mood_before=self.internal_state.mood,
            mood_after=max(0.0, self.internal_state.mood - 0.05),
            mood_change_reason="system_error",
            expressed_signals=["hesitation"],
            persona_consistency=0.5,
        )

    def _update_internal_state(self, user_message: str, intent_result: Optional[IntentGateOutput]) -> None:
        if not intent_result:
            return
        if intent_result.is_aligned:
            self.internal_state.trust_level = min(1.0, self.internal_state.trust_level + 0.1)
            self.internal_state.mood = min(1.0, self.internal_state.mood + 0.05)
        else:
            self.internal_state.patience = max(0, self.internal_state.patience - 1)
            self.internal_state.mood = max(0.0, self.internal_state.mood - 0.1)

    async def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        fsm_state: Optional[FSMState] = None,
        intent_result: Optional[IntentGateOutput] = None,
        llm_context: Optional[LLMCallContext] = None,
    ) -> NPCOutput:
        return await self.process(user_message, conversation_history, fsm_state, intent_result, llm_context=llm_context)

    async def generate_response_with_stream(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
        stream_callback: Any,
        llm_context: Optional[LLMCallContext] = None,
    ) -> NPCOutput:
        result = await self.generate_response(
            user_message=user_message,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            intent_result=intent_result,
            llm_context=llm_context,
        )

        event_id = str(uuid.uuid4())
        chunks = self._split_chunks(result.response, chunk_size=120)
        for index, chunk in enumerate(chunks):
            payload = {
                "type": "npc_chunk",
                "event_id": event_id,
                "sequence": index,
                "is_final": index == len(chunks) - 1,
                "content": chunk,
            }
            try:
                if asyncio.iscoroutinefunction(stream_callback):
                    await stream_callback(payload)
                else:
                    stream_callback(payload)
            except Exception as exc:
                logger.warning("Stream callback failed: %s", exc)
                break
        return result

    def _split_chunks(self, text: str, chunk_size: int = 120) -> List[str]:
        if not text:
            return [""]
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "(no history)"
        formatted = []
        for msg in history[-10:]:
            role = "seller" if msg["role"] == "user" else ("system" if msg["role"] == "system" else "customer")
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def update_persona_context(self, additional_context: Dict[str, Any]) -> None:
        pass
