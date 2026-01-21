"""
NPC Customer Simulator Agent
模拟真实客户，受 CustomerPersona 约束
❌ 绝不提供教练建议，只扮演客户
"""
import json
import logging
from dataclasses import dataclass
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


class NPCAgent(BaseAgent):
    """
    NPC 客户模拟器
    
    核心职责：
    - 模拟真实客户行为
    - 受 CustomerPersona（画像/情绪/性格）约束
    - 根据销售员表现动态调整情绪
    - 输出结构化的客户回复
    
    ❌ 严禁：
    - 提供任何教练建议
    - 跳出客户角色
    - 主动推进销售流程
    """
    
    def __init__(
        self,
        persona: Optional[CustomerPersona] = None,
        persona_profile: Optional[PersonaProfile] = None,
        **kwargs,
    ):
        """
        初始化 NPC Agent
        
        Args:
            persona: 客户人设配置
        """
        super().__init__(temperature=0.7, **kwargs)  # NPC 需要多样性
        self.persona = persona
        self.persona_profile = persona_profile

    def set_persona(self, persona_profile: PersonaProfile) -> None:
        self.persona_profile = persona_profile
    
    @property
    def system_prompt(self) -> str:
        persona_name = self.persona.name if self.persona else "Unknown"
        occupation = self.persona.occupation if self.persona else "Unknown"
        age_range = self.persona.age_range if self.persona else "Unknown"
        personality_traits = self.persona.personality_traits if self.persona else []
        buying_motivation = self.persona.buying_motivation if self.persona else "Unknown"
        main_concerns = self.persona.main_concerns if self.persona else "Unknown"
        communication_style = self.persona.communication_style if self.persona else "Unknown"
        decision_style = self.persona.decision_style if self.persona else "Unknown"
        industry = self.persona_profile.industry if self.persona_profile else occupation
        objection_style = self.persona_profile.objection_style if self.persona_profile else "Neutral"
        difficulty_level = self.persona_profile.difficulty_level if self.persona_profile else "Medium"
        return f"""You are a simulated customer in a sales training system. Stay in character.

[Customer Persona]
- Name: {persona_name}
- Industry: {industry}
- Objection Style: {objection_style}
- Difficulty Level: {difficulty_level}
- Role: {occupation}
- Age Range: {age_range}
- Personality Traits: {personality_traits}
- Buying Motivation: {buying_motivation}
- Main Concerns: {main_concerns}
- Communication Style: {communication_style}
- Decision Style: {decision_style}

[Rules]
1. Never provide coaching or sales advice.
2. Do not break character.
3. Adjust mood based on salesperson performance.
4. Reply naturally in 50-150 words.

[Output Requirements]
Return strict JSON with: response, mood_before, mood_after, mood_change_reason, expressed_signals, persona_consistency.
"""
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
        conversation_history = conversation_history or []
        history_str = self._format_conversation_history(conversation_history)
        stage_value = fsm_state.current_stage.value if fsm_state else "UNKNOWN"
        mood_value = fsm_state.npc_mood if fsm_state else 0.5
        turn_count = fsm_state.turn_count if fsm_state else len(conversation_history)
        intent_text = intent_result.detected_intent if intent_result else "unknown"
        intent_aligned = intent_result.is_aligned if intent_result else True

        user_prompt = f"""[Context]
- Stage: {stage_value}
- Mood: {mood_value:.2f}
- Turn: {turn_count}

[History]
{history_str}

[User]
{user_message}

[Intent]
- Detected: {intent_text}
- Aligned: {intent_aligned}

Generate the customer reply in JSON."""

        try:
            return await self.invoke_with_parser(user_prompt)
        except Exception as e:
            logger.error(f"NPC process failed: {e}")
            return NPCOutput(
                response="嗯，我需要再考虑一下。",
                mood_before=mood_value,
                mood_after=max(0.0, mood_value - 0.05),
                mood_change_reason="系统异常，默认轻微负面反应",
                expressed_signals=["观望"],
                persona_consistency=0.5,
            )

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
    ) -> NPCOutput:
        return await self.process(
            user_message=user_message,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            intent_result=intent_result,
        )

    async def generate_response_with_stream(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
        stream_callback: Any,
    ) -> NPCOutput:
        """
        生成客户回复 (支持流式)
        """
        # 构建对话历史字符串
        history_str = self._format_conversation_history(conversation_history)
        
        # 构建用户提示词
        user_prompt = f"""【当前状态】
- 销售阶段：{fsm_state.current_stage.value}
- 当前情绪值：{fsm_state.npc_mood:.2f}
- 对话轮次：{fsm_state.turn_count}

【对话历史】
{history_str}

【销售员最新输入】
{user_message}

【销售员意图分析】
- 检测意图：{intent_result.detected_intent}
- 是否对齐当前阶段：{intent_result.is_aligned}

请根据你的人设和当前情绪，生成客户回复。"""

        try:
            schema_instructions = self._build_schema_instructions()
            system_prompt = (
                f"{self.system_prompt}\n\n"
                f"你必须仅输出满足以下 JSON Schema 的 JSON（不要输出 Markdown/解释文字）：\n"
                f"{schema_instructions}"
            )
            
            # Invoke with stream
            raw_json = await self.invoke_with_stream(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                callback=stream_callback
            )
            
            # Parse final result
            json_str = self._extract_json(raw_json)
            data = json.loads(json_str)
            return self.output_schema.model_validate(data)
            
        except Exception as e:
            logger.error(f"NPC response stream generation failed: {e}")
            return NPCOutput(
                response="嗯，我需要再考虑一下。",
                mood_before=fsm_state.npc_mood,
                mood_after=max(0.0, fsm_state.npc_mood - 0.05),
                mood_change_reason="系统异常，默认轻微负面反应",
                expressed_signals=["观望"],
                persona_consistency=0.5,
            )
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史对话）"
        
        formatted = []
        for msg in history[-10:]:  # 最近 10 条
            if msg["role"] == "user":
                role = "销售员"
            elif msg["role"] == "system":
                role = "系统"
            else:
                role = "客户"
            formatted.append(f"{role}：{msg['content']}")
        
        return "\n".join(formatted)
    
    def update_persona_context(self, additional_context: Dict[str, Any]) -> None:
        """
        更新人设上下文（用于动态调整）
        
        Args:
            additional_context: 额外上下文信息
        """
        # 可以根据对话进展动态调整人设细节
        pass
