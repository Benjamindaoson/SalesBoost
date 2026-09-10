"""WeChat webhook API endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Query, HTTPException, Depends
from redis.asyncio import Redis

from salesagent.dependencies import get_redis
from salesagent.integrations.wechat_work import WeChatWorkClient, handle_wework_message

log = structlog.get_logger()
router = APIRouter(prefix="/wechat", tags=["WeChat"])


@router.get("/work/webhook")
async def wechat_work_webhook_verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    redis: Redis = Depends(get_redis),
) -> str:
    """
    WeChat Work webhook verification endpoint.

    When you configure the webhook URL in WeChat Work admin panel,
    WeChat will send a GET request to verify the URL.
    """
    client = WeChatWorkClient(redis=redis)

    # Verify signature
    if not client.verify_signature(msg_signature, timestamp, nonce):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Return echostr to complete verification
    log.info("WeChat Work webhook verified")
    return echostr


@router.post("/work/webhook")
async def wechat_work_webhook_receive(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    """
    WeChat Work webhook message receiver.

    Receives messages from WeChat Work and processes them.
    """
    client = WeChatWorkClient(redis=redis)

    # Verify signature
    if not client.verify_signature(msg_signature, timestamp, nonce):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Get request body
    body = await request.body()
    xml_data = body.decode('utf-8')

    # Parse XML message
    from xml.etree import ElementTree as ET
    root = ET.fromstring(xml_data)

    # Check if encrypted
    encrypt_node = root.find('Encrypt')
    if encrypt_node is not None:
        # Decrypt message
        encrypted_msg = encrypt_node.text
        message = client.decrypt_message(encrypted_msg)
    else:
        # Plain text message
        message = {
            'ToUserName': root.find('ToUserName').text,
            'FromUserName': root.find('FromUserName').text,
            'CreateTime': root.find('CreateTime').text,
            'MsgType': root.find('MsgType').text,
            'Content': root.find('Content').text if root.find('Content') is not None else '',
            'MsgId': root.find('MsgId').text if root.find('MsgId') is not None else '',
        }

    if not message:
        raise HTTPException(status_code=400, detail="Failed to parse message")

    # Handle message asynchronously
    import asyncio
    asyncio.create_task(handle_wework_message(client, message))

    # Return success response
    return {'status': 'ok'}


@router.post("/work/send")
async def wechat_work_send_message(
    user_id: str,
    content: str,
    msg_type: str = "text",
    redis: Redis = Depends(get_redis),
) -> dict[str, bool]:
    """
    Manual API to send WeChat Work message.

    Useful for testing or manual interventions.
    """
    client = WeChatWorkClient(redis=redis)

    if msg_type == "text":
        success = await client.send_text_message(user_id, content)
    elif msg_type == "markdown":
        success = await client.send_markdown_message(user_id, content)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported msg_type: {msg_type}")

    return {'success': success}
