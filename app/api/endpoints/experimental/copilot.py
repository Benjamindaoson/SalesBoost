"""
Live Copilot (E3)
实时辅助接口
"""
import logging
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

class CopilotRequest(BaseModel):
    context: str # 当前对话上下文
    user_input: Optional[str] = None # 用户正在输入的草稿

class CopilotResponse(BaseModel):
    suggestions: List[str]
    risk_alert: Optional[str] = None
    next_best_action: str

@router.post("/analyze", response_model=CopilotResponse)
async def analyze_context(req: CopilotRequest):
    """
    Mock: 实时分析上下文并给出建议
    """
    logger.info("Copilot analysis requested")
    
    return CopilotResponse(
        suggestions=[
            "询问预算范围",
            "确认决策流程",
            "强调产品 ROI"
        ],
        risk_alert=None,
        next_best_action="提议进行产品演示"
    )
