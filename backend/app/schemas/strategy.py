"""
策略分类体系 Schema
销售决策策略模型
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────
# Core building blocks (referenced by blackboard.py)
# ─────────────────────────────────────────────────

class EvidenceType(str, Enum):
    """证据来源类型"""
    INTENT = "intent"
    HISTORY = "history"
    RAG = "rag"
    POLICY_DOC = "policy_doc"
    MANUAL = "manual"


class Evidence(BaseModel):
    """证据条目 — 支撑策略决策的信号或观察."""
    id: str = Field(..., alias="evidence_id", description="唯一证据 ID")
    source_type: EvidenceType = Field(default=EvidenceType.INTENT, alias="source", description="证据来源类型")
    content_snippet: str = Field(..., alias="content", description="证据内容摘要")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class StrategyCategory(str, Enum):
    """策略类别"""
    VALUE_PROPOSITION = "value_proposition"
    NEEDS_DISCOVERY = "needs_discovery"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING_TECHNIQUE = "closing_technique"
    RELATIONSHIP_BUILDING = "relationship_building"


class StrategyObject(BaseModel):
    """策略候选对象 — 策略决策引擎的核心数据结构."""
    strategy_id: str = Field(..., description="策略唯一 ID")
    strategy_name: Optional[str] = Field(None, description="策略名称")
    category: StrategyCategory = Field(default=StrategyCategory.VALUE_PROPOSITION, description="策略类别")
    hypothesis: str = Field(default="", description="策略假设/原因")
    description: Optional[str] = Field(None, description="策略描述")
    expected_effect: Dict[str, float] = Field(default_factory=dict, description="期望效果")
    script_candidates: List[str] = Field(default_factory=list, description="话术候选")
    evidence: List[Evidence] = Field(default_factory=list, description="相关证据")
    risks: List[str] = Field(default_factory=list, description="潜在风险")
    
    # Legacy fields
    situation_type: Optional[str] = None
    priority: int = 1
    confidence: float = 1.0
    is_golden: bool = False

    model_config = ConfigDict(populate_by_name=True)


class StrategyResponse(BaseModel):
    """策略建议响应"""
    candidates: List[StrategyObject]
    primary_recommendation_id: str
    reasoning: str


class SituationType(str, Enum):
    """情境类型"""
    # OPENING 阶段
    COLD_CALL = "cold_call"
    WARM_REFERRAL = "warm_referral"
    INBOUND_INQUIRY = "inbound_inquiry"
    
    # NEEDS_DISCOVERY 阶段
    SURFACE_NEED = "surface_need"
    HIDDEN_PAIN = "hidden_pain"
    BUDGET_PROBE = "budget_probe"
    DECISION_MAKER_CHECK = "decision_maker_check"
    
    # PRODUCT_INTRO 阶段
    FEATURE_DEMO = "feature_demo"
    VALUE_PROPOSITION = "value_proposition"
    COMPETITIVE_COMPARISON = "competitive_comparison"
    
    # OBJECTION_HANDLING 阶段
    PRICE_OBJECTION = "price_objection"
    TIMING_OBJECTION = "timing_objection"
    TRUST_OBJECTION = "trust_objection"
    COMPETITOR_OBJECTION = "competitor_objection"
    AUTHORITY_OBJECTION = "authority_objection"
    
    # CLOSING 阶段
    SOFT_CLOSE = "soft_close"
    HARD_CLOSE = "hard_close"
    TRIAL_CLOSE = "trial_close"


# 策略库：每种情境下的可用策略及最优策略
STRATEGY_TAXONOMY: Dict[SituationType, Dict] = {
    SituationType.PRICE_OBJECTION: {
        "available": [
            "reframe_value",
            "compare_competitors",
            "offer_tradeoff",
            "delay_decision",
            "break_down_cost",
            "roi_calculation",
        ],
        "golden": "reframe_value",
        "description": "价格异议处理",
    },
    SituationType.TIMING_OBJECTION: {
        "available": [
            "create_urgency",
            "future_pace",
            "cost_of_delay",
            "trial_offer",
        ],
        "golden": "cost_of_delay",
        "description": "时机异议处理",
    },
    SituationType.TRUST_OBJECTION: {
        "available": [
            "social_proof",
            "case_study",
            "guarantee_offer",
            "expert_endorsement",
        ],
        "golden": "case_study",
        "description": "信任异议处理",
    },
    SituationType.BUDGET_PROBE: {
        "available": [
            "direct_ask",
            "range_anchor",
            "value_first",
            "competitor_reference",
        ],
        "golden": "range_anchor",
        "description": "预算探测",
    },
    SituationType.HIDDEN_PAIN: {
        "available": [
            "deep_probe",
            "implication_question",
            "pain_amplify",
            "future_vision",
        ],
        "golden": "implication_question",
        "description": "隐藏痛点挖掘",
    },
}


class StrategyAnalysis(BaseModel):
    """策略分析结果 - Evaluator 输出"""
    situation_type: str = Field(..., description="情境类型")
    strategy_chosen: str = Field(..., description="用户选择的策略")
    action_units: List[str] = Field(default_factory=list, description="策略动作单元分解")
    available_strategies: List[str] = Field(default_factory=list, description="可用策略列表")
    is_optimal: bool = Field(..., description="是否为最优策略")
    golden_strategy: str = Field(..., description="该情境下的最优策略")
    optimality_reason: str = Field(..., description="最优/非最优原因分析")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class StrategyGuidance(BaseModel):
    """策略级指导 - Coach 输出升级"""
    current_strategy: str = Field(..., description="你当前使用的策略")
    current_strategy_analysis: str = Field(..., description="当前策略分析")
    golden_strategy: str = Field(..., description="该情境下的最优策略")
    why_golden_better: str = Field(..., description="为什么最优策略更有效")
    transition_suggestion: str = Field(..., description="如何从当前策略过渡到最优策略")
    example_utterance: str = Field(..., description="最优策略的示例话术")


class AdoptionAnalysis(BaseModel):
    """采纳分析结果"""
    suggestion_id: str
    adopted: bool
    adoption_style: str
    adoption_evidence: Optional[str] = None
    baseline_scores: Dict[str, float]
    observed_scores: Dict[str, float]
    skill_delta: Dict[str, float]
    is_effective: bool
    effectiveness_score: float
    feedback_signal: str = Field(default="NO_ACTION", description="学习反馈信号: FIRST_TIME_ACTION / EFFECTIVE_ADOPTION / NO_IMPROVEMENT / NO_ACTION")
    feedback_text: str = Field(default="", description="人类可读的反馈文本")


class CurriculumPlan(BaseModel):
    """训练计划"""
    next_training_plan: List["TrainingFocus"] = Field(default_factory=list)
    reasoning: str = Field(..., description="为什么推荐这个训练计划")
    expected_improvement: Dict[str, float] = Field(default_factory=dict)


class TrainingFocus(BaseModel):
    """单个训练焦点"""
    stage: str = Field(..., description="训练阶段")
    focus_slots: List[str] = Field(default_factory=list, description="重点 Slot")
    focus_strategy: str = Field(..., description="重点策略")
    focus_situation: str = Field(..., description="重点情境")
    npc_persona_traits: List[str] = Field(default_factory=list, description="NPC 人设特征")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    priority: int = Field(default=1, ge=1, le=5, description="优先级 1-5")


CurriculumPlan.model_rebuild()
