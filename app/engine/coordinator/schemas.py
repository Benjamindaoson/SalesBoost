from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, confloat, field_validator


class RiskSchema(BaseModel):
    compliance_risk: bool
    need_human: bool
    risk_reason: str = Field(default="", max_length=200)

    @field_validator("risk_reason")
    def _risk_reason_required(cls, v, info):
        data = info.data
        if (data.get("compliance_risk") or data.get("need_human")) and not v:
            raise ValueError("risk_reason required when risk is flagged")
        return v


class ReasoningSchema(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    analysis: List[str] = Field(min_length=1, max_length=3)
    core_concern: str = Field(..., max_length=200)
    strategy: str = Field(..., max_length=200)
    need_tools: bool
    why_not_tools: str = Field(default="", max_length=200)
    risk: RiskSchema
    confidence: confloat(ge=0.0, le=1.0)

    @field_validator("why_not_tools")
    def _why_not_tools_required(cls, v, info):
        if info.data.get("need_tools") is False and not v:
            raise ValueError("why_not_tools required when need_tools=false")
        return v


class RoutingPolicySchema(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    target_node: Literal["npc", "tools", "coach", "compliance", "human"]
    confidence: confloat(ge=0.0, le=1.0)
    reason: str = Field(..., max_length=200)
    candidates: List[Literal["npc", "tools", "coach", "compliance", "human"]]

    @field_validator("candidates")
    def _candidates_must_include_target(cls, v, info):
        if info.data.get("target_node") not in v:
            raise ValueError("candidates must include target_node")
        return v


class BanditContextSchema(BaseModel):
    intent: str
    confidence: confloat(ge=0.0, le=1.0)
    fsm_stage: str
    need_tools: bool
    risk_flags: List[str] = Field(default_factory=list)
    recent_tool_calls: bool


class BanditRequestSchema(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    context: BanditContextSchema
    candidates: List[Literal["npc", "tools", "coach", "compliance", "human"]]


class BanditResponseSchema(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    chosen: Literal["npc", "tools", "coach", "compliance", "human"]
    score: confloat(ge=0.0, le=1.0)
    exploration: bool


class BanditFeedbackSchema(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    decision_id: str
    chosen: Literal["npc", "tools", "coach", "compliance", "human"]
    reward: confloat(ge=-1.0, le=1.0)
    signals: Dict[str, float]
