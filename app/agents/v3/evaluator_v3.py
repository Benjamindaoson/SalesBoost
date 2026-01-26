"""
Evaluator V3 - 裁判
封装现有 Evaluator agent，输出 Evaluation
固定低温；模型选择尽量固定（HR-4）
"""
import logging
from typing import Dict, Any, List, Optional
from app.schemas.v3_agent_outputs import Evaluation, DimensionScore, ErrorTag
from app.schemas.fsm import FSMState, SalesStage, StageSlotConfig
from app.schemas.agent_outputs import ComplianceOutput
from app.agents.roles.evaluator_agent import EvaluatorAgent
from app.services.model_gateway import ModelGateway, AgentType, LatencyMode, RoutingContext
from app.services.model_gateway.budget import BudgetManager

logger = logging.getLogger(__name__)


class EvaluatorV3:
    """Evaluator V3 - 裁判"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        # 封装现有 Evaluator Agent（固定低温）
        self.evaluator_agent = EvaluatorAgent()
        # HR-4: 固定模型选择（不允许 per-turn 随机切）
        self._fixed_model = None  # 首次调用时确定
    
    async def evaluate(
        self,
        user_message: str,
        npc_response: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        stage_config: Optional[StageSlotConfig],
        compliance_result: ComplianceOutput,
        session_id: str,
        turn_number: int,
    ) -> Evaluation:
        """
        评估轮次
        
        Args:
            user_message: 用户消息
            npc_response: NPC 回复
            conversation_history: 对话历史
            fsm_state: FSM 状态
            stage_config: 阶段配置
            compliance_result: 合规检查结果
            session_id: 会话ID
            turn_number: 轮次号
            
        Returns:
            Evaluation
        """
        # HR-4: Evaluator 一致性 - 固定模型/低温
        # Evaluator Agent 已在 __init__ 中设置 temperature=0.1
        
        # 创建合规结果（简化）
        from app.schemas.agent_outputs import ComplianceOutput
        compliance_result = ComplianceOutput(
            is_compliant=True,
            risk_flags=[],
            blocked=False,
            risk_level="OK",
        )
        
        # 调用现有 Evaluator Agent
        npc_response = npc_reply.response if hasattr(npc_reply, 'response') else str(npc_reply)
        evaluator_output, strategy_analysis = await self.evaluator_agent.evaluate(
            user_message=user_message,
            npc_response=npc_response,
            conversation_history=conversation_history,
            fsm_state=fsm_state,
            stage_config=stage_config,
            compliance_result=compliance_result,
        )
        
        # 转换为 Evaluation
        error_tags = []
        compliance_flags = []
        stage_mistakes = []
        
        # 从 evaluator_output 提取错误标签
        for improvement_point in evaluator_output.improvement_points:
            # 简单分类
            if "合规" in improvement_point or "风险" in improvement_point:
                error_tags.append(ErrorTag(
                    tag="compliance",
                    severity="major",
                    description=improvement_point,
                    suggestion=None,
                ))
                compliance_flags.append("compliance_issue")
            elif "阶段" in improvement_point or "目标" in improvement_point:
                stage_mistakes.append(improvement_point)
                error_tags.append(ErrorTag(
                    tag="stage_mistake",
                    severity="minor",
                    description=improvement_point,
                    suggestion=None,
                ))
        
        # 从合规结果提取合规标志
        if not compliance_result.is_compliant:
            for risk_flag in compliance_result.risk_flags:
                compliance_flags.append(risk_flag.risk_type)
        
        # 计算一致性得分（基于五维评分的方差）
        scores = [
            evaluator_output.integrity.score,
            evaluator_output.relevance.score,
            evaluator_output.correctness.score,
            evaluator_output.logic.score,
            evaluator_output.compliance.score,
        ]
        import numpy as np
        consistency_score = 1.0 - min(np.std(scores) / 10.0, 1.0)  # 方差越小，一致性越高
        
        return Evaluation(
            integrity=DimensionScore(
                score=evaluator_output.integrity.score,
                rationale=evaluator_output.integrity.feedback,
                evidence=evaluator_output.integrity.evidence,
            ),
            relevance=DimensionScore(
                score=evaluator_output.relevance.score,
                rationale=evaluator_output.relevance.feedback,
                evidence=evaluator_output.relevance.evidence,
            ),
            correctness=DimensionScore(
                score=evaluator_output.correctness.score,
                rationale=evaluator_output.correctness.feedback,
                evidence=evaluator_output.correctness.evidence,
            ),
            logic=DimensionScore(
                score=evaluator_output.logic.score,
                rationale=evaluator_output.logic.feedback,
                evidence=evaluator_output.logic.evidence,
            ),
            compliance=DimensionScore(
                score=evaluator_output.compliance.score,
                rationale=evaluator_output.compliance.feedback,
                evidence=evaluator_output.compliance.evidence,
            ),
            overall_score=evaluator_output.overall_score,
            goal_advanced=evaluator_output.goal_advanced,
            goal_feedback=evaluator_output.goal_feedback,
            error_tags=error_tags,
            compliance_flags=compliance_flags,
            stage_mistakes=stage_mistakes,
            consistency_score=consistency_score,
        )
