"""
MVP 功能 Schema 定义
信用卡KOS销售实时辅助 + 轻量复盘
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IntentLabel(str, Enum):
    """意图标签（MVP 核心分类）"""
    BENEFIT_QA = "权益问答"  # 客户询问权益/活动信息
    OBJECTION_HANDLING = "异议处理"  # 客户提出异议
    CLOSING_PUSH = "推进成交"  # 识别推进成交时机
    COMPLIANCE_RISK = "合规风险"  # 检测到合规风险
    OTHER = "其他"  # 其他情况


class QuickSuggestRequest(BaseModel):
    """快速建议请求"""
    session_id: str
    last_user_msg: str
    optional_context: Optional[Dict[str, Any]] = None


class QuickSuggestResponse(BaseModel):
    """快速建议响应（MVP 核心输出）"""
    intent_label: IntentLabel = Field(..., description="意图分类")
    suggested_reply: str = Field(
        ..., 
        description="一句话/两句话内，必须可直接复制发送（<=220中文字符，最多2段）",
        max_length=220
    )
    alt_replies: List[str] = Field(
        ..., 
        min_items=2,
        description="至少2条备用话术"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    evidence: Optional[Dict[str, Any]] = Field(
        None,
        description="若是权益/活动类，必须可追溯：{source_titles: [], source_snippets: []}"
    )


class ComplianceCheckRequest(BaseModel):
    """合规检测请求"""
    text: str
    context: Optional[Dict[str, Any]] = None


class RiskLevel(str, Enum):
    """风险等级"""
    OK = "OK"  # 无风险
    WARN = "WARN"  # 警告，建议修改
    BLOCK = "BLOCK"  # 必须拦截，不允许发送


class ComplianceCheckResponse(BaseModel):
    """合规检测响应"""
    risk_level: RiskLevel = Field(..., description="风险等级")
    risk_tags: List[str] = Field(default_factory=list, description="风险标签")
    safe_rewrite: Optional[str] = Field(
        None,
        description="安全改写版本（命中WARN/BLOCK时必须有，短句，可直接替换发送）"
    )
    original: str = Field(..., description="原始文本")
    reason: Optional[str] = Field(None, description="风险原因（轻提示文案）")


class MicroFeedbackItem(BaseModel):
    """轻量复盘反馈项"""
    title: str = Field(..., description="反馈标题")
    what_happened: str = Field(..., description="发生了什么")
    better_move: str = Field(..., description="更好的做法")
    copyable_phrase: str = Field(..., description="可直接复用的话术/句子")


class MicroFeedbackResponse(BaseModel):
    """轻量复盘响应（<=3条）"""
    feedback_items: List[MicroFeedbackItem] = Field(
        ...,
        max_items=3,
        description="最多3条可执行反馈"
    )
    session_id: str
    total_turns: int

