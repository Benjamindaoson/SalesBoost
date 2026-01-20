"""
State Updater Service
更新 FSM 状态、Slot、Mood
"""
import logging
from typing import Tuple
from app.schemas.fsm import FSMState, TransitionDecision
from app.schemas.agent_outputs import IntentGateOutput, NPCOutput, EvaluatorOutput
from app.fsm.engine import FSMEngine

logger = logging.getLogger(__name__)


class StateUpdater:
    """
    状态更新器
    
    核心职责：
    - 根据各 Agent 输出更新 FSM 状态
    - 更新 Slot 填充
    - 更新 NPC 情绪
    - 评估并执行状态转换
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
            state: 当前 FSM 状态
            intent_result: 意图识别结果
            npc_result: NPC 输出
            evaluator_result: 评估结果
            current_turn: 当前轮次
            
        Returns:
            (更新后的状态, 转换决策)
        """
        logger.info(f"State update: turn={current_turn}, stage={state.current_stage.value}")
        
        # Step 1: 更新 Slot（从 Intent Gate 和 Evaluator 提取）
        state = self._update_slots_from_intent(state, intent_result, current_turn)
        state = self._update_slots_from_evaluator(state, evaluator_result, current_turn)
        
        # Step 2: 更新 NPC 情绪
        state = self._update_mood(state, npc_result)
        
        # Step 3: 评估状态转换
        transition_decision = self.fsm_engine.evaluate_transition(
            state=state,
            goal_achieved=evaluator_result.goal_advanced,
        )
        
        # Step 4: 执行转换（如果需要）
        if transition_decision.should_transition:
            state = self.fsm_engine.execute_transition(state, transition_decision)
            logger.info(f"Stage transition: {transition_decision.from_stage} -> {transition_decision.to_stage}")
        
        return state, transition_decision

    def _update_slots_from_intent(
        self,
        state: FSMState,
        intent_result: IntentGateOutput,
        current_turn: int,
    ) -> FSMState:
        """从意图识别结果更新 Slot"""
        for detected_slot in intent_result.detected_slots:
            if detected_slot.confidence >= 0.6:
                state = self.fsm_engine.update_slot(
                    state=state,
                    slot_name=detected_slot.slot_name,
                    value=detected_slot.value,
                    confidence=detected_slot.confidence,
                    turn=current_turn,
                    source_utterance=detected_slot.source_span or "",
                )
        return state
    
    def _update_slots_from_evaluator(
        self,
        state: FSMState,
        evaluator_result: EvaluatorOutput,
        current_turn: int,
    ) -> FSMState:
        """从评估结果更新 Slot"""
        for detected_slot in evaluator_result.extracted_slots:
            # 只更新尚未填充或置信度更高的 Slot
            existing = state.slot_values.get(detected_slot.slot_name)
            if not existing or existing.confidence < detected_slot.confidence:
                state = self.fsm_engine.update_slot(
                    state=state,
                    slot_name=detected_slot.slot_name,
                    value=detected_slot.value,
                    confidence=detected_slot.confidence,
                    turn=current_turn,
                    source_utterance=detected_slot.source_span or "",
                )
        return state
    
    def _update_mood(self, state: FSMState, npc_result: NPCOutput) -> FSMState:
        """更新 NPC 情绪"""
        mood_delta = npc_result.mood_after - npc_result.mood_before
        state = self.fsm_engine.update_mood(state, mood_delta)
        return state
