"""WeChat webhook endpoint for receiving messages."""
from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from redis.asyncio import Redis

from salesagent.integrations.message_queue import MessageQueue
from salesagent.integrations.wechat_work import get_wechat_client
from salesagent.dependencies import get_redis
from salesagent.auth.dependencies import get_current_user

log = structlog.get_logger()

router = APIRouter()


@router.get("/wechat/webhook")
async def wechat_webhook_verify(
    msg_signature: str = Query(..., alias="msg_signature"),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    current_user: dict = Depends(get_current_user),
) -> str:
    """Verify WeChat webhook URL.

    This endpoint is called by WeChat to verify the webhook URL.
    We need to return the echostr parameter after verification.

    Args:
        msg_signature: Message signature from WeChat
        timestamp: Timestamp from WeChat
        nonce: Nonce from WeChat
        echostr: Echo string to return

    Returns:
        Echo string if verification succeeds
    """
    client = get_wechat_client()

    # Verify signature
    if not client.verify_signature(msg_signature, timestamp, nonce):
        log.error("WeChat webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    log.info("WeChat webhook verified successfully")
    return echostr


@router.post("/wechat/webhook")
async def wechat_webhook_receive(
    request: Request,
    redis: Redis = Depends(get_redis),
    msg_signature: str = Query(None, alias="msg_signature"),
    timestamp: str = Query(None),
    nonce: str = Query(None),
) -> dict[str, Any]:
    """Receive messages from WeChat webhook.

    Args:
        request: FastAPI request object
        redis: Redis client
        msg_signature: Message signature
        timestamp: Timestamp
        nonce: Nonce

    Returns:
        Success response
    """
    client = get_wechat_client()

    # Verify signature if provided
    if msg_signature and timestamp and nonce:
        if not client.verify_signature(msg_signature, timestamp, nonce):
            log.error("WeChat webhook signature verification failed")
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse request body
    try:
        body = await request.body()
        data = json.loads(body) if body else await request.json()
    except Exception as e:
        log.error("Failed to parse webhook body", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Extract message info
    msg_type = data.get("MsgType")
    from_user = data.get("FromUserName")
    to_user = data.get("ToUserName")
    create_time = data.get("CreateTime")

    log.info(
        "Received WeChat message",
        msg_type=msg_type,
        from_user=from_user,
        to_user=to_user,
    )

    # Handle different message types
    if msg_type == "text":
        content = data.get("Content")
        msg_id = data.get("MsgId")

        # Push to inbound queue
        queue = MessageQueue(redis)
        await queue.push_inbound(
            user_id=from_user,
            content=content,
            metadata={
                "msg_id": msg_id,
                "create_time": create_time,
                "to_user": to_user,
            },
        )

        log.info("Pushed text message to inbound queue", msg_id=msg_id)

    elif msg_type == "event":
        event = data.get("Event")
        log.info("Received WeChat event", event=event, from_user=from_user)

        # Handle events (subscribe, unsubscribe, etc.)
        if event == "subscribe":
            # User subscribed, send welcome message
            await client.send_text_message(
                user_id=from_user,
                content="欢迎使用 SalesBoost！我是您的 AI 销售助理，随时为您服务。",
            )

    elif msg_type == "image":
        pic_url = data.get("PicUrl")
        media_id = data.get("MediaId")
        log.info("Received image message", pic_url=pic_url, media_id=media_id)
        # TODO: Handle image messages

    elif msg_type == "voice":
        media_id = data.get("MediaId")
        format_type = data.get("Format")
        log.info("Received voice message", media_id=media_id, format=format_type)
        # TODO: Handle voice messages

    else:
        log.warning("Unsupported message type", msg_type=msg_type)

    return {"errcode": 0, "errmsg": "ok"}


@router.post("/wechat/send")
async def wechat_send_message(
    user_id: str,
    content: str,
    msg_type: str = "text",
) -> dict[str, Any]:
    """Manually send message to WeChat user (for testing).

    Args:
        user_id: WeChat user ID
        content: Message content
        msg_type: Message type (text, markdown)

    Returns:
        API response
    """
    client = get_wechat_client()

    if msg_type == "text":
        result = await client.send_text_message(user_id, content)
    elif msg_type == "markdown":
        result = await client.send_markdown_message(user_id, content)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported msg_type: {msg_type}")

    return result


@router.get("/wechat/user/{user_id}")
async def get_wechat_user(user_id: str) -> dict[str, Any]:
    """Get WeChat user information.

    Args:
        user_id: WeChat user ID

    Returns:
        User information
    """
    client = get_wechat_client()
    user_info = await client.get_user_info(user_id)
    return user_info
