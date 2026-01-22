"""
Budget Manager - 管理会话和轮次预算
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from app.services.model_gateway.schemas import BudgetConfig, ModelCall, AgentType

logger = logging.getLogger(__name__)


class BudgetManager:
    """预算管理器"""
    
    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()
        # 会话预算追踪：session_id -> spent_budget
        self.session_budgets: Dict[str, float] = {}
        # 轮次预算追踪：session_id -> turn_budget
        self.turn_budgets: Dict[str, float] = {}
    
    def initialize_session(self, session_id: str):
        """初始化会话预算"""
        self.session_budgets[session_id] = 0.0
        self.turn_budgets[session_id] = 0.0
        logger.info(f"Session budget initialized: {session_id}, budget=${self.config.per_session_budget}")
    
    def check_budget(
        self,
        session_id: str,
        estimated_cost: float,
        path: str = "fast"  # "fast" or "slow"
    ) -> tuple[bool, float]:
        """
        检查预算是否足够
        
        Returns:
            (is_available, remaining_budget)
        """
        session_spent = self.session_budgets.get(session_id, 0.0)
        turn_spent = self.turn_budgets.get(session_id, 0.0)
        
        # 检查会话预算
        session_remaining = self.config.per_session_budget - session_spent
        if session_remaining < estimated_cost:
            logger.warning(
                f"Session budget insufficient: {session_id}, "
                f"remaining=${session_remaining:.4f}, needed=${estimated_cost:.4f}"
            )
            return False, session_remaining
        
        # 检查轮次预算
        path_budget = self.config.fast_path_budget if path == "fast" else self.config.slow_path_budget
        turn_remaining = path_budget - turn_spent
        if turn_remaining < estimated_cost:
            logger.warning(
                f"Turn budget insufficient: {session_id}, "
                f"remaining=${turn_remaining:.4f}, needed=${estimated_cost:.4f}"
            )
            return False, turn_remaining
        
        return True, min(session_remaining, turn_remaining)
    
    def deduct_budget(
        self,
        session_id: str,
        cost: float,
        path: str = "fast"
    ):
        """扣减预算"""
        if session_id not in self.session_budgets:
            self.initialize_session(session_id)
        
        self.session_budgets[session_id] += cost
        self.turn_budgets[session_id] += cost
        
        logger.debug(
            f"Budget deducted: {session_id}, cost=${cost:.4f}, "
            f"session_spent=${self.session_budgets[session_id]:.4f}, "
            f"turn_spent=${self.turn_budgets[session_id]:.4f}"
        )
    
    def reset_turn_budget(self, session_id: str):
        """重置轮次预算（每轮开始时调用）"""
        self.turn_budgets[session_id] = 0.0
    
    def get_remaining_budget(self, session_id: str) -> float:
        """获取剩余预算"""
        session_spent = self.session_budgets.get(session_id, 0.0)
        return self.config.per_session_budget - session_spent
    
    def record_call(self, call: ModelCall):
        """记录模型调用（用于审计）"""
        # 这里可以写入数据库或日志
        logger.info(
            f"Model call: {call.agent_type} -> {call.provider}/{call.model}, "
            f"cost=${call.cost_usd:.4f}, latency={call.latency_ms:.0f}ms"
        )
