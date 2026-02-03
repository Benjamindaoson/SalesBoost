from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class StrategyCategory(str, Enum):
    """8 大销售环节策略分类 (8 Major Sales Strategy Categories)"""
    OPENING_HOOK = "opening_hook"             # 开场破冰
    NEEDS_DISCOVERY = "needs_discovery"       # 需求挖掘
    VALUE_PROPOSITION = "value_proposition"   # 价值主张
    OBJECTION_HANDLING = "objection_handling" # 异议处理
    CLOSING_TRIAL = "closing_trial"           # 试探性成交
    URGENCY_CREATION = "urgency_creation"     # 营造紧迫感
    TRUST_BUILDING = "trust_building"         # 信任建立
    FOLLOW_UP = "follow_up"                   # 随访跟进

class EvidenceType(str, Enum):
    KNOWLEDGE_BASE = "kb"
    DATABASE = "db"
    POLICY_DOC = "policy"

class Evidence(BaseModel):
    """证据链对象 (Evidence Chain Object)"""
    id: str
    source_type: EvidenceType
    content_snippet: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class StrategyObject(BaseModel):
    """
    策略对象 (Strategy Object) - 满分版系统的核心决策单元
    由 Mentor 生成，由 Director 仲裁执行。
    """
    strategy_id: str = Field(..., description="策略打法唯一标识")
    category: StrategyCategory
    hypothesis: str = Field(..., description="为什么适用此策略的假设依据")
    
    # 预期效果 (Expected Effect)
    expected_effect: Dict[str, float] = Field(
        ..., 
        description="预期对 Blackboard 变量的影响，如 {'trust': 0.2, 'resistance': -0.3}"
    )
    
    # 候选话术 (Script Candidates)
    script_candidates: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=3,
        description="2-3 个符合该策略的候选话术"
    )
    
    # 证据链 (Evidence Chain)
    evidence: List[Evidence] = Field(
        ..., 
        description="该策略所引用的事实依据（RAG/DB）"
    )
    
    # 风险评估 (Risk Assessment)
    risks: Optional[List[str]] = Field(
        None, 
        description="可能触发的合规或业务风险点"
    )

class StrategyResponse(BaseModel):
    """Mentor 的完整输出格式"""
    candidates: List[StrategyObject]
    primary_recommendation_id: str
    reasoning: str
