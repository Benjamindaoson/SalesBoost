"""
API v1 - 请求/响应 Pydantic 模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CoachProcessRequest(BaseModel):
    """POST /coach/process 请求体"""
    session_id: str = Field(..., description="会话 ID")
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="对话历史 [{\"role\": \"sales\"|\"customer\", \"content\": \"...\"}]",
    )
    text_stream: Optional[str] = Field(
        None,
        description="本 turn 实时转写文本（可选）；会追加为 sales 最新一条",
    )
    current_context: Optional[Dict[str, Any]] = Field(None, description="当前上下文（可选）")
    turn_number: int = Field(1, ge=1, description="轮次号")


class CoachProcessResponse(BaseModel):
    """POST /coach/process 标准化 JSON 响应"""
    success: bool = Field(..., description="是否成功")
    phase: str = Field(..., description="当前阶段")
    detected_phase: str = Field(..., description="识别到的阶段")
    phase_transition_detected: bool = Field(False, description="是否发生阶段跳转")
    customer_intent: str = Field(..., description="客户意图")
    action_advice: str = Field(..., description="行动建议")
    script_example: str = Field(..., description="推荐话术")
    compliance_risk: Optional[Dict[str, Any]] = Field(None, description="合规风险")
    error: Optional[str] = Field(None, description="错误信息（仅 success=false 时）")
