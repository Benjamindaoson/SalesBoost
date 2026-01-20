"""
销售模拟环境（改造版 - 集成 DecisionEngine）
实现具体的销售任务模拟逻辑

【重要改造】
- 集成 DecisionEngineAdapter
- 所有状态转换由主系统 DecisionEngine 决定
- 移除内部状态判断逻辑
"""
import logging
import random
from typing import Dict, Any, Tuple, Optional

from app.sales_simulation.environment.base_env import BaseSimulationEnv
from app.sales_simulation.environment.state_manager import StateManager
from app.sales_simulation.schemas.scenario import SimulationScenario
from app.sales_simulation.schemas.trajectory import (
    StepAction,
    StepObservation,
    ActionType,
)
from app.sales_simulation.adapters.decision_engine_adapter import DecisionEngineAdapter
from app.schemas.fsm import FSMState

logger = logging.getLogger(__name__)


class SalesSimulationEnv(BaseSimulationEnv):
    """
    销售模拟环境（改造版）
    
    【核心功能】
    - 模拟客户响应
    - 计算奖励信号
    - 判断终止条件
    - 检测关键信号
    - 【新增】通过 DecisionEngineAdapter 调用主系统决策逻辑
    """
    
    def __init__(self, scenario: SimulationScenario):
        """
        初始化销售环境
        
        Args:
            scenario: 模拟场景
        """
        super().__init__(scenario)
        self.state_manager = StateManager(scenario)
        self.max_turns = scenario.config.max_turns
        
        # 【新增】集成 DecisionEngineAdapter
        self.decision_adapter = DecisionEngineAdapter()
        self.fsm_state: Optional[FSMState] = None
        
        logger.info("SalesSimulationEnv initialized with DecisionEngineAdapter")
    
    def reset(self, seed: Optional[int] = None) -> StepObservation:
        """
        重置环境
        
        Args:
            seed: 随机种子
            
        Returns:
            初始观察
        """
        if seed is not None:
            self.set_seed(seed)
        
        self.current_step = 0
        self.is_done = False
        self.state_manager.reset()
        
        # 【新增】初始化 FSM State（使用主系统逻辑）
        self.fsm_state = self.decision_adapter.create_initial_fsm_state()
        
        # 同步 FSM State 到 StateManager
        self.state_manager.apply_stage_transition(self.fsm_state.current_stage.value)
        
        logger.info(f"Environment reset with seed={seed}, initial_stage={self.fsm_state.current_stage.value}")
        
        # 返回初始观察
        return StepObservation(
            customer_response=self._generate_initial_response(),
            customer_mood=self.state_manager.customer_mood,
            customer_interest=self.state_manager.customer_interest,
            current_stage=self.state_manager.current_stage,
            goal_progress=self.state_manager.goal_progress,
            compliance_passed=True,
            detected_signals=[],
        )
    
    def step(
        self,
        action: StepAction,
    ) -> Tuple[StepObservation, float, bool, Dict[str, Any]]:
        """
        执行一步动作
        
        Args:
            action: Agent 动作
            
        Returns:
            observation: 环境观察
            reward: 奖励信号
            done: 是否结束
            info: 额外信息
        """
        self.current_step += 1
        
        # 1. 检查合规性
        compliance_passed = self._check_compliance(action)
        
        # 2. 生成客户响应
        customer_response = self._generate_customer_response(action)
        
        # 3. 更新状态
        self._update_state_from_action(action)
        
        # 4. 检测信号
        signals = self._detect_signals(action, customer_response)
        
        # 5. 计算奖励
        reward = self._calculate_reward(action, compliance_passed)
        
        # 6. 判断终止
        done = self.is_terminal()
        
        # 7. 记录对话
        self.state_manager.add_conversation_turn(
            agent_message=action.content,
            customer_response=customer_response,
            step_index=self.current_step,
        )
        
        # 8. 构建观察
        observation = StepObservation(
            customer_response=customer_response,
            customer_mood=self.state_manager.customer_mood,
            customer_interest=self.state_manager.customer_interest,
            current_stage=self.state_manager.current_stage,
            goal_progress=self.state_manager.goal_progress,
            compliance_passed=compliance_passed,
            detected_signals=signals,
        )
        
        # 9. 构建信息
        info = {
            "step": self.current_step,
            "goal_achieved": self.state_manager.goal_achieved,
            "violations": len(self.state_manager.violations),
            "customer_satisfaction": self.state_manager.calculate_customer_satisfaction(),
        }
        
        logger.debug(
            f"Step {self.current_step}: reward={reward:.3f}, "
            f"mood={observation.customer_mood:.2f}, done={done}"
        )
        
        return observation, reward, done, info
    
    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self.state_manager.get_state_snapshot()
    
    def is_terminal(self) -> bool:
        """判断是否终止"""
        # 终止条件：
        # 1. 达到最大轮数
        # 2. 目标已达成
        # 3. 客户情绪过低（< 0.2）
        # 4. 严重违规（> 3次）
        
        if self.current_step >= self.max_turns:
            logger.info("Terminated: max turns reached")
            return True
        
        if self.state_manager.goal_achieved:
            logger.info("Terminated: goal achieved")
            return True
        
        if self.state_manager.customer_mood < 0.2:
            logger.info("Terminated: customer mood too low")
            return True
        
        if len(self.state_manager.violations) > 3:
            logger.info("Terminated: too many violations")
            return True
        
        return False
    
    # ========== 私有方法 ==========
    
    def _generate_initial_response(self) -> str:
        """生成初始客户响应"""
        customer = self.scenario.customer_profile
        
        responses = [
            f"你好，我是{customer.name}。",
            f"嗯，你找我有什么事吗？",
            f"我现在有点忙，请简短说明。",
        ]
        
        return random.choice(responses)
    
    def _generate_customer_response(self, action: StepAction) -> str:
        """
        生成客户响应（简化版 Mock）
        
        实际应用中应该调用 NPC Agent
        """
        customer = self.scenario.customer_profile
        mood = self.state_manager.customer_mood
        
        # 根据动作类型和情绪生成响应
        if action.action_type == ActionType.QUESTION:
            if mood > 0.6:
                return "这是个好问题。让我想想..."
            else:
                return "这个问题我不太想回答。"
        
        elif action.action_type == ActionType.PRESENT:
            if self.state_manager.customer_interest > 0.5:
                return "听起来不错，能详细说说吗？"
            else:
                return "嗯，我不确定这个适合我们。"
        
        elif action.action_type == ActionType.HANDLE_OBJECTION:
            if mood > 0.5:
                return "你说的有道理，我再考虑考虑。"
            else:
                return "我还是有顾虑。"
        
        elif action.action_type == ActionType.CLOSE:
            if self.state_manager.goal_progress > 0.8:
                return "好的，我们可以安排下一步。"
            else:
                return "现在还不是时候。"
        
        else:
            return "嗯，继续说。"
    
    def _check_compliance(self, action: StepAction) -> bool:
        """
        检查合规性
        
        简化版：检查是否包含违禁词
        """
        forbidden_words = ["保证", "一定", "绝对", "最好", "第一"]
        
        for word in forbidden_words:
            if word in action.content:
                self.state_manager.add_violation(f"使用违禁词: {word}")
                return False
        
        return True
    
    def _update_state_from_action(self, action: StepAction) -> None:
        """根据动作更新状态"""
        # 根据动作类型更新客户状态
        if action.action_type == ActionType.QUESTION:
            # 提问增加兴趣，轻微增加情绪
            self.state_manager.update_customer_state(
                mood_delta=0.05,
                interest_delta=0.1,
                trust_delta=0.05,
            )
            self.state_manager.update_goal_progress(0.05)
        
        elif action.action_type == ActionType.LISTEN:
            # 倾听增加信任和情绪
            self.state_manager.update_customer_state(
                mood_delta=0.1,
                trust_delta=0.1,
            )
        
        elif action.action_type == ActionType.PRESENT:
            # 展示增加兴趣，可能降低情绪（如果过早）
            if self.state_manager.customer_interest > 0.4:
                self.state_manager.update_customer_state(
                    interest_delta=0.15,
                    mood_delta=0.05,
                )
                self.state_manager.update_goal_progress(0.1)
            else:
                self.state_manager.update_customer_state(mood_delta=-0.1)
        
        elif action.action_type == ActionType.HANDLE_OBJECTION:
            # 处理异议，根据质量影响情绪
            if action.confidence > 0.7:
                self.state_manager.update_customer_state(
                    mood_delta=0.1,
                    trust_delta=0.1,
                )
                self.state_manager.update_goal_progress(0.1)
            else:
                self.state_manager.update_customer_state(mood_delta=-0.05)
        
        elif action.action_type == ActionType.CLOSE:
            # 促单，根据时机影响结果
            if self.state_manager.goal_progress > 0.7:
                self.state_manager.update_goal_progress(0.2)
            else:
                self.state_manager.update_customer_state(mood_delta=-0.15)
    
    def _detect_signals(self, action: StepAction, response: str) -> list[str]:
        """检测关键信号"""
        signals = []
        
        # 检测兴趣信号
        interest_keywords = ["不错", "详细", "了解", "考虑"]
        if any(kw in response for kw in interest_keywords):
            signals.append("interest_signal")
            self.state_manager.add_signal("interest_signal")
        
        # 检测异议信号
        objection_keywords = ["但是", "顾虑", "担心", "不确定"]
        if any(kw in response for kw in objection_keywords):
            signals.append("objection_signal")
            self.state_manager.add_signal("objection_signal")
        
        # 检测购买信号
        buying_keywords = ["安排", "下一步", "试试", "开始"]
        if any(kw in response for kw in buying_keywords):
            signals.append("buying_signal")
            self.state_manager.add_signal("buying_signal")
        
        return signals
    
    def _calculate_reward(self, action: StepAction, compliance_passed: bool) -> float:
        """
        计算奖励信号
        
        奖励组成：
        - 目标进度奖励
        - 客户状态奖励
        - 合规性奖励
        - 效率奖励
        """
        reward = 0.0
        
        # 1. 目标进度奖励（权重 0.4）
        goal_reward = self.state_manager.goal_progress * 0.4
        reward += goal_reward
        
        # 2. 客户状态奖励（权重 0.3）
        customer_reward = (
            self.state_manager.customer_mood * 0.15 +
            self.state_manager.customer_interest * 0.10 +
            self.state_manager.customer_trust * 0.05
        )
        reward += customer_reward
        
        # 3. 合规性奖励/惩罚（权重 0.2）
        if compliance_passed:
            reward += 0.2
        else:
            reward -= 0.3
        
        # 4. 效率奖励（权重 0.1）
        efficiency = 1.0 - (self.current_step / self.max_turns)
        reward += efficiency * 0.1
        
        # 5. 目标达成额外奖励
        if self.state_manager.goal_achieved:
            reward += 1.0
        
        return reward

