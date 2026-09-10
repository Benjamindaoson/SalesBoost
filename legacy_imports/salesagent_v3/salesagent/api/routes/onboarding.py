"""Onboarding API for new user setup."""
from __future__ import annotations

import secrets
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.integrations.wechat_work import get_wechat_client
from salesagent.core.settings import settings
from salesagent.dependencies import get_db, get_redis
from salesagent.auth.dependencies import get_current_user

log = structlog.get_logger()
router = APIRouter()


@router.get("/wechat-qr")
async def get_wechat_qr(
    user_id: str,
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate WeChat binding QR code.

    Args:
        user_id: User ID
        redis: Redis client

    Returns:
        QR code URL
    """
    # Generate temporary token
    token = secrets.token_urlsafe(32)
    await redis.setex(f"wechat_bind:{token}", 300, user_id)  # 5 minutes TTL

    # Generate QR code URL
    qr_url = (
        f"https://open.work.weixin.qq.com/wwopen/sso/qrConnect?"
        f"appid={settings.wechat_corp_id}&"
        f"redirect_uri=https://salesboost.com/callback&"
        f"state={token}"
    )

    log.info("Generated WeChat QR code", user_id=user_id, token=token)

    return {"qr_url": qr_url, "token": token}


@router.post("/wechat-callback")
async def wechat_callback(
    code: str,
    state: str,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Handle WeChat OAuth callback.

    Args:
        code: Authorization code from WeChat
        state: State token
        redis: Redis client
        db: Database session

    Returns:
        Binding result
    """
    # Verify state token
    user_id = await redis.get(f"wechat_bind:{state}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Exchange code for user info (simplified, actual implementation needs more steps)
    client = get_wechat_client()
    # In real implementation, use code to get user_id from WeChat
    wechat_user_id = f"wechat_{code[:8]}"

    # Store binding
    await redis.set(f"user:{user_id}:wechat_id", wechat_user_id)
    await redis.delete(f"wechat_bind:{state}")

    log.info("WeChat binding successful", user_id=user_id, wechat_user_id=wechat_user_id)

    return {
        "status": "success",
        "user_id": user_id,
        "wechat_user_id": wechat_user_id,
    }


@router.post("/upload-knowledge")
async def upload_knowledge(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload knowledge base document during onboarding.

    Args:
        user_id: User ID
        file: Uploaded file
        db: Database session

    Returns:
        Upload result
    """
    # Read file content
    content = await file.read()

    # Import knowledge indexer
    from salesagent.knowledge.indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer(db=db)

    # Index document
    doc_id = await indexer.index_document(
        user_id=user_id,
        filename=file.filename,
        content=content,
        content_type=file.content_type,
    )

    log.info(
        "Knowledge document uploaded",
        user_id=user_id,
        filename=file.filename,
        doc_id=doc_id,
    )

    return {
        "status": "success",
        "doc_id": doc_id,
        "filename": file.filename,
    }


@router.post("/set-preferences")
async def set_preferences(
    user_id: str,
    tone: str,
    response_speed: int,
    auto_send: bool,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Set user preferences during onboarding.

    Args:
        user_id: User ID
        tone: Communication tone (professional/friendly/concise)
        response_speed: Response speed in seconds (15-90)
        auto_send: Whether to auto-send AI messages
        redis: Redis client

    Returns:
        Success response
    """
    # Validate inputs
    if tone not in ["professional", "friendly", "concise"]:
        raise HTTPException(status_code=400, detail="Invalid tone")

    if not 15 <= response_speed <= 90:
        raise HTTPException(status_code=400, detail="Response speed must be between 15-90")

    # Store preferences in Redis
    preferences = {
        "tone": tone,
        "response_speed": response_speed,
        "auto_send": "1" if auto_send else "0",
    }

    for key, value in preferences.items():
        await redis.hset(f"user:{user_id}:preferences", key, str(value))

    log.info("User preferences set", user_id=user_id, preferences=preferences)

    return {"status": "success", "preferences": preferences}


@router.post("/test-chat")
async def test_chat(
    message: str,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Test AI chat in sandbox mode.

    Args:
        message: Test message
        redis: Redis client

    Returns:
        AI response
    """
    try:
        # Import components
        from salesagent.reasoning.chain import SalesReasoningChain
        from salesagent.llm.gateway import ModelGateway
        from salesagent.fsm.sales_fsm import SaleStage

        gateway = ModelGateway()
        reasoning = SalesReasoningChain(gateway=gateway, redis=redis)

        # Run reasoning
        reasoning_output = await reasoning.run(
            messages=[{"role": "user", "content": message}],
            fsm_stage=SaleStage.ICEBREAK,
            session_id="sandbox_test",
        )

        # Generate response
        response = await gateway.complete(
            task="response",
            system="你是一位专业的销售顾问，正在与客户进行友好的对话。",
            user=message,
            session_id="sandbox_test",
        )

        log.info("Sandbox test completed", message_preview=message[:50])

        return {
            "response": response,
            "intent": reasoning_output.literal_intent,
            "tactics": reasoning_output.recommended_tactics.model_dump(),
        }

    except Exception as e:
        log.error("Sandbox test failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/activate")
async def activate_user(
    user_id: str,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Activate user account after onboarding.

    Args:
        user_id: User ID
        redis: Redis client
        db: Database session

    Returns:
        Activation result
    """
    # Set activation flag
    await redis.set(f"user:{user_id}:activated", "1")

    # TODO: Update user status in database

    log.info("User activated", user_id=user_id)

    return {
        "status": "success",
        "user_id": user_id,
        "message": "账户已激活，欢迎使用 SalesBoost！",
    }


@router.get("/status/{user_id}")
async def get_onboarding_status(
    user_id: str,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get onboarding progress status.

    Args:
        user_id: User ID
        redis: Redis client

    Returns:
        Onboarding status
    """
    # Check each step
    wechat_bound = await redis.get(f"user:{user_id}:wechat_id") is not None
    preferences_set = await redis.exists(f"user:{user_id}:preferences") > 0
    activated = await redis.get(f"user:{user_id}:activated") == "1"

    # Calculate progress
    steps_completed = sum([wechat_bound, preferences_set, activated])
    total_steps = 5  # WeChat, Upload, Preferences, Test, Activate
    progress = int((steps_completed / total_steps) * 100)

    return {
        "user_id": user_id,
        "progress": progress,
        "steps": {
            "wechat_binding": wechat_bound,
            "knowledge_upload": False,  # TODO: check from DB
            "preferences_set": preferences_set,
            "sandbox_tested": False,  # TODO: track test completion
            "activated": activated,
        },
    }
