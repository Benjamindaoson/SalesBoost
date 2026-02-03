"""
FSM 状态与 Slot Schema 定义
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


class SalesStage(str, Enum):
    """销售流程五大阶段"""
    OPENING = "OPENING"                    # 破冰建联
    NEEDS_DISCOVERY = "NEEDS_DISCOVERY"    # 需求挖掘
    PRODUCT_INTRO = "PRODUCT_INTRO"        # 产品介绍
    OBJECTION_HANDLING = "OBJECTION_HANDLING"  # 异议处理
    CLOSING = "CLOSING"                    # 促单成交
    COMPLETED = "COMPLETED"                # 训练完成


class SlotDefinition(BaseModel):
    """单个 Slot 定义"""
    name: str = Field(..., description="Slot 名称")
    description: str = Field(..., description="Slot 描述")
    required: bool = Field(default=True, description="是否必填")
    stage: SalesStage = Field(..., description="所属阶段")
    extraction_hint: str = Field(..., description="提取提示词")


class SlotValue(BaseModel):
    """Slot 填充值"""
    slot_name: str
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at_turn: Optional[int] = None
    source_utterance: Optional[str] = None


class StageSlotConfig(BaseModel):
    """阶段 Slot 配置"""
    stage: SalesStage
    slots: List[SlotDefinition]
    min_coverage_to_advance: float = Field(default=0.7, ge=0.0, le=1.0, description="推进到下一阶段的最低覆盖率")
    goal_description: str = Field(..., description="阶段目标描述")


class SlotCoverage(BaseModel):
    """Slot 覆盖率统计"""
    stage: SalesStage
    total_slots: int
    filled_slots: int
    required_filled: int
    required_total: int
    
    @computed_field
    @property
    def coverage_rate(self) -> float:
        """总体覆盖率"""
        if self.total_slots == 0:
            return 1.0
        return self.filled_slots / self.total_slots
    
    @computed_field
    @property
    def required_coverage_rate(self) -> float:
        """必填项覆盖率"""
        if self.required_total == 0:
            return 1.0
        return self.required_filled / self.required_total


class FSMState(BaseModel):
    """FSM 完整状态"""
    current_stage: SalesStage = Field(default=SalesStage.OPENING)
    stage_history: List[SalesStage] = Field(default_factory=list)
    slot_values: Dict[str, SlotValue] = Field(default_factory=dict)
    stage_coverages: Dict[str, SlotCoverage] = Field(default_factory=dict)
    turn_count: int = Field(default=0)
    npc_mood: float = Field(default=0.5, ge=0.0, le=1.0)
    goal_achieved: Dict[str, bool] = Field(default_factory=dict, description="各阶段目标是否达成")
    
    def get_current_coverage(self) -> Optional[SlotCoverage]:
        """获取当前阶段覆盖率"""
        return self.stage_coverages.get(self.current_stage.value)


class TransitionDecision(BaseModel):
    """状态转换决策"""
    should_transition: bool = Field(..., description="是否应该转换")
    from_stage: SalesStage
    to_stage: Optional[SalesStage] = None
    reason: str = Field(..., description="决策原因")
    slot_coverage: float = Field(..., description="当前 Slot 覆盖率")
    goal_achieved: bool = Field(..., description="阶段目标是否达成")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# 默认 Slot 配置
DEFAULT_STAGE_SLOTS: Dict[SalesStage, StageSlotConfig] = {
    SalesStage.OPENING: StageSlotConfig(
        stage=SalesStage.OPENING,
        goal_description="建立信任关系，获取客户基本信息",
        min_coverage_to_advance=0.6,
        slots=[
            SlotDefinition(
                name="customer_name",
                description="客户姓名",
                required=True,
                stage=SalesStage.OPENING,
                extraction_hint="从对话中提取客户的姓名或称呼"
            ),
            SlotDefinition(
                name="greeting_completed",
                description="是否完成问候",
                required=True,
                stage=SalesStage.OPENING,
                extraction_hint="判断销售是否进行了礼貌的开场问候"
            ),
            SlotDefinition(
                name="rapport_established",
                description="是否建立初步信任",
                required=False,
                stage=SalesStage.OPENING,
                extraction_hint="判断是否通过寒暄或共同话题建立了初步信任"
            ),
        ]
    ),
    SalesStage.NEEDS_DISCOVERY: StageSlotConfig(
        stage=SalesStage.NEEDS_DISCOVERY,
        goal_description="挖掘客户核心需求和痛点",
        min_coverage_to_advance=0.7,
        slots=[
            SlotDefinition(
                name="pain_point",
                description="客户痛点",
                required=True,
                stage=SalesStage.NEEDS_DISCOVERY,
                extraction_hint="提取客户明确表达的问题或困扰"
            ),
            SlotDefinition(
                name="budget_range",
                description="预算范围",
                required=True,
                stage=SalesStage.NEEDS_DISCOVERY,
                extraction_hint="提取客户的预算信息或价格敏感度"
            ),
            SlotDefinition(
                name="decision_timeline",
                description="决策时间线",
                required=False,
                stage=SalesStage.NEEDS_DISCOVERY,
                extraction_hint="提取客户的购买时间计划"
            ),
            SlotDefinition(
                name="decision_maker",
                description="决策人信息",
                required=False,
                stage=SalesStage.NEEDS_DISCOVERY,
                extraction_hint="判断当前联系人是否为最终决策人"
            ),
        ]
    ),
    SalesStage.PRODUCT_INTRO: StageSlotConfig(
        stage=SalesStage.PRODUCT_INTRO,
        goal_description="针对需求介绍产品价值",
        min_coverage_to_advance=0.7,
        slots=[
            SlotDefinition(
                name="value_proposition_delivered",
                description="是否传递核心价值主张",
                required=True,
                stage=SalesStage.PRODUCT_INTRO,
                extraction_hint="判断销售是否清晰传递了产品的核心价值"
            ),
            SlotDefinition(
                name="feature_benefit_linked",
                description="功能与利益是否关联",
                required=True,
                stage=SalesStage.PRODUCT_INTRO,
                extraction_hint="判断销售是否将产品功能与客户利益关联"
            ),
            SlotDefinition(
                name="customer_interest_signal",
                description="客户兴趣信号",
                required=False,
                stage=SalesStage.PRODUCT_INTRO,
                extraction_hint="提取客户对产品表现出的兴趣信号"
            ),
        ]
    ),
    SalesStage.OBJECTION_HANDLING: StageSlotConfig(
        stage=SalesStage.OBJECTION_HANDLING,
        goal_description="有效处理客户异议",
        min_coverage_to_advance=0.8,
        slots=[
            SlotDefinition(
                name="objection_identified",
                description="异议是否被识别",
                required=True,
                stage=SalesStage.OBJECTION_HANDLING,
                extraction_hint="提取客户提出的具体异议或顾虑"
            ),
            SlotDefinition(
                name="objection_addressed",
                description="异议是否被处理",
                required=True,
                stage=SalesStage.OBJECTION_HANDLING,
                extraction_hint="判断销售是否针对异议给出了有效回应"
            ),
            SlotDefinition(
                name="customer_concern_resolved",
                description="客户顾虑是否消除",
                required=False,
                stage=SalesStage.OBJECTION_HANDLING,
                extraction_hint="判断客户的顾虑是否得到缓解"
            ),
        ]
    ),
    SalesStage.CLOSING: StageSlotConfig(
        stage=SalesStage.CLOSING,
        goal_description="推动成交或明确下一步",
        min_coverage_to_advance=0.8,
        slots=[
            SlotDefinition(
                name="closing_attempt",
                description="是否尝试促单",
                required=True,
                stage=SalesStage.CLOSING,
                extraction_hint="判断销售是否主动尝试促成交易"
            ),
            SlotDefinition(
                name="next_step_agreed",
                description="是否约定下一步",
                required=True,
                stage=SalesStage.CLOSING,
                extraction_hint="判断是否与客户约定了明确的下一步行动"
            ),
            SlotDefinition(
                name="commitment_obtained",
                description="是否获得承诺",
                required=False,
                stage=SalesStage.CLOSING,
                extraction_hint="判断是否获得客户的购买承诺或意向确认"
            ),
        ]
    ),
}
