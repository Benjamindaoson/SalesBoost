"""Assistant API — SSE streaming endpoint.

Replaces the previous 501 stub with a real streaming response backed by
ModelGateway.stream_call(). Clients consume this as Server-Sent Events.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...api.deps import require_user
from ...infra.gateway.schemas import ModelCall, RoutingContext, AgentType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantInvokeRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: str = "You are a sales coaching assistant."


async def _sse_generator(
    body: AssistantInvokeRequest,
) -> AsyncIterator[str]:
    """Yield SSE-formatted text chunks from ModelGateway.stream_call()."""
    try:
        from ...infra.gateway.model_gateway import ModelGateway
        from ...core.config import get_settings
        gateway = ModelGateway(get_settings())
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Gateway unavailable: {e}'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    routing = RoutingContext(agent_type=AgentType.COACH)
    call = ModelCall(
        prompt=body.message,
        system_prompt=body.system_prompt,
    )
    try:
        async for chunk in gateway.stream_call(call, routing):
            payload = json.dumps({"delta": chunk, "session_id": body.session_id})
            yield f"data: {payload}\n\n"
    except Exception as e:
        logger.error("[assistant] stream error session=%s: %s", body.session_id, e)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    yield "data: [DONE]\n\n"


@router.get("/health")
async def assistant_health():
    return {"status": "ok"}


@router.post("/invoke")
async def assistant_invoke(
    body: AssistantInvokeRequest,
    current_user=Depends(require_user),
):
    """Stream assistant response as Server-Sent Events.

    Response format: one SSE event per token chunk.
      data: {"delta": "<text>", "session_id": "<id>"}\n\n
    Terminated by:
      data: [DONE]\n\n
    """
    return StreamingResponse(
        _sse_generator(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
