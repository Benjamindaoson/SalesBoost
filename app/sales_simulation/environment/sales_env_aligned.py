"""
销售模拟环境（完全对齐版）
与主系统 FSM 完全对齐的模拟环境

【关键改造】
- step() 方法中调用 DecisionEngineAdapter
- 所有状态转换由主系统 DecisionEngine 决定
- 移除所有内部状态判断逻辑
"""
import logging
import asyncio
from typing import Dict, Any, Tuple, Optional

from app.sales_simulation.environment.sales_env import SalesSimulationEnv
from app.sales_simulation.schemas.trajectory import StepAction, StepObservation

logger = logging.getLogger(__name__)


class AlignedSalesSimulationEnv(SalesSimulationEnv):
    """
    对齐版销售模拟环境
    
    【核心改造】
    重写 step() 方法，集成 DecisionEngineAdapter
    """
    
    async def step_async(
        self,
        action: StepAction,
    ) -> Tuple[StepObservation, float, bool, Dict[str, Any]]:
        """
        执行一步动作（对齐版 - 异步）
        
        【改造】
        在原有逻辑基础上，增加 DecisionEngine 调用
        
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
        
        # 3. 更新状态（客户情绪等）
        self._update_state_from_action(action)
        
        # 4. 检测信号
        signals = self._detect_signals(action, customer_response)
        
        # 【新增】5. 调用 DecisionEngineAdapter 决定状态转换
        observation_data = {
            "customer_response": customer_response,
            "customer_mood": self.state_manager.customer_mood,
            "customer_interest": self.state_manager.customer_interest,
            "current_stage": self.state_manager.current_stage,
            "goal_progress": self.state_manager.goal_progress,
            "detected_signals": signals,
            "step_score": 0.7,  # 简化处理
            "mood_before": self.state_manager.customer_mood - 0.05,
        }
        
        # 调用 DecisionEngine（异步）
        try:
            updated_fsm_state, transition_decision = await self.decision_adapter.decide_next_state(
                current_fsm_state=self.fsm_state,
                simulation_observation=observation_data,
                current_turn=self.current_step,
            )
            
            # 更新 FSM State
            self.fsm_state = updated_fsm_state
            
            # 如果发生了状态转换，同步到 StateManager
            if transition_decision.should_transition and transition_decision.to_stage:
                self.state_manager.apply_stage_transition(transition_decision.to_stage.value)
                logger.info(
                    f"FSM transition applied: {transition_decision.from_stage.value} -> "
                    f"{transition_decision.to_stage.value}, reason: {transition_decision.reason}"
                )
        except Exception as e:
            logger.error(f"DecisionEngine call failed: {e}, continuing without state transition")
        
        # 6. 计算奖励
        reward = self._calculate_reward(action, compliance_passed)
        
        # 7. 判断终止
        done = self.is_terminal()
        
        # 8. 记录对话
        self.state_manager.add_conversation_turn(
            agent_message=action.content,
            customer_response=customer_response,
            step_index=self.current_step,
        )
        
        # 9. 构建观察
        observation = StepObservation(
            customer_response=customer_response,
            customer_mood=self.state_manager.customer_mood,
            customer_interest=self.state_manager.customer_interest,
            current_stage=self.state_manager.current_stage,
            goal_progress=self.state_manager.goal_progress,
            compliance_passed=compliance_passed,
            detected_signals=signals,
        )
        
        # 10. 构建信息
        info = {
            "step": self.current_step,
            "goal_achieved": self.state_manager.goal_achieved,
            "violations": len(self.state_manager.violations),
            "customer_satisfaction": self.state_manager.calculate_customer_satisfaction(),
            "fsm_state": self.fsm_state.current_stage.value if self.fsm_state else None,
        }
        
        logger.debug(
            f"Step {self.current_step}: reward={reward:.3f}, "
            f"mood={observation.customer_mood:.2f}, stage={observation.current_stage}, done={done}"
        )
        
        return observation, reward, done, info
    
    def step(
        self,
        action: StepAction,
    ) -> Tuple[StepObservation, float, bool, Dict[str, Any]]:
        """
        同步版本的 step（向后兼容）
        
        【注意】
        这是同步包装，内部调用异步版本
        建议直接使用 step_async() 以获得更好的性能
        """
        import asyncio
        
        # 获取或创建事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建一个任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.step_async(action))
                return future.result()
        except RuntimeError:
            # 没有运行中的事件循环，直接运行
            return asyncio.run(self.step_async(action))

