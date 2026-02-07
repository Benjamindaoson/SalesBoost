from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .strategy import StrategyObject, Evidence

class StateConfidence(BaseModel):
    """状态置信度 (State Confidence) - 满分版关键字段"""
    value: float = Field(..., ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    method: str = Field(..., description="估计方法: llm_heuristic, rule_based, etc.")

class CustomerPsychology(BaseModel):
    """客户心理状态估计"""
    trust: float = Field(0.5, ge=0.0, le=1.0)
    resistance: float = Field(0.3, ge=0.0, le=1.0)
    interest: float = Field(0.5, ge=0.0, le=1.0)
    confidence: StateConfidence  # 整体心理估计的置信度

class SalesStageEstimate(BaseModel):
    """销售阶段估计"""
    current: str
    previous: Optional[str] = None
    transition_timestamp: Optional[datetime] = None
    confidence: StateConfidence

class DecisionTrace(BaseModel):
    """决策轨迹 - 用于回放与审计"""
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    intent_detected: str
    active_branch: str  # Parallel_Work, Fast_Path, etc.
    mentor_candidates_count: int
    selected_strategy_id: Optional[str]
    auditor_action: str  # PASS, REWRITE, BLOCK
    reasoning: str = Field(..., description="Director 仲裁的最终理由")
    caller_role: Optional[str] = Field(None, description="触发本轮决策的角色，如 session_director")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="本轮工具调用审计列表，需包含 tool_call_id/caller_role")

class RealTimeTelemetry(BaseModel):
    """实时遥测 - 生产环境/Live模式专用"""
    speech_rate_wpm: Optional[float] = None  # 语速
    interruption_count: int = 0  # 打断次数
    silence_duration_ms: float = 0.0  # 沉默时长
    sentiment_valence: float = 0.0  # 情感效价 (-1.0 ~ 1.0)
    background_noise_level: str = "low"  # low, medium, high

class ExternalContext(BaseModel):
    """外部上下文 - 连接 CRM/Meeting 等真实世界系统"""
    crm_opportunity_id: Optional[str] = None
    crm_stage_mapped: Optional[str] = None  # 映射到 Salesforce/HubSpot 的阶段
    meeting_platform: str = "simulation"  # zoom, teams, simulation
    participants: List[str] = Field(default_factory=list)

class PendingAction(BaseModel):
    """待执行动作 - Agent 不仅是建议，而是执行 (Agentic Workflow)"""
    action_type: str  # e.g., "update_crm", "send_slack_alert", "push_battlecard"
    payload: Dict[str, Any]
    status: str = "pending"  # pending, executed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BlackboardSchema(BaseModel):
    """
    SalesBoost Blackboard (共享黑板) - 系统的真相来源 (Source of Truth)
    符合闭环控制系统架构，支持策略显式化、证据链与全量遥测。
    Updated for 2026 Agentic Architecture: 支持实时遥测与外部动作执行。
    """
    # 1. 基础信息 (Session Context)
    session_id: str
    user_id: str
    turn_count: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    mode: str = "simulation"  # simulation vs live_shadow
    
    # 2. 状态估计 (State Estimation - 一等公民)
    stage_estimate: SalesStageEstimate
    psychology: CustomerPsychology
    last_intent: Optional[str] = None
    
    # 2.1 实时信号 (Real-time Signals - 硅谷标准)
    telemetry: RealTimeTelemetry = Field(default_factory=RealTimeTelemetry)
    external_context: ExternalContext = Field(default_factory=ExternalContext)

    # 3. 决策空间 (Decision Space - 策略显式化)
    current_strategy_candidates: List[StrategyObject] = Field(default_factory=list)
    selected_strategy: Optional[StrategyObject] = None
    
    # 4. 证据与约束 (Evidence & Constraints)
    active_evidence: List[Evidence] = Field(default_factory=list)
    compliance_flags: List[str] = Field(default_factory=list)
    risk_labels: Dict[str, Any] = Field(default_factory=dict)
    
    # 5. 闭环反馈 (Closed-loop Feedback)
    adoption_signal: Optional[str] = Field(None, description="ACCEPTED, REJECTED, PARTIAL, DELAYED")
    adoption_notes: Optional[str] = None
    
    # 6. 代理动作 (Agentic Actions - 从 Copilot 到 Autopilot)
    pending_actions: List[PendingAction] = Field(default_factory=list)

    # 7. 遥测与回放 (Telemetry & Trace)
    history: List[DecisionTrace] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
