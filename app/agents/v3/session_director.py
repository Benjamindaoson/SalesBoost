"""
Session Director (V3) - 控制器
只做决策，不生成内容
"""
import logging
from typing import Dict, Any, Optional
from app.schemas.v3_agent_outputs import TurnPlan
from app.schemas.fsm import FSMState
from app.services.model_gateway import ModelGateway
from app.services.model_gateway.schemas import RoutingContext, AgentType, LatencyMode, RiskLevel, TurnImportance

logger = logging.getLogger(__name__)


class SessionDirectorV3:
    """Session Director V3"""
    
    def __init__(self, model_gateway: ModelGateway):
        self.model_gateway = model_gateway
    
    async def plan_turn(
        self,
        fsm_state: FSMState,
        turn_context: Dict[str, Any],
        budget_remaining: float,
        risk_level: RiskLevel,
        evidence_confidence: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> TurnPlan:
        """
        规划本轮执行计划
        
        Args:
            fsm_state: FSM 状态
            turn_context: 轮次上下文
            budget_remaining: 剩余预算比例
            risk_level: 风险等级
            evidence_confidence: 证据置信度
            session_id: 会话ID
            
        Returns:
            TurnPlan
        """
        # 1. 决定快/慢路径
        # 快路径条件：预算充足 + 低风险 + 低重要性
        use_fast_path = (
            budget_remaining > 0.3 and
            risk_level == RiskLevel.LOW and
            turn_context.get("importance", TurnImportance.MEDIUM) == TurnImportance.LOW
        )
        
        path = "fast" if use_fast_path else "slow"
        
        # 2. 决定调用哪些 agents
        if use_fast_path:
            agents_to_call = ["retriever", "npc_generator"]
        else:
            agents_to_call = ["retriever", "npc_generator", "coach_generator", "evaluator", "adoption_tracker"]
        
        # 3. 预算分配
        if use_fast_path:
            budget_allocation = {
                "retriever": 0.2,
                "npc_generator": 0.8,
            }
        else:
            budget_allocation = {
                "retriever": 0.15,
                "npc_generator": 0.3,
                "coach_generator": 0.3,
                "evaluator": 0.2,
                "adoption_tracker": 0.05,
            }
        
        # 4. 模型路由（由 Router 决定，这里只是记录）
        model_routing = {}
        for agent in agents_to_call:
            # 路由决策由 ModelGateway 的 Router 完成
            # 这里只是占位
            model_routing[agent] = "auto"  # 表示由 Router 自动选择
        
        # 5. 升级触发器
        upgrade_triggers = []
        if risk_level == RiskLevel.HIGH:
            upgrade_triggers.append("high_risk")
        if evidence_confidence and evidence_confidence < 0.5:
            upgrade_triggers.append("low_confidence")
        if budget_remaining < 0.2:
            upgrade_triggers.append("low_budget")
        
        # 6. 决策理由
        reasoning = (
            f"Path: {path}, "
            f"Risk: {risk_level.value}, "
            f"Budget: {budget_remaining:.2f}, "
            f"Agents: {', '.join(agents_to_call)}"
        )
        
        return TurnPlan(
            path=path,
            agents_to_call=agents_to_call,
            budget_allocation=budget_allocation,
            model_routing=model_routing,
            upgrade_triggers=upgrade_triggers,
            reasoning=reasoning,
        )

