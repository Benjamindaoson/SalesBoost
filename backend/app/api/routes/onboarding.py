"""
Onboarding API

新手引导相关API端点

Author: Claude (Anthropic)
Date: 2026-02-05
Updated: 2026-02-06 - 添加数据库持久化
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...api.middleware import User, get_current_user
from ...infra.database import get_db
from ...models.user_models import UserOnboarding

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingCompleteRequest(BaseModel):
    """引导完成请求"""
    userId: str
    completedAt: str


class OnboardingSkipRequest(BaseModel):
    """引导跳过请求"""
    userId: str
    skippedAt: str
    currentStep: int


class OnboardingStatusResponse(BaseModel):
    """引导状态响应"""
    is_complete: bool
    completed_at: Optional[str] = None
    skipped_at: Optional[str] = None
    current_step: int = 0


@router.post("/complete")
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    标记用户完成新手引导

    Args:
        request: 完成请求
        user: 当前用户
        db: 数据库会话

    Returns:
        成功响应
    """
    try:
        # 验证userId与当前用户匹配
        if request.userId != user.id:
            raise HTTPException(status_code=403, detail="User ID mismatch")

        # 查找或创建onboarding记录
        onboarding = db.query(UserOnboarding).filter(
            UserOnboarding.user_id == user.id
        ).first()

        if not onboarding:
            onboarding = UserOnboarding(
                user_id=user.id,
                is_complete=True,
                current_step=5,
                completed_at=datetime.fromisoformat(request.completedAt.replace('Z', '+00:00')),
                completed_steps=[0, 1, 2, 3, 4]
            )
            db.add(onboarding)
        else:
            onboarding.is_complete = True
            onboarding.current_step = 5
            onboarding.completed_at = datetime.fromisoformat(request.completedAt.replace('Z', '+00:00'))
            onboarding.completed_steps = [0, 1, 2, 3, 4]

        db.commit()
        db.refresh(onboarding)

        return {
            "success": True,
            "message": "Onboarding completed successfully",
            "completedAt": request.completedAt,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip")
async def skip_onboarding(
    request: OnboardingSkipRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    标记用户跳过新手引导

    Args:
        request: 跳过请求
        user: 当前用户
        db: 数据库会话

    Returns:
        成功响应
    """
    try:
        # 验证userId与当前用户匹配
        if request.userId != user.id:
            raise HTTPException(status_code=403, detail="User ID mismatch")

        # 查找或创建onboarding记录
        onboarding = db.query(UserOnboarding).filter(
            UserOnboarding.user_id == user.id
        ).first()

        if not onboarding:
            onboarding = UserOnboarding(
                user_id=user.id,
                is_complete=True,
                current_step=request.currentStep,
                skipped_at=datetime.fromisoformat(request.skippedAt.replace('Z', '+00:00')),
                skip_reason="User skipped onboarding"
            )
            db.add(onboarding)
        else:
            onboarding.is_complete = True
            onboarding.current_step = request.currentStep
            onboarding.skipped_at = datetime.fromisoformat(request.skippedAt.replace('Z', '+00:00'))
            onboarding.skip_reason = "User skipped onboarding"

        db.commit()
        db.refresh(onboarding)

        return {
            "success": True,
            "message": "Onboarding skipped",
            "skippedAt": request.skippedAt,
            "currentStep": request.currentStep,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户的新手引导状态

    Args:
        user: 当前用户
        db: 数据库会话

    Returns:
        引导状态
    """
    try:
        # 从数据库获取用户的onboarding状态
        onboarding = db.query(UserOnboarding).filter(
            UserOnboarding.user_id == user.id
        ).first()

        if not onboarding:
            # 用户还没有onboarding记录，返回默认状态
            return OnboardingStatusResponse(
                is_complete=False,
                current_step=0,
            )

        return OnboardingStatusResponse(
            is_complete=onboarding.is_complete,
            completed_at=onboarding.completed_at.isoformat() if onboarding.completed_at else None,
            skipped_at=onboarding.skipped_at.isoformat() if onboarding.skipped_at else None,
            current_step=onboarding.current_step,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_onboarding(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    重置用户的新手引导状态

    Args:
        user: 当前用户
        db: 数据库会话

    Returns:
        成功响应
    """
    try:
        # 查找onboarding记录
        onboarding = db.query(UserOnboarding).filter(
            UserOnboarding.user_id == user.id
        ).first()

        if onboarding:
            # 重置状态
            onboarding.is_complete = False
            onboarding.current_step = 0
            onboarding.completed_at = None
            onboarding.skipped_at = None
            onboarding.skip_reason = None
            onboarding.completed_steps = []

            db.commit()

        return {
            "success": True,
            "message": "Onboarding reset successfully",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
