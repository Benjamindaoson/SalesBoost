"""
Agent 输出 Schema 定义
所有 Agent 必须返回严格的 Pydantic Model
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from schemas.fsm import FSMState, TransitionDecision

# ============================================================
# Intent Gate Output
# ============================================================

class DetectedSlot(BaseModel):
    """检测到的 Slot"""
    slot_name: str
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_span: Optional[str] = None


class IntentGateOutput(BaseModel):
    """Intent Gate 输出"""
    detected_intent: str = Field(..., description="检测到的用户意图")
    is_aligned: bool = Field(..., description="是否与当前 FSM 阶段对齐")
    alignment_reason: str = Field(..., description="对齐/不对齐的原因")
    detected_slots: List[DetectedSlot] = Field(default_factory=list, description="检测到的 Slot 填充")
    missing_slots: List[str] = Field(default_factory=list, description="当前阶段缺失的 Slot")
    suggested_redirect: Optional[str] = Field(None, description="如果不对齐，建议的引导话术")
    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================
# NPC Agent Output
# ============================================================

class NPCOutput(BaseModel):
    """NPC Agent 输出"""
    response: str = Field(..., description="NPC 客户回复")
    mood_before: float = Field(..., ge=0.0, le=1.0, description="回复前情绪值")
    mood_after: float = Field(..., ge=0.0, le=1.0, description="回复后情绪值")
    mood_change_reason: str = Field(..., description="情绪变化原因")
    expressed_signals: List[str] = Field(default_factory=list, description="表达的信号（兴趣/疑虑/反对等）")
    persona_consistency: float = Field(..., ge=0.0, le=1.0, description="人设一致性得分")


# ============================================================
# Coach Agent Output
# ============================================================

class CoachOutput(BaseModel):
    """Coach Agent 输出 - 战术指导"""
    suggestion: str = Field(..., description="具体建议")
    reasoning: str = Field(..., description="建议理由")
    example_utterance: str = Field(..., description="示例话术")
    priority: str = Field(..., description="优先级: high/medium/low")
    technique_name: str = Field(..., description="使用的销售技巧名称")
    stage_alignment: bool = Field(..., description="建议是否与当前阶段对齐")
    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================
# Evaluator Agent Output - 五维评分
# ============================================================

class DimensionScore(BaseModel):
    """单维度评分"""
    score: float = Field(..., ge=0.0, le=10.0, description="0-10 分")
    feedback: str = Field(..., description="评分反馈")
    evidence: Optional[str] = Field(None, description="评分依据（引用原文）")


class EvaluatorOutput(BaseModel):
    """Evaluator Agent 输出 - 五维评分"""
    # 五维评分（PRD 强制要求）
    integrity: DimensionScore = Field(..., description="完整性 - 信息是否完整")
    relevance: DimensionScore = Field(..., description="相关性 - 是否切题")
    correctness: DimensionScore = Field(..., description="正确性 - 信息是否准确")
    logic: DimensionScore = Field(..., description="逻辑性 - 表达是否有条理")
    compliance: DimensionScore = Field(..., description="合规性 - 是否符合规范")
    
    # 聚合分数
    overall_score: float = Field(..., ge=0.0, le=10.0, description="综合得分")
    
    # 阶段目标判断
    goal_advanced: bool = Field(..., description="是否推进了阶段目标")
    goal_feedback: str = Field(..., description="目标推进反馈")
    
    # Slot 提取
    extracted_slots: List[DetectedSlot] = Field(default_factory=list, description="本轮提取的 Slot")
    
    # 改进建议
    improvement_points: List[str] = Field(default_factory=list, description="改进点")
    
    @property
    def dimension_scores(self) -> Dict[str, float]:
        """获取五维分数字典"""
        return {
            "integrity": self.integrity.score,
            "relevance": self.relevance.score,
            "correctness": self.correctness.score,
            "logic": self.logic.score,
            "compliance": self.compliance.score,
        }


# ============================================================
# RAG Agent Output
# ============================================================

class RAGItem(BaseModel):
    """RAG 检索结果项"""
    content: str = Field(..., description="检索内容")
    source_citations: List[str] = Field(..., description="来源引用（必须可追溯）")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    content_type: str = Field(..., description="内容类型: script/case/strategy/faq")


class RAGOutput(BaseModel):
    """RAG Agent 输出"""
    retrieved_content: List[RAGItem] = Field(default_factory=list)
    query_understanding: str = Field(..., description="查询理解")
    no_result_fallback: bool = Field(default=False, description="是否触发兜底")
    fallback_reason: Optional[str] = Field(None, description="兜底原因")


# ============================================================
# Compliance Agent Output
# ============================================================

class RiskFlag(BaseModel):
    """风险标记"""
    risk_type: str = Field(..., description="风险类型: exaggeration/misleading/prohibited")
    original_text: str = Field(..., description="原始文本")
    risk_reason: str = Field(..., description="风险原因")
    severity: str = Field(..., description="严重程度: high/medium/low")
    safe_alternative: Optional[str] = Field(None, description="安全替代表述")


class ComplianceOutput(BaseModel):
    """Compliance Agent 输出"""
    is_compliant: bool = Field(..., description="是否合规")
    risk_flags: List[RiskFlag] = Field(default_factory=list, description="风险标记列表")
    blocked: bool = Field(default=False, description="是否被拦截")
    block_reason: Optional[str] = Field(None, description="拦截原因")
    sanitized_message: Optional[str] = Field(None, description="净化后的消息（如果需要）")
    # MVP 增强字段
    risk_level: str = Field(default="OK", description="风险等级: OK/WARN/BLOCK")
    safe_rewrite: Optional[str] = Field(None, description="完整的安全改写版本（短句，可直接替换发送）")


# ============================================================
# Orchestrator Turn Result
# ============================================================

class OrchestratorTurnResult(BaseModel):
    """Orchestrator 单轮处理结果"""
    turn_number: int
    user_message: str
    
    # 各 Agent 输出
    intent_result: IntentGateOutput
    rag_result: RAGOutput
    compliance_result: ComplianceOutput
    npc_result: NPCOutput
    coach_result: CoachOutput
    evaluator_result: EvaluatorOutput
    
    # 策略分析（销冠能力复制系统）
    strategy_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="策略分析结果"
    )
    strategy_guidance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="策略级指导"
    )
    adoption_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="采纳分析结果"
    )
    
    # FSM 状态
    transition_decision: TransitionDecision
    fsm_state_snapshot: FSMState
    
    # 元数据
    processing_time_ms: float
    timestamp: str


class SessionCompleteResult(BaseModel):
    """会话结束结果 (Session Completion)"""
    session_id: str
    final_score: float
    duration_seconds: int
    curriculum_plan: Optional[Dict[str, Any]] = None  # CurriculumPlanner output
