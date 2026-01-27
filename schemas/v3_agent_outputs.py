"""
V3 Agent Output Schemas
6-Agent 架构的结构化输出定义
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ============================================================
# Session Director Output
# ============================================================

class TurnPlan(BaseModel):
    """Turn Plan - Session Director 输出"""
    turn_number: int
    path_mode: Literal["fast", "slow", "both"] = Field(..., description="路径模式")
    agents_to_call: List[str] = Field(..., description="需要调用的 Agent 列表")
    budget_allocation: Dict[str, float] = Field(..., description="预算分配：{agent: budget}")
    model_upgrade: bool = Field(default=False, description="是否升级模型")
    risk_level: str = Field(default="low", description="风险等级")
    evidence_confidence: float = Field(..., ge=0.0, le=1.0, description="证据置信度")
    reasoning: str = Field(..., description="决策理由")


# ============================================================
# Retriever Output
# ============================================================

class EvidenceItem(BaseModel):
    """证据项"""
    content: str
    source: str = Field(..., description="来源（文档标题/URL）")
    source_type: Literal["fact", "policy", "objection_playbook", "graph_insight"] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class EvidencePack(BaseModel):
    """Evidence Pack - Retriever 输出"""
    items: List[EvidenceItem] = Field(default_factory=list)
    retrieval_mode: Literal["lightweight", "graphrag"] = Field(..., description="检索模式")
    total_items: int = Field(default=0)
    confidence: float = Field(..., ge=0.0, le=1.0, description="整体置信度")
    retrieval_time_ms: float = Field(default=0.0)
    graph_nodes_visited: Optional[int] = Field(None, description="GraphRAG 节点数（如果使用）")


# ============================================================
# NPC Generator Output
# ============================================================

class NpcReply(BaseModel):
    """Npc Reply - NPC Generator 输出"""
    response: str = Field(..., description="NPC 回复内容")
    mood_before: float = Field(..., ge=0.0, le=1.0)
    mood_after: float = Field(..., ge=0.0, le=1.0)
    mood_change_reason: str
    expressed_signals: List[str] = Field(default_factory=list, description="表达的信号")
    persona_consistency: float = Field(..., ge=0.0, le=1.0)
    stage_alignment: bool = Field(..., description="是否与当前阶段对齐")


# ============================================================
# Coach Generator Output
# ============================================================

class CoachAdvice(BaseModel):
    """Coach Advice - Coach Generator 输出"""
    why: str = Field(..., description="为什么给出这个建议")
    action: str = Field(..., description="建议的行动")
    suggested_reply: str = Field(..., description="建议的话术（可直接复制）")
    alternatives: List[str] = Field(default_factory=list, description="备选话术")
    guardrails: List[str] = Field(default_factory=list, description="注意事项/风险提示")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    confidence: float = Field(..., ge=0.0, le=1.0)
    technique_name: Optional[str] = Field(None, description="使用的销售技巧")


# ============================================================
# Evaluator Output
# ============================================================

class DimensionScore(BaseModel):
    """维度评分 (1-5分)"""
    score: int = Field(..., ge=1, le=5, description="1-5 分评分")
    rationale: str = Field(..., description="评分理由")
    evidence: Optional[str] = Field(None, description="证据（引用原文）")


class ErrorTag(BaseModel):
    """错误标签"""
    tag: str = Field(..., description="错误类型")
    severity: Literal["critical", "major", "minor"] = Field(...)
    description: str
    suggestion: Optional[str] = Field(None, description="改进建议")


class Evaluation(BaseModel):
    """Evaluation - Evaluator 输出"""
    # 五维评分 (学问练评 - 评)
    integrity: DimensionScore = Field(..., description="完整性")
    relevance: DimensionScore = Field(..., description="相关性")
    correctness: DimensionScore = Field(..., description="正确性")
    logic: DimensionScore = Field(..., description="逻辑性")
    compliance: DimensionScore = Field(..., description="合规性")
    
    # 聚合分数 (1-5)
    overall_score: float = Field(..., ge=1.0, le=5.0)
    
    # 阶段目标判断
    goal_advanced: bool
    goal_feedback: str
    
    # 错误标签
    error_tags: List[ErrorTag] = Field(default_factory=list)
    
    # 合规标志
    compliance_flags: List[str] = Field(default_factory=list)
    
    # 阶段错误
    stage_mistakes: List[str] = Field(default_factory=list, description="阶段相关错误")
    
    # 一致性标记
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="评估一致性得分")
    
    task_resolution_bonus: float = Field(default=0.0, description="任务解决奖励分")
    turn_number: Optional[int] = None
    timestamp: Optional[str] = None


# ============================================================
# Adoption Tracker Output
# ============================================================

class AdoptionLog(BaseModel):
    """Adoption Log - Adoption Tracker 输出"""
    suggestion_id: Optional[str] = Field(None, description="建议ID")
    suggestion_text: str
    was_adopted: bool
    adoption_evidence: Optional[str] = Field(None, description="采纳证据")
    adoption_style: Literal["exact", "paraphrased", "concept", "not_adopted"] = Field(...)
    is_effective: bool = Field(..., description="是否有效采纳")
    skill_delta: float = Field(default=0.0, description="技能变化量")
    feedback_signal: Optional[str] = Field(None, description="反馈信号")
    resolved_tasks: List[str] = Field(default_factory=list, description="本轮解决的待办事项")
    task_bonus_score: float = Field(default=0.0, description="任务解决奖励分")
    turn_number: int
    timestamp: str


# ============================================================
# Fast Path Result
# ============================================================

class FastPathResult(BaseModel):
    """Fast Path 结果"""
    turn_number: int
    npc_reply: NpcReply
    evidence_pack: EvidencePack
    turn_plan: TurnPlan
    ttfs_ms: float = Field(..., description="Time To First Sentence (毫秒)")
    total_latency_ms: float = Field(..., description="总延迟")


# ============================================================
# Slow Path Result
# ============================================================

class SlowPathResult(BaseModel):
    """Slow Path 结果"""
    turn_number: int
    coach_advice: Optional[CoachAdvice] = None
    evaluation: Optional[Evaluation] = None
    adoption_log: Optional[AdoptionLog] = None
    total_latency_ms: float = Field(..., description="总延迟")


# ============================================================
# Turn Result (Combined)
# ============================================================

class V3TurnResult(BaseModel):
    """V3 Turn Result - 完整轮次结果"""
    turn_number: int
    fast_path_result: FastPathResult
    slow_path_result: Optional[SlowPathResult] = None
    session_id: str
    user_id: str
    timestamp: str
