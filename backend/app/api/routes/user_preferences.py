"""
User Preferences API

用户偏好设置API - 支持高级定制化

Author: Claude (Anthropic)
Date: 2026-02-05

Storage: In-memory dict keyed by user_id. Replace with Redis/DB for production.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...api.middleware import User, get_current_user

router = APIRouter(prefix="/api/user/preferences", tags=["preferences"])

# In-memory storage (replace with DB/Redis for production)
_preferences_store: Dict[str, dict] = {}
_custom_personas_store: Dict[str, List[dict]] = {}


class CustomerPersona(BaseModel):
    """自定义客户画像"""
    industry: str = Field(..., description="行业")
    position: str = Field(..., description="职位")
    personality: str = Field(..., description="性格类型")
    budget_range: str = Field(..., description="预算范围")
    decision_style: str = Field(..., description="决策风格")
    pain_points: List[str] = Field(default=[], description="痛点列表")
    needs: List[str] = Field(default=[], description="需求列表")


class CoachStyle(BaseModel):
    """AI教练风格设置"""
    strictness: str = Field(default="balanced", description="严格程度: strict/balanced/lenient")
    feedback_frequency: str = Field(default="normal", description="反馈频率: high/normal/low")
    focus_areas: List[str] = Field(default=[], description="关注重点")
    tone: str = Field(default="professional", description="语气: professional/friendly/motivational")


class TrainingDifficulty(BaseModel):
    """训练难度设置"""
    mode: str = Field(default="adaptive", description="模式: adaptive/manual/challenge")
    level: int = Field(default=3, ge=1, le=5, description="难度等级 1-5")
    adaptive_speed: str = Field(default="normal", description="自适应速度: slow/normal/fast")


class DataExportSettings(BaseModel):
    """数据导出设置"""
    format: str = Field(default="csv", description="导出格式: csv/excel/json")
    include_audio: bool = Field(default=False, description="是否包含录音")
    include_analysis: bool = Field(default=True, description="是否包含分析")


class UserPreferences(BaseModel):
    """用户偏好设置"""
    # 自定义客户画像
    custom_personas: List[CustomerPersona] = Field(default=[], description="自定义客户画像列表")

    # AI教练风格
    coach_style: CoachStyle = Field(default_factory=CoachStyle, description="AI教练风格")

    # 训练难度
    training_difficulty: TrainingDifficulty = Field(default_factory=TrainingDifficulty, description="训练难度")

    # 数据导出
    data_export: DataExportSettings = Field(default_factory=DataExportSettings, description="数据导出设置")

    # 通知设置
    notifications: Dict[str, bool] = Field(
        default={
            "practice_reminders": True,
            "achievement_alerts": True,
            "weekly_reports": True,
            "team_updates": False,
        },
        description="通知设置"
    )

    # 界面设置
    ui_settings: Dict[str, Any] = Field(
        default={
            "theme": "light",
            "language": "zh-CN",
            "show_tips": True,
            "auto_play_audio": False,
        },
        description="界面设置"
    )


@router.get("", response_model=UserPreferences)
async def get_preferences(
    user: User = Depends(get_current_user),
):
    """
    获取用户偏好设置

    Args:
        user: 当前用户

    Returns:
        用户偏好设置
    """
    # Load from in-memory store (or default)
    stored = _preferences_store.get(str(user.id))
    if stored:
        return UserPreferences(**stored)
    return UserPreferences()


@router.put("")
async def update_preferences(
    preferences: UserPreferences,
    user: User = Depends(get_current_user),
):
    """
    更新用户偏好设置

    Args:
        preferences: 新的偏好设置
        user: 当前用户

    Returns:
        更新后的偏好设置
    """
    # Save to in-memory store
    _preferences_store[str(user.id)] = preferences.model_dump()

    return {
        "success": True,
        "message": "Preferences updated successfully",
        "preferences": preferences,
    }


@router.post("/personas")
async def create_custom_persona(
    persona: CustomerPersona,
    user: User = Depends(get_current_user),
):
    """
    创建自定义客户画像

    Args:
        persona: 客户画像
        user: 当前用户

    Returns:
        创建的画像
    """
    # Save to in-memory store
    uid = str(user.id)
    if uid not in _custom_personas_store:
        _custom_personas_store[uid] = []
    persona_id = f"persona_{len(_custom_personas_store[uid])}_{uid}"
    entry = {"id": persona_id, **persona.model_dump()}
    _custom_personas_store[uid].append(entry)

    return {
        "success": True,
        "message": "Custom persona created",
        "persona": entry,
    }


@router.delete("/personas/{persona_id}")
async def delete_custom_persona(
    persona_id: str,
    user: User = Depends(get_current_user),
):
    """
    删除自定义客户画像

    Args:
        persona_id: 画像ID
        user: 当前用户

    Returns:
        删除结果
    """
    # Remove from in-memory store
    uid = str(user.id)
    if uid in _custom_personas_store:
        _custom_personas_store[uid] = [p for p in _custom_personas_store[uid] if p.get("id") != persona_id]

    return {
        "success": True,
        "message": "Custom persona deleted",
    }


@router.post("/export")
async def export_data(
    settings: DataExportSettings,
    user: User = Depends(get_current_user),
):
    """
    导出用户数据

    Args:
        settings: 导出设置
        user: 当前用户

    Returns:
        导出文件URL
    """
    # Generate export placeholder (full implementation would use export_service)
    return {
        "success": True,
        "download_url": f"/api/downloads/{user.id}/export.{settings.format}",
        "expires_at": "2026-02-06T00:00:00Z",
    }


@router.get("/presets")
async def get_presets():
    """
    获取预设配置

    Returns:
        预设配置列表
    """
    return {
        "coach_styles": [
            {
                "id": "strict",
                "name": "严格教练",
                "description": "高标准要求，详细反馈",
                "config": {
                    "strictness": "strict",
                    "feedback_frequency": "high",
                    "tone": "professional",
                }
            },
            {
                "id": "friendly",
                "name": "友好导师",
                "description": "鼓励为主，温和指导",
                "config": {
                    "strictness": "lenient",
                    "feedback_frequency": "normal",
                    "tone": "friendly",
                }
            },
            {
                "id": "motivational",
                "name": "激励大师",
                "description": "充满激情，激发潜能",
                "config": {
                    "strictness": "balanced",
                    "feedback_frequency": "high",
                    "tone": "motivational",
                }
            },
        ],
        "customer_personas": [
            {
                "id": "enterprise_cto",
                "name": "企业CTO",
                "description": "技术决策者，关注技术细节和ROI",
                "config": {
                    "industry": "technology",
                    "position": "CTO",
                    "personality": "analytical",
                    "budget_range": "high",
                    "decision_style": "data-driven",
                    "pain_points": ["技术债务", "团队效率", "系统稳定性"],
                    "needs": ["技术方案", "成本优化", "风险控制"],
                }
            },
            {
                "id": "smb_owner",
                "name": "中小企业主",
                "description": "务实决策者，关注性价比和快速见效",
                "config": {
                    "industry": "retail",
                    "position": "Owner",
                    "personality": "pragmatic",
                    "budget_range": "medium",
                    "decision_style": "intuitive",
                    "pain_points": ["成本压力", "人手不足", "竞争激烈"],
                    "needs": ["快速见效", "易于使用", "性价比高"],
                }
            },
        ],
    }
