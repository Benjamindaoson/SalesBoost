"""
状态管理器（改造版 - 只应用状态，不做决策）
管理模拟环境的内部状态

【重要改造】
- 移除所有状态转换决策逻辑
- 只负责"应用"由 DecisionEngineAdapter 做出的决策
- 不再包含任何 "是否该进入下一阶段" 的判断
"""
import logging
from typing import Dict, Any, List, Optional
from copy import deepcopy

from app.sales_simulation.schemas.scenario import SimulationScenario, CustomerProfile
from app.fsm.protocol import SalesFSMState, validate_state

logger = logging.getLogger(__name__)


class StateManager:
    """
    状态管理器（改造版）
    
    【核心职责】（只应用，不决策）
    - 维护客户状态（情绪、兴趣、信任度）
    - 应用销售阶段状态（由外部决策）
    - 维护对话历史
    - 提供状态查询
    
    【禁止】
    - 不得包含任何状态转换判断逻辑
    - 不得决定"是否该进入下一阶段"
    - 所有阶段转换由 DecisionEngineAdapter 决定
    """
    
    def __init__(self, scenario: SimulationScenario):
        """
        初始化状态管理器
        
        Args:
            scenario: 模拟场景
        """
        self.scenario = scenario
        self.customer_profile = scenario.customer_profile
        
        # 客户状态
        self.customer_mood: float = self.customer_profile.initial_mood
        self.customer_interest: float = self.customer_profile.initial_interest
        self.customer_trust: float = 0.3  # 初始信任度
        
        # 销售阶段
        self.current_stage: str = "OPENING"
        self.stage_history: List[str] = ["OPENING"]
        
        # 目标进度
        self.goal_progress: float = 0.0
        self.goal_achieved: bool = False
        
        # 对话历史
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 检测到的信号
        self.detected_signals: List[str] = []
        
        # 违规记录
        self.violations: List[str] = []
        
        logger.info(f"StateManager initialized for scenario: {scenario.id}")
    
    def reset(self) -> None:
        """重置状态到初始值"""
        self.customer_mood = self.customer_profile.initial_mood
        self.customer_interest = self.customer_profile.initial_interest
        self.customer_trust = 0.3
        
        self.current_stage = "OPENING"
        self.stage_history = ["OPENING"]
        
        self.goal_progress = 0.0
        self.goal_achieved = False
        
        self.conversation_history = []
        self.detected_signals = []
        self.violations = []
        
        logger.debug("State reset to initial values")
    
    def update_customer_state(
        self,
        mood_delta: float = 0.0,
        interest_delta: float = 0.0,
        trust_delta: float = 0.0,
    ) -> None:
        """
        更新客户状态
        
        Args:
            mood_delta: 情绪变化量
            interest_delta: 兴趣变化量
            trust_delta: 信任变化量
        """
        self.customer_mood = max(0.0, min(1.0, self.customer_mood + mood_delta))
        self.customer_interest = max(0.0, min(1.0, self.customer_interest + interest_delta))
        self.customer_trust = max(0.0, min(1.0, self.customer_trust + trust_delta))
        
        logger.debug(
            f"Customer state updated: mood={self.customer_mood:.2f}, "
            f"interest={self.customer_interest:.2f}, trust={self.customer_trust:.2f}"
        )
    
    def apply_stage_transition(self, new_stage: str) -> bool:
        """
        应用销售阶段转换（由外部决策）
        
        【重要】
        这个方法只"应用"转换结果，不做任何决策判断
        转换决策由 DecisionEngineAdapter 完成
        
        Args:
            new_stage: 新阶段（来自 DecisionEngine 的决策）
            
        Returns:
            是否成功应用转换
            
        Raises:
            ValueError: 如果 new_stage 不是合法的 FSM 状态
        """
        # 验证状态合法性（防漂移）
        if not validate_state(new_stage):
            raise ValueError(
                f"Invalid FSM state: {new_stage}. "
                f"Must be one of {[s.value for s in SalesFSMState]}"
            )
        
        if new_stage != self.current_stage:
            self.stage_history.append(new_stage)
            old_stage = self.current_stage
            self.current_stage = new_stage
            logger.info(f"Stage transition applied: {old_stage} -> {new_stage}")
            return True
        return False
    
    def update_goal_progress(self, delta: float) -> None:
        """
        更新目标进度
        
        Args:
            delta: 进度增量
        """
        self.goal_progress = max(0.0, min(1.0, self.goal_progress + delta))
        
        # 检查目标是否达成
        if self.goal_progress >= 0.95 and not self.goal_achieved:
            self.goal_achieved = True
            logger.info("Goal achieved!")
    
    def add_conversation_turn(
        self,
        agent_message: str,
        customer_response: str,
        step_index: int,
    ) -> None:
        """
        添加对话轮次
        
        Args:
            agent_message: Agent 消息
            customer_response: 客户响应
            step_index: 步骤索引
        """
        self.conversation_history.append({
            "step": step_index,
            "agent": agent_message,
            "customer": customer_response,
            "stage": self.current_stage,
            "mood": self.customer_mood,
            "interest": self.customer_interest,
        })
    
    def add_signal(self, signal: str) -> None:
        """
        添加检测到的信号
        
        Args:
            signal: 信号类型
        """
        self.detected_signals.append(signal)
        logger.debug(f"Signal detected: {signal}")
    
    def add_violation(self, violation: str) -> None:
        """
        添加违规记录
        
        Args:
            violation: 违规描述
        """
        self.violations.append(violation)
        logger.warning(f"Violation detected: {violation}")
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        获取状态快照
        
        Returns:
            状态字典
        """
        return {
            "customer_mood": self.customer_mood,
            "customer_interest": self.customer_interest,
            "customer_trust": self.customer_trust,
            "current_stage": self.current_stage,
            "stage_history": deepcopy(self.stage_history),
            "goal_progress": self.goal_progress,
            "goal_achieved": self.goal_achieved,
            "conversation_turns": len(self.conversation_history),
            "detected_signals": deepcopy(self.detected_signals),
            "violations": deepcopy(self.violations),
        }
    
    def get_conversation_context(self, last_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近 N 轮对话上下文
        
        Args:
            last_n: 最近 N 轮
            
        Returns:
            对话历史列表
        """
        return deepcopy(self.conversation_history[-last_n:])
    
    def calculate_customer_satisfaction(self) -> float:
        """
        计算客户满意度
        
        Returns:
            满意度评分 (0-1)
        """
        # 综合情绪、兴趣、信任度
        satisfaction = (
            self.customer_mood * 0.4 +
            self.customer_interest * 0.3 +
            self.customer_trust * 0.3
        )
        return satisfaction

