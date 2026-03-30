"""
Unified Agent I/O Schemas

All agent-to-agent and coordinator-to-agent communication MUST use these
Pydantic models for type safety, validation, and observability.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    NPC = "npc"
    COACH = "coach"
    EVALUATOR = "evaluator"
    RAG = "rag"
    COMPLIANCE = "compliance"


# ---------------------------------------------------------------------------
# NPC Output (replaces raw JSON)
# ---------------------------------------------------------------------------

class NPCAgentOutput(BaseModel):
    """NPC Agent 标准化输出"""
    content: str = Field(..., description="客户回复内容")
    mood: float = Field(..., ge=0.0, le=1.0, description="情绪值 0-1")
    next_stage_hint: Optional[str] = Field(None, description="阶段提示")
    expressed_signals: List[str] = Field(default_factory=list, description="表达的信号")


# ---------------------------------------------------------------------------
# Coach Output (replaces CoachAdvice dataclass)
# ---------------------------------------------------------------------------

class ComplianceRiskSchema(BaseModel):
    """合规风险"""
    risk_level: str = Field(..., description="high/medium/low")
    sensitive_words: List[str] = Field(default_factory=list)
    warning_message: str = Field(default="")


class CoachAgentOutput(BaseModel):
    """Coach Agent 标准化输出"""
    phase: str = Field(..., description="当前阶段")
    detected_phase: str = Field(..., description="检测到的阶段")
    phase_transition_detected: bool = Field(default=False)
    customer_intent: str = Field(..., description="客户意图")
    action_advice: str = Field(..., description="行动建议")
    script_example: str = Field(..., description="示例话术")
    compliance_risk: Optional[ComplianceRiskSchema] = None


# ---------------------------------------------------------------------------
# Blackboard / Coordinator Message (agent-to-agent)
# ---------------------------------------------------------------------------

class AgentMessage(BaseModel):
    """Agent 间传递的标准化消息"""
    source: AgentRole = Field(..., description="来源 Agent")
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    validated: bool = Field(default=True, description="是否已通过 Schema 校验")


def validate_npc_output(data: Any) -> NPCAgentOutput:
    """校验并返回 NPC 输出"""
    if isinstance(data, NPCAgentOutput):
        return data
    if isinstance(data, dict):
        return NPCAgentOutput(**data)
    raise ValueError(f"Invalid NPC output type: {type(data)}")


def validate_coach_output(data: Any) -> CoachAgentOutput:
    """校验并返回 Coach 输出"""
    if isinstance(data, CoachAgentOutput):
        return data
    if isinstance(data, dict):
        return _normalize_coach_dict(data)
    if hasattr(data, "dict"):
        d = data.dict() if callable(getattr(data, "dict", None)) else {}
        if not d and hasattr(data, "__dict__"):
            d = {k: v for k, v in vars(data).items() if not k.startswith("_")}
        return _normalize_coach_dict(d)
    raise ValueError(f"Invalid Coach output type: {type(data)}")


def _normalize_coach_dict(d: Dict[str, Any]) -> CoachAgentOutput:
    """将 phase/detected_phase 等枚举转为 str"""
    out = dict(d)
    for k in ("phase", "detected_phase"):
        if k in out and hasattr(out[k], "value"):
            out[k] = out[k].value
    if out.get("compliance_risk") and not isinstance(out["compliance_risk"], dict):
        cr = out["compliance_risk"]
        out["compliance_risk"] = (
            cr if isinstance(cr, dict) else
            {"risk_level": getattr(cr, "risk_level", "low"), "sensitive_words": getattr(cr, "sensitive_words", []), "warning_message": getattr(cr, "warning_message", "")}
        )
    return CoachAgentOutput(**out)
