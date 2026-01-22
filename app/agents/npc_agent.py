"""
NPC Customer Simulator Agent
模拟真实客户，受 CustomerPersona 约束
❌ 绝不提供教练建议，只扮演客户
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agent_outputs import NPCOutput, IntentGateOutput
from app.schemas.fsm import FSMState, SalesStage
from app.models.config_models import CustomerPersona

logger = logging.getLogger(__name__)

@dataclass
class PersonaProfile:
    name: str
    industry: str
    objection_style: str
    difficulty_level: str

@dataclass
class NPCInternalState:
    """Internal Cognitive State of the NPC (Dimension 5)"""
    mood: float = 0.5
    trust_level: float = 0.3
    patience: int = 3
    hidden_concerns: List[str] = field(default_factory=list)
    last_tactic_detected: Optional[str] = None

class NPCAgent(BaseAgent):
    """
    NPC 客户模拟器 (Stateful Agent)
    """
    
    def __init__(
        self,
        persona: Optional[CustomerPersona] = None,
        persona_profile: Optional[PersonaProfile] = None,
        **kwargs,
    ):
        super().__init__(temperature=0.7, **kwargs)
        self.persona = persona
        self.persona_profile = persona_profile
        # Initialize internal cognitive state
        self.internal_state = NPCInternalState()

    def set_persona(self, persona_profile: PersonaProfile) -> None:
        self.persona_profile = persona_profile
    
    @property
    def system_prompt(self) -> str:
        # Optimized for Prefix Caching (Dimension 4)
        # Static instructions first
        base_prompt = """You are a simulated customer in a sales training system. Stay in character.
[Rules]
1. Never provide coaching or sales advice.
2. Do not break character.
3. Adjust mood based on salesperson performance.
4. Reply naturally in 50-150 words.

[Output Requirements]
Return strict JSON with: response, mood_before, mood_after, mood_change_reason, expressed_signals, persona_consistency.
"""
        # Dynamic Persona info follows
        if self.persona and self.persona_profile:
             return base_prompt + f"""
[Customer Persona]
- Name: {self.persona.name}
- Industry: {self.persona_profile.industry}
- Objection Style: {self.persona_profile.objection_style}
- Difficulty Level: {self.persona_profile.difficulty_level}
- Role: {self.persona.occupation}
- Traits: {self.persona.personality_traits}
"""
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
    ) -> NPCOutput:
        
        # 1. Update Internal State (Cognitive Step)
        self._update_internal_state(user_message, intent_result)
        
        # 2. Construct Prompt
        conversation_history = conversation_history or []
        history_str = self._format_conversation_history(conversation_history)
        
        # Use FSM State + Internal Cognitive State
        user_prompt = f"""[Context]
- Stage: {fsm_state.current_stage.value if fsm_state else "UNKNOWN"}
- Mood: {self.internal_state.mood:.2f} (Internal)
- Trust: {self.internal_state.trust_level:.2f} (Internal)
- Patience: {self.internal_state.patience}
- Last Intent Detected: {intent_result.detected_intent if intent_result else "None"}

[History]
{history_str}

[User Input]
{user_message}

Generate the customer reply in JSON."""

        try:
            output = await self.invoke_with_parser(user_prompt)
            # Sync back to FSM State if needed (though FSM usually manages its own)
            return output
        except Exception as e:
            logger.error(f"NPC process failed: {e}")
            return NPCOutput(
                response="嗯，我需要再考虑一下。",
                mood_before=self.internal_state.mood,
                mood_after=max(0.0, self.internal_state.mood - 0.05),
                mood_change_reason="系统异常",
                expressed_signals=["观望"],
                persona_consistency=0.5,
            )

    def _update_internal_state(self, user_message: str, intent_result: Optional[IntentGateOutput]):
        """Simple rule-based cognitive update (Dimension 5)"""
        if not intent_result:
            return
            
        # Example: If user intent matches stage, trust increases
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
    ) -> NPCOutput:
        """Alias for process"""
        return await self.process(user_message, conversation_history, fsm_state, intent_result)

    async def generate_response_with_stream(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
        stream_callback: Any,
    ) -> NPCOutput:
        # (Stream implementation similar to process, omitted for brevity but follows same pattern)
        # Reusing the simple invoke for now to ensure state consistency
        return await self.process(user_message, conversation_history, fsm_state, intent_result)

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史对话）"
        
        formatted = []
        for msg in history[-10:]:  # Prefix Caching optimization: Fixed window
            role = "销售员" if msg["role"] == "user" else ("系统" if msg["role"] == "system" else "客户")
            formatted.append(f"{role}：{msg['content']}")
        return "\n".join(formatted)

    def update_persona_context(self, additional_context: Dict[str, Any]) -> None:
        pass
