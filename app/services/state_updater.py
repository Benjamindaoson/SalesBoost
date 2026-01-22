"""
State Updater Service
FSM 状态更新逻辑封装
"""
import logging
from typing import Tuple

from app.schemas.fsm import FSMState, TransitionDecision
from app.schemas.agent_outputs import (
    IntentGateOutput,
    NPCOutput,
    EvaluatorOutput,
)
from app.fsm.engine import FSMEngine

logger = logging.getLogger(__name__)

class StateUpdater:
    """
    负责根据 Agent 输出更新 FSM 状态
    
    将复杂的 Slot 更新、覆盖率计算、状态流转逻辑从 Orchestrator 剥离
    """
    
    def __init__(self, fsm_engine: FSMEngine):
        self.fsm_engine = fsm_engine
        
    async def update(
        self,
        state: FSMState,
        intent_result: IntentGateOutput,
        npc_result: NPCOutput,
        evaluator_result: EvaluatorOutput,
        current_turn: int,
    ) -> Tuple[FSMState, TransitionDecision]:
        """
        更新状态
        
        Args:
            state: 当前状态
            intent_result: 意图分析结果
            npc_result: NPC 输出
            evaluator_result: 评估结果
            current_turn: 当前轮次
            
        Returns:
            (更新后的状态, 转换决策)
        """
        # 1. 更新 NPC 情绪
        mood_change = npc_result.mood_after - state.npc_mood
        state = self.fsm_engine.update_mood(state, mood_change)
        
        # 2. 更新 Slots (基于 Evaluator 识别的关键信息)
        # 假设 EvaluatorOutput 中包含 extracted_slots 字段（需要扩展 Evaluator）
        # 这里暂时模拟：如果意图匹配，且 evaluator 认为 goal advanced，则尝试填充 dummy slot
        # 实际逻辑应由 IntentGate 或专门的 NLU 模块提取 Slots
        
        # 3. 评估状态流转
        # 使用 Evaluator 的 goal_advanced 作为主要依据
        goal_achieved = evaluator_result.goal_advanced
        
        # 为了演示 FSM 流转，这里简化逻辑：
        # 如果 goal_achieved 为 True，且当前阶段不是 COMPLETED，则允许流转
        # 实际应结合 Slot 覆盖率
        
        transition_decision = self.fsm_engine.evaluate_transition(
            state=state,
            goal_achieved=goal_achieved
        )
        
        # 4. 执行流转
        if transition_decision.should_transition:
            state = self.fsm_engine.execute_transition(state, transition_decision)
            
        return state, transition_decision
