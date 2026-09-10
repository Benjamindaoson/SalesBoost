"""Chat API — SSE streaming endpoint."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from salesagent.core.constants import SaleStage, StageSignal
from langgraph.checkpoint.memory import MemorySaver
from salesagent.orchestration.builder import build_graph
from salesagent.models.db_models import Session as SessionModel
from salesagent.dependencies import get_db, get_redis
from salesagent.auth.dependencies import get_current_user
from salesagent.observability.metrics import active_sessions, session_messages_total
from salesagent.observability.error_tracking import set_user_context, add_breadcrumb

log = structlog.get_logger()
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: str | None = None
    customer_id: str | None = None


async def _get_or_create_session(
    session_id: str | None,
    customer_id: str | None,
    db: AsyncSession,
) -> str:
    from salesagent.models.db_models import Session as SessionModel

    if session_id:
        # Verify session exists
        from sqlalchemy import select
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        if result.scalar_one_or_none():
            return session_id

    # Create new session
    new_id = str(uuid.uuid4())
    session = SessionModel(id=new_id, customer_id=customer_id, status="active")
    db.add(session)
    await db.commit()
    return new_id


async def _event_stream(
    session_id: str,
    user_message: str,
    db: AsyncSession,
    redis: object,
) -> AsyncGenerator[str, None]:
    """
    Core SSE event generator using LangGraph orchestration.

    This implementation properly uses LangGraph's graph.astream() to orchestrate
    all nodes (reasoning → analyzer → strategy → retrieval → simulation → fsm → response).

    Flow:
    1. Initialize components (gateway, guard, memory)
    2. Build initial AgentState
    3. Let LangGraph orchestrate all nodes via graph.astream()
    4. Stream events back to client (reasoning, tokens, guard events)
    5. Handle HITL interrupts if needed
    6. Post-turn: memory extraction, message persistence
    """
    from salesagent.core.settings import settings
    from salesagent.fsm.sales_fsm import SalesFSM
    from salesagent.llm.gateway import ModelGateway
    from salesagent.guard.streaming_guard import StreamingGuard
    from salesagent.orchestration.state import AgentState
    from salesagent.memory.working_memory import WorkingMemory
    from salesagent.memory.adaptive_memory import AdaptiveMemory
    from salesagent.memory.extractor import MemoryExtractor
    from salesagent.orchestration.builder import build_graph

    try:
        # ── Initialize components ─────────────────────────────────────────
        gateway = ModelGateway(redis=redis)
        await gateway.initialize()
        guard = StreamingGuard(gateway=gateway, redis=redis)

        working_mem = WorkingMemory(redis=redis, session_id=session_id)
        adaptive_mem = AdaptiveMemory(db=db)

        # Set Sentry context
        set_user_context(session_id=session_id)
        add_breadcrumb("Chat stream started", category="chat", data={"session_id": session_id})

        # ── Load session + FSM ──────────────────────────────────────────
        fsm = await SalesFSM.from_session(session_id, db)

        # ── Update working memory ──────────────────────────────────────
        await working_mem.add_message("user", user_message)
        messages = await working_mem.get_messages()
        session_messages_total.labels(role="user").inc()

        # ── Build customer profile from Adaptive Memory ────────────────
        customer_profile = await adaptive_mem.build_customer_profile(session_id)

        # ── Get turn index ──────────────────────────────────────────────
        turn_index = len([m for m in messages if m["role"] == "user"])

        # ── Initial AgentState ─────────────────────────────────────────
        state: AgentState = {
            "session_id": session_id,
            "turn_index": turn_index,
            "fsm_stage": fsm.current_stage,
            "messages": messages,
            "user_message": user_message,
            "customer_profile": customer_profile,
            "reasoning_output": None,
            "retrieved_docs": [],
            "response_text": "",
            "response_stream_done": False,
            "guard_events": [],
            "guard_active": settings.guard_enabled,
            "reward_scores": {},
            "critic_rationale": "",
            "compliance_report": {},
            "sse_events": [],
            "error": None,
        }

        # ── Build LangGraph ──────────────────────────────────────────────
        graph = build_graph(gateway=gateway, guard=guard, db=db, redis=redis)
        config = {"configurable": {"thread_id": session_id}}

        # ── Check for Resumption ──────────────────────────────────────────
        session_res = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_obj = session_res.scalar_one()

        if session_obj.is_waiting_approval:
            # Check for override
            if session_obj.pending_human_override:
                await graph.aupdate_state(config, {"human_override": session_obj.pending_human_override})
                session_obj.pending_human_override = None

            session_obj.is_waiting_approval = False
            await db.commit()
            initial_input = None
        else:
            initial_input = state

        # ── LangGraph Execution Loop ────────────────────────────────────────
        log.info("Starting LangGraph execution", session_id=session_id)

        async for event in graph.astream(initial_input, config, stream_mode="values"):
            # Update local state reference
            state.update(event)

            # Emit reasoning output when available
            if event.get("reasoning_output") and not event.get("_reasoning_emitted"):
                yield f"data: {json.dumps({'event': 'reasoning', 'data': event['reasoning_output'].model_dump()})}\n\n"
                state["_reasoning_emitted"] = True

            # Emit tokens as they stream from response node
            if event.get("response_text") and not event.get("response_stream_done"):
                # Response node handles streaming internally
                # We just emit the final response here
                pass

            # Check for HITL Interrupt
            curr_state = await graph.aget_state(config)
            if curr_state.next and curr_state.next[0] == "response":
                if event.get("requires_approval"):
                    session_obj.is_waiting_approval = True
                    await db.commit()
                    yield f"data: {json.dumps({'event': 'wait_approval', 'data': {'session_id': session_id}})}\n\n"
                    return

        # ── Post-turn async work ───────────────────────────────────────
        async def _post_turn() -> None:
            try:
                full_response = state.get("response_text", "")

                # Wrap all DB operations in a transaction for atomicity
                async with db.begin():
                    # Store assistant message in working memory (Redis - outside transaction)
                    await working_mem.add_message("assistant", full_response)
                    session_messages_total.labels(role="assistant").inc()

                    # Extract + store memory entities
                    extractor = MemoryExtractor()
                    entities = await extractor.extract(
                        message=user_message,
                        reasoning_output=state.get("reasoning_output"),
                        session_id=session_id,
                    )
                    for entity in entities:
                        await adaptive_mem.upsert(session_id=session_id, **entity)

                    # Persist message to DB
                    from salesagent.models.db_models import Message
                    msg = Message(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        turn_index=turn_index,
                        reasoning_output=state.get("reasoning_output").model_dump() if state.get("reasoning_output") else {},
                        guard_events=state.get("guard_events", []),
                        model_used=settings.primary_response_model,
                    )
                    db.add(msg)
                    # Transaction auto-commits on exit

            except Exception as exc:
                log.error("Post-turn processing failed", error=str(exc))
                await db.rollback()

        asyncio.create_task(_post_turn())

        # ── Emit final events ────────────────────────────────────────────
        yield f"data: {json.dumps({'event': 'reward', 'data': state.get('reward_scores', {})})}\n\n"
        yield f"data: {json.dumps({'event': 'done', 'data': {'session_id': session_id, 'stage': fsm.current_stage.value}})}\n\n"

    except Exception as exc:
        log.error("SSE stream error", error=str(exc), session_id=session_id)
        yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """POST /chat/stream — SSE streaming sales conversation."""
    log.info("Chat stream request", user=current_user.get("sub"), session_id=chat_request.session_id)

    redis = await get_redis()

    session_id = await _get_or_create_session(
        session_id=chat_request.session_id,
        customer_id=chat_request.customer_id,
        db=db,
    )

    return StreamingResponse(
        _event_stream(
            session_id=session_id,
            user_message=chat_request.message,
            db=db,
            redis=redis,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        },
    )
