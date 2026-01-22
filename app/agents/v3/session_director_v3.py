"""
Session Director V3 - 控制器 Agent
职责：决策本轮走快/慢路径、调用哪些 agent、预算分配、是否升级模型
不生成内容，只做决策
"""
import logging
from typing import Dict, Any, Optional
from app.schemas.v3_agent_outputs import TurnPlan
from app.schemas.fsm import FSMState, SalesStage
from app.services.model_gateway import ModelGateway, AgentType, LatencyMode, RoutingContext
from app.services.model_gateway.budget import BudgetManager

logger = logging.getLogger(__name__)


class SessionDirectorV3:
    """Session Director V3 - 控制器"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
    
    async def plan_turn(
        self,
        turn_number: int,
        fsm_state: FSMState,
        user_message: str,
        conversation_history: list[Dict[str, Any]],
        session_id: str,
        user_id: str,
    ) -> TurnPlan:
        """
        规划本轮执行计划
        
        Args:
            turn_number: 轮次号
            fsm_state: FSM 状态
            user_message: 用户消息
            conversation_history: 对话历史
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            TurnPlan
        """
        # 1. 计算轮次重要性
        turn_importance = self._calculate_turn_importance(
            fsm_state.current_stage,
            turn_number,
            conversation_history
        )
        
        # 2. 评估风险等级
        risk_level = self._assess_risk_level(user_message, fsm_state)
        
        # 3. 获取剩余预算
        budget_remaining = self.budget_manager.get_remaining_budget(session_id)
        
        # 4. 决定路径模式
        path_mode = self._decide_path_mode(
            turn_importance,
            risk_level,
            budget_remaining,
            fsm_state.current_stage
        )
        
        # 5. 决定调用哪些 Agent
        agents_to_call = self._decide_agents(path_mode, fsm_state.current_stage)
        
        # 6. 分配预算
        budget_allocation = self._allocate_budget(
            agents_to_call,
            budget_remaining,
            path_mode
        )
        
        # 7. 决定是否升级模型
        model_upgrade = self._should_upgrade_model(
            turn_importance,
            risk_level,
            budget_remaining
        )
        
        # 8. 评估证据置信度（基于历史）
        evidence_confidence = self._estimate_evidence_confidence(conversation_history)
        
        # 9. 生成决策理由
        reasoning = self._generate_reasoning(
            path_mode,
            agents_to_call,
            turn_importance,
            risk_level,
            budget_remaining
        )
        
        return TurnPlan(
            turn_number=turn_number,
            path_mode=path_mode,
            agents_to_call=agents_to_call,
            budget_allocation=budget_allocation,
            model_upgrade=model_upgrade,
            risk_level=risk_level,
            evidence_confidence=evidence_confidence,
            reasoning=reasoning,
        )
    
    def _calculate_turn_importance(
        self,
        current_stage: SalesStage,
        turn_number: int,
        conversation_history: list[Dict[str, Any]]
    ) -> float:
        """计算轮次重要性（0-1）"""
        # 关键阶段重要性高
        stage_importance = {
            SalesStage.CLOSING: 0.9,
            SalesStage.OBJECTION_HANDLING: 0.8,
            SalesStage.PRODUCT_INTRO: 0.6,
            SalesStage.NEEDS_DISCOVERY: 0.5,
            SalesStage.OPENING: 0.3,
        }
        base_importance = stage_importance.get(current_stage, 0.5)
        
        # 轮次越靠后重要性越高（接近成交）
        turn_factor = min(turn_number / 20.0, 1.0)
        
        # 对话长度影响（太长可能偏离主题）
        history_factor = 1.0 - min(len(conversation_history) / 50.0, 0.3)
        
        return min(base_importance + turn_factor * 0.2 + history_factor * 0.1, 1.0)
    
    def _assess_risk_level(self, user_message: str, fsm_state: FSMState) -> str:
        """评估风险等级"""
        # 简单规则：检查关键词
        high_risk_keywords = ["绝对", "保证", "稳赚", "保本"]
        medium_risk_keywords = ["很多", "大量", "马上"]
        
        message_lower = user_message.lower()
        
        if any(kw in message_lower for kw in high_risk_keywords):
            return "high"
        elif any(kw in message_lower for kw in medium_risk_keywords):
            return "medium"
        else:
            return "low"
    
    def _decide_path_mode(
        self,
        turn_importance: float,
        risk_level: str,
        budget_remaining: float,
        current_stage: SalesStage
    ) -> str:
        """决定路径模式"""
        # 关键阶段或高风险：走 both（快+慢）
        if turn_importance > 0.8 or risk_level == "high":
            return "both"
        
        # 预算不足：只走 fast
        if budget_remaining < 0.01:
            return "fast"
        
        # 默认：both（快路径立即返回，慢路径异步）
        return "both"
    
    def _decide_agents(self, path_mode: str, current_stage: SalesStage) -> list[str]:
        """决定调用哪些 Agent"""
        agents = []
        
        if path_mode in ["fast", "both"]:
            agents.extend(["retriever", "npc_generator"])
        
        if path_mode in ["slow", "both"]:
            agents.extend(["coach_generator", "evaluator", "adoption_tracker"])
            # 关键阶段可能需要 GraphRAG
            if current_stage in [SalesStage.OBJECTION_HANDLING, SalesStage.CLOSING]:
                agents.append("retriever_graphrag")
        
        return agents
    
    def _allocate_budget(
        self,
        agents_to_call: list[str],
        budget_remaining: float,
        path_mode: str
    ) -> Dict[str, float]:
        """分配预算"""
        allocation = {}
        
        # Fast Path 预算
        fast_budget = 0.02 if path_mode in ["fast", "both"] else 0.0
        # Slow Path 预算
        slow_budget = 0.03 if path_mode in ["slow", "both"] else 0.0
        
        # 按 Agent 分配
        fast_agents = ["retriever", "npc_generator"]
        slow_agents = ["coach_generator", "evaluator", "adoption_tracker", "retriever_graphrag"]
        
        for agent in agents_to_call:
            if agent in fast_agents:
                allocation[agent] = fast_budget / len([a for a in agents_to_call if a in fast_agents])
            elif agent in slow_agents:
                allocation[agent] = slow_budget / len([a for a in agents_to_call if a in slow_agents])
            else:
                allocation[agent] = 0.01  # 默认
        
        return allocation
    
    def _should_upgrade_model(
        self,
        turn_importance: float,
        risk_level: str,
        budget_remaining: float
    ) -> bool:
        """决定是否升级模型"""
        # 高重要性 + 高风险 + 预算充足
        if turn_importance > 0.8 and risk_level == "high" and budget_remaining > 0.1:
            return True
        return False
    
    def _estimate_evidence_confidence(self, conversation_history: list[Dict[str, Any]]) -> float:
        """估算证据置信度"""
        # 基于历史对话长度和内容质量
        if len(conversation_history) < 2:
            return 0.5  # 初始阶段置信度低
        
        # 简单启发式：对话越长，置信度越高（但有限）
        confidence = min(len(conversation_history) / 10.0, 0.9)
        return confidence
    
    def _generate_reasoning(
        self,
        path_mode: str,
        agents_to_call: list[str],
        turn_importance: float,
        risk_level: str,
        budget_remaining: float
    ) -> str:
        """生成决策理由"""
        return (
            f"Path mode: {path_mode}, "
            f"Importance: {turn_importance:.2f}, "
            f"Risk: {risk_level}, "
            f"Budget: ${budget_remaining:.2f}, "
            f"Agents: {', '.join(agents_to_call)}"
        )

