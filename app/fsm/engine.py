"""
FSM 引擎 - 基于 Slot 覆盖率的状态流转
"""
import logging
from typing import Dict, List, Optional, Tuple
from app.schemas.fsm import (
    SalesStage,
    FSMState,
    SlotValue,
    SlotCoverage,
    StageSlotConfig,
    TransitionDecision,
    DEFAULT_STAGE_SLOTS,
)

logger = logging.getLogger(__name__)


class FSMEngine:
    """
    FSM 引擎
    
    核心职责：
    - 管理销售阶段状态
    - 基于 Slot 覆盖率判断阶段流转
    - 提供状态查询和更新接口
    
    流转规则（严格执行）：
    1. 必须满足当前阶段的 min_coverage_to_advance
    2. 必须满足阶段目标达成 (goal_achieved = True)
    3. 只能单向流转，不可回退
    """
    
    # 阶段流转顺序
    STAGE_ORDER: List[SalesStage] = [
        SalesStage.OPENING,
        SalesStage.NEEDS_DISCOVERY,
        SalesStage.PRODUCT_INTRO,
        SalesStage.OBJECTION_HANDLING,
        SalesStage.CLOSING,
        SalesStage.COMPLETED,
    ]
    
    def __init__(self, stage_configs: Optional[Dict[SalesStage, StageSlotConfig]] = None):
        """
        初始化 FSM 引擎
        
        Args:
            stage_configs: 阶段 Slot 配置，默认使用 DEFAULT_STAGE_SLOTS
        """
        self.stage_configs = stage_configs or DEFAULT_STAGE_SLOTS
    
    def create_initial_state(self) -> FSMState:
        """创建初始状态"""
        state = FSMState(
            current_stage=SalesStage.OPENING,
            stage_history=[SalesStage.OPENING],
            slot_values={},
            stage_coverages={},
            turn_count=0,
            npc_mood=0.5,
            goal_achieved={stage.value: False for stage in SalesStage if stage != SalesStage.COMPLETED},
        )
        # 初始化各阶段覆盖率
        for stage, config in self.stage_configs.items():
            state.stage_coverages[stage.value] = SlotCoverage(
                stage=stage,
                total_slots=len(config.slots),
                filled_slots=0,
                required_filled=0,
                required_total=len([s for s in config.slots if s.required]),
            )
        return state
    
    def update_slot(
        self,
        state: FSMState,
        slot_name: str,
        value: str,
        confidence: float,
        turn: int,
        source_utterance: str,
    ) -> FSMState:
        """
        更新 Slot 值
        
        Args:
            state: 当前状态
            slot_name: Slot 名称
            value: 填充值
            confidence: 置信度
            turn: 当前轮次
            source_utterance: 来源话语
            
        Returns:
            更新后的状态
        """
        # 查找 Slot 所属阶段
        slot_stage: Optional[SalesStage] = None
        slot_required: bool = False
        
        for stage, config in self.stage_configs.items():
            for slot_def in config.slots:
                if slot_def.name == slot_name:
                    slot_stage = stage
                    slot_required = slot_def.required
                    break
            if slot_stage:
                break
        
        if not slot_stage:
            logger.warning(f"Unknown slot: {slot_name}")
            return state
        
        # 更新 Slot 值
        is_new_fill = slot_name not in state.slot_values or state.slot_values[slot_name].value is None
        
        state.slot_values[slot_name] = SlotValue(
            slot_name=slot_name,
            value=value,
            confidence=confidence,
            extracted_at_turn=turn,
            source_utterance=source_utterance,
        )
        
        # 更新覆盖率
        if is_new_fill:
            coverage = state.stage_coverages.get(slot_stage.value)
            if coverage:
                coverage.filled_slots += 1
                if slot_required:
                    coverage.required_filled += 1
        
        logger.info(f"Slot updated: {slot_name} = {value} (confidence: {confidence})")
        return state
    
    def calculate_stage_coverage(self, state: FSMState, stage: SalesStage) -> SlotCoverage:
        """
        计算指定阶段的 Slot 覆盖率
        
        Args:
            state: 当前状态
            stage: 目标阶段
            
        Returns:
            覆盖率统计
        """
        config = self.stage_configs.get(stage)
        if not config:
            return SlotCoverage(
                stage=stage,
                total_slots=0,
                filled_slots=0,
                required_filled=0,
                required_total=0,
            )
        
        filled = 0
        required_filled = 0
        required_total = 0
        
        for slot_def in config.slots:
            if slot_def.required:
                required_total += 1
            
            slot_value = state.slot_values.get(slot_def.name)
            if slot_value and slot_value.value is not None and slot_value.confidence >= 0.5:
                filled += 1
                if slot_def.required:
                    required_filled += 1
        
        return SlotCoverage(
            stage=stage,
            total_slots=len(config.slots),
            filled_slots=filled,
            required_filled=required_filled,
            required_total=required_total,
        )
    
    def evaluate_transition(
        self,
        state: FSMState,
        goal_achieved: bool,
    ) -> TransitionDecision:
        """
        评估是否应该进行状态转换
        
        基于以下条件判断：
        1. Slot 覆盖率 >= min_coverage_to_advance
        2. 阶段目标达成 (goal_achieved = True)
        
        Args:
            state: 当前状态
            goal_achieved: 当前阶段目标是否达成（由 Evaluator 判断）
            
        Returns:
            转换决策
        """
        current_stage = state.current_stage
        
        # 已完成状态不再转换
        if current_stage == SalesStage.COMPLETED:
            return TransitionDecision(
                should_transition=False,
                from_stage=current_stage,
                to_stage=None,
                reason="训练已完成",
                slot_coverage=1.0,
                goal_achieved=True,
            )
        
        # 获取当前阶段配置
        config = self.stage_configs.get(current_stage)
        if not config:
            return TransitionDecision(
                should_transition=False,
                from_stage=current_stage,
                to_stage=None,
                reason=f"未找到阶段配置: {current_stage.value}",
                slot_coverage=0.0,
                goal_achieved=False,
            )
        
        # 计算当前覆盖率
        coverage = self.calculate_stage_coverage(state, current_stage)
        coverage_rate = coverage.required_coverage_rate
        
        # 更新状态中的覆盖率
        state.stage_coverages[current_stage.value] = coverage
        
        # 判断是否满足转换条件
        coverage_met = coverage_rate >= config.min_coverage_to_advance
        
        if not coverage_met:
            return TransitionDecision(
                should_transition=False,
                from_stage=current_stage,
                to_stage=None,
                reason=f"Slot 覆盖率不足: {coverage_rate:.1%} < {config.min_coverage_to_advance:.1%}",
                slot_coverage=coverage_rate,
                goal_achieved=goal_achieved,
            )
        
        if not goal_achieved:
            return TransitionDecision(
                should_transition=False,
                from_stage=current_stage,
                to_stage=None,
                reason="阶段目标尚未达成",
                slot_coverage=coverage_rate,
                goal_achieved=goal_achieved,
            )
        
        # 确定下一阶段
        next_stage = self._get_next_stage(current_stage)
        
        return TransitionDecision(
            should_transition=True,
            from_stage=current_stage,
            to_stage=next_stage,
            reason=f"满足转换条件: 覆盖率 {coverage_rate:.1%}, 目标达成",
            slot_coverage=coverage_rate,
            goal_achieved=goal_achieved,
            confidence=min(coverage_rate, 1.0),
        )
    
    def execute_transition(self, state: FSMState, decision: TransitionDecision) -> FSMState:
        """
        执行状态转换
        
        Args:
            state: 当前状态
            decision: 转换决策
            
        Returns:
            更新后的状态
        """
        if not decision.should_transition or not decision.to_stage:
            return state
        
        # 记录目标达成
        state.goal_achieved[decision.from_stage.value] = True
        
        # 更新阶段
        state.current_stage = decision.to_stage
        state.stage_history.append(decision.to_stage)
        
        logger.info(f"FSM Transition: {decision.from_stage.value} -> {decision.to_stage.value}")
        logger.info(f"Reason: {decision.reason}")
        
        return state
    
    def update_mood(self, state: FSMState, delta: float) -> FSMState:
        """
        更新 NPC 情绪值
        
        Args:
            state: 当前状态
            delta: 情绪变化量 (-1.0 到 1.0)
            
        Returns:
            更新后的状态
        """
        new_mood = max(0.0, min(1.0, state.npc_mood + delta))
        state.npc_mood = new_mood
        return state
    
    def increment_turn(self, state: FSMState) -> FSMState:
        """增加轮次计数"""
        state.turn_count += 1
        return state
    
    def _get_next_stage(self, current: SalesStage) -> Optional[SalesStage]:
        """获取下一阶段"""
        try:
            current_idx = self.STAGE_ORDER.index(current)
            if current_idx < len(self.STAGE_ORDER) - 1:
                return self.STAGE_ORDER[current_idx + 1]
        except ValueError:
            pass
        return None
    
    def get_stage_config(self, stage: SalesStage) -> Optional[StageSlotConfig]:
        """获取阶段配置"""
        return self.stage_configs.get(stage)
    
    def get_current_slots(self, state: FSMState) -> List[str]:
        """获取当前阶段需要填充的 Slot 列表"""
        config = self.stage_configs.get(state.current_stage)
        if not config:
            return []
        return [slot.name for slot in config.slots]
    
    def get_missing_slots(self, state: FSMState) -> List[str]:
        """获取当前阶段缺失的必填 Slot"""
        config = self.stage_configs.get(state.current_stage)
        if not config:
            return []
        
        missing = []
        for slot_def in config.slots:
            if slot_def.required:
                slot_value = state.slot_values.get(slot_def.name)
                if not slot_value or slot_value.value is None or slot_value.confidence < 0.5:
                    missing.append(slot_def.name)
        
        return missing
