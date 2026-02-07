"""
Intent classification schemas and enums
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class SalesStage(str, Enum):
    """销售阶段枚举"""
    OPENING = "opening"
    DISCOVERY = "discovery"
    PRESENTATION = "presentation"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    FOLLOW_UP = "follow_up"


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: str = Field(..., description="主要意图标签")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    stage_suggestion: Optional[str] = Field(None, description="建议的销售阶段")
    alternative_intents: List[Dict[str, float]] = Field(
        default_factory=list,
        description="备选意图列表"
    )
    context_enhanced: bool = Field(
        default=False,
        description="是否使用了上下文增强"
    )
    model_version: str = Field(default="fasttext_v1.0", description="模型版本")
    language: Optional[str] = Field(None, description="检测到的语言(zh/en)")


class IntentCategory(str, Enum):
    """快速意图分类类别（FastIntent使用）"""
    CREATIVE = "creative"
    LOGIC = "logic"
    EXTRACTION = "extraction"
    SIMPLE_CHAT = "simple_chat"
