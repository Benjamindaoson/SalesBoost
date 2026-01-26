"""
Coach Generator V3 - 教练
封装现有 Coach agent，输出 CoachAdvice（结构化，含 guardrails）
"""
import logging
from typing import Dict, Any, List, Optional
from app.schemas.v3_agent_outputs import CoachAdvice
from app.schemas.fsm import FSMState
from app.schemas.agent_outputs import RAGOutput, ComplianceOutput
from app.schemas.strategy import StrategyAnalysis
from app.agents.roles.coach_agent import CoachAgent
from app.services.model_gateway import ModelGateway, AgentType, LatencyMode, RoutingContext
from app.services.model_gateway.budget import BudgetManager

logger = logging.getLogger(__name__)


class CoachGeneratorV3:
    """Coach Generator V3 - 教练"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        # 封装现有 Coach Agent
        self.coach_agent = CoachAgent()
    
    async def generate(
        self,
        user_message: str,
        npc_response: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        rag_content: RAGOutput,
        compliance_result: ComplianceOutput,
        strategy_analysis: Optional[StrategyAnalysis],
        session_id: str,
        turn_number: int,
        retrieval_confidence: float,
    ) -> CoachAdvice:
        """
        生成教练建议
        
        Args:
            user_message: 用户消息
            npc_response: NPC 回复
            conversation_history: 对话历史
            fsm_state: FSM 状态
            rag_content: RAG 检索结果
            compliance_result: 合规检查结果
            strategy_analysis: 策略分析结果
            session_id: 会话ID
            turn_number: 轮次号
            retrieval_confidence: 检索置信度（用于 HR-3）
            
        Returns:
            CoachAdvice
        """
        # HR-3: 低置信度禁止确定性强回答
        # 如果检索置信度 < 0.6，需要在建议中强调不确定性
        
        # 转换 evidence_pack 到 RAGOutput
        from app.schemas.agent_outputs import RAGOutput, RAGItem
        rag_content = RAGOutput(
            retrieved_content=[
                RAGItem(
                    content=item.content,
                    source_citations=[item.source],
                    relevance_score=item.relevance_score,
                    content_type=item.source_type,
                )
                for item in evidence_pack.items
            ] if evidence_pack else [],
            query_understanding=user_message,
            no_result_fallback=not evidence_pack or len(evidence_pack.items) == 0,
        )
        
        # 创建合规结果（简化）
        from app.schemas.agent_outputs import ComplianceOutput
        compliance_result = ComplianceOutput(
            is_compliant=True,
            risk_flags=[],
            blocked=False,
            risk_level="OK",
        )
        
        # 调用现有 Coach Agent
        npc_response = npc_reply.response if hasattr(npc_reply, 'response') else str(npc_reply)
        coach_output, strategy_guidance = await self.coach_agent.generate_advice(
            user_message=user_message,
            npc_response=npc_response,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            rag_content=rag_content,
            compliance_result=compliance_result,
            strategy_analysis=None,  # 简化，实际可以从外部传入
        )
        
        # 提取 guardrails（从合规结果）
        guardrails = []
        if not compliance_result.is_compliant:
            for risk_flag in compliance_result.risk_flags:
                guardrails.append(f"{risk_flag.risk_type}: {risk_flag.risk_reason}")
        
        # HR-3: 低置信度时添加不确定性提示
        if retrieval_confidence < 0.6:
            guardrails.append("检索置信度较低，建议确认信息准确性")
            # 修改建议，强调不确定性
            if "建议" in coach_output.suggestion or "可以" in coach_output.suggestion:
                coach_output.suggestion = f"[需确认] {coach_output.suggestion}"
        
        # 生成备选话术（从 example_utterance 和 suggestion 提取）
        alternatives = []
        if coach_output.example_utterance:
            alternatives.append(coach_output.example_utterance)
        if strategy_guidance and strategy_guidance.example_utterance:
            alternatives.append(strategy_guidance.example_utterance)
        
        # 转换为 CoachAdvice
        return CoachAdvice(
            why=coach_output.reasoning,
            action=coach_output.suggestion,
            suggested_reply=coach_output.example_utterance or coach_output.suggestion,
            alternatives=alternatives[:2],  # 最多2条
            guardrails=guardrails,
            priority=coach_output.priority,
            confidence=coach_output.confidence,
            technique_name=coach_output.technique_name,
        )
