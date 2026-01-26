"""
NPC Generator V3 - 客户模拟器
封装现有 NPC agent，输出 NpcReply
"""
import logging
import time
from typing import Dict, Any, List, AsyncGenerator
from app.schemas.v3_agent_outputs import NpcReply
from app.schemas.fsm import FSMState
from app.schemas.agent_outputs import IntentGateOutput
from app.agents.roles.npc_agent import NPCAgent
from app.models.config_models import CustomerPersona
from app.core.llm_context import LLMCallContext
from app.services.model_gateway import ModelGateway
from app.services.model_gateway.budget import BudgetManager

logger = logging.getLogger(__name__)


class NPCGeneratorV3:
    """NPC Generator V3 - 客户模拟器"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
        persona: CustomerPersona,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        # 封装现有 NPC Agent
        self.npc_agent = NPCAgent(persona=persona)
    
    async def generate(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
        session_id: str,
        turn_number: int,
        retrieval_confidence: float,
    ) -> NpcReply:
        """
        生成 NPC 回复
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            fsm_state: FSM 状态
            intent_result: 意图识别结果
            session_id: 会话ID
            turn_number: 轮次号
            retrieval_confidence: 检索置信度（用于 HR-3）
            
        Returns:
            NpcReply
        """
        # HR-3: 低置信度禁止确定性强回答
        # 如果检索置信度低，需要在 prompt 中强调不确定性
        
        # 创建简单的 intent_result（NPC Agent 需要）
        from app.schemas.agent_outputs import IntentGateOutput
        intent_result = IntentGateOutput(
            detected_intent="general",
            is_aligned=True,
            alignment_reason="V3 simplified intent",
            detected_slots=[],
            missing_slots=[],
            confidence=0.8,
        )
        
        # 调用现有 NPC Agent
        llm_context = LLMCallContext(
            session_id=session_id,
            turn_number=turn_number,
            latency_mode="fast",
            budget_remaining=self.budget_manager.get_remaining_budget(session_id),
            budget_authorized=True,
        )
        npc_output = await self.npc_agent.generate_response(
            user_message=user_message,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            intent_result=intent_result,
            llm_context=llm_context,
        )
        
        # 转换为 NpcReply
        return NpcReply(
            response=npc_output.response,
            mood_before=npc_output.mood_before,
            mood_after=npc_output.mood_after,
            mood_change_reason=npc_output.mood_change_reason,
            expressed_signals=npc_output.expressed_signals,
            persona_consistency=npc_output.persona_consistency,
            stage_alignment=True,  # 由 NPC Agent 内部保证
        )

    async def generate_stream(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        intent_result: IntentGateOutput,
        session_id: str,
        turn_number: int,
        retrieval_confidence: float,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成 NPC 流式回复
        """
        # 创建简单的 intent_result（NPC Agent 需要）
        # 保持与 generate 方法一致的逻辑
        from app.schemas.agent_outputs import IntentGateOutput
        intent_result_v3 = IntentGateOutput(
            detected_intent="general",
            is_aligned=True,
            alignment_reason="V3 simplified intent",
            detected_slots=[],
            missing_slots=[],
            confidence=0.8,
        )
        
        llm_context = LLMCallContext(
            session_id=session_id,
            turn_number=turn_number,
            latency_mode="fast",
            budget_remaining=self.budget_manager.get_remaining_budget(session_id),
            budget_authorized=True,
        )
        
        async for chunk in self.npc_agent.process_stream(
            user_message=user_message,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            intent_result=intent_result_v3,
            llm_context=llm_context,
        ):
            if chunk["type"] == "token":
                yield chunk
            elif chunk["type"] == "result":
                npc_output = chunk["data"]
                reply = NpcReply(
                    response=npc_output.response,
                    mood_before=npc_output.mood_before,
                    mood_after=npc_output.mood_after,
                    mood_change_reason=npc_output.mood_change_reason,
                    expressed_signals=npc_output.expressed_signals,
                    persona_consistency=npc_output.persona_consistency,
                    stage_alignment=True,
                )
                yield {"type": "result", "data": reply}
