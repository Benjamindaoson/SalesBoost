"""Response Node — streams tokens through Guard, then assembles final response."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import structlog
from opentelemetry import trace

from salesagent.orchestration.state import AgentState

log = structlog.get_logger()
tracer = trace.get_tracer(__name__)


async def response_node(
    state: AgentState,
    gateway: object,
    guard: object,
    sse_queue: object = None,
) -> AgentState:
    """
    Generate and stream the final response through the Guard.

    This node:
    1. Checks for hot path bypass
    2. Assembles system prompt from reasoning output
    3. Streams tokens through Guard
    4. Returns final response in state
    """
    with tracer.start_as_current_span("response_node") as span:
        span.set_attribute("session_id", state.get("session_id", ""))

        # ── Early return if already processed ──────────────────────────────────
        if state.get("response_stream_done"):
            span.set_attribute("already_processed", True)
            return state

        # ── Hot Path Bypass ──────────────────────────────────────────────────
        if state.get("is_hot_path") and state.get("hot_path_response"):
            response = state["hot_path_response"]
            span.set_attribute("hot_path", True)
            log.info("Hot Path Execution: Returning pre-retrieved response", session_id=state.get("session_id"))
            state["response_text"] = response
            state["response_stream_done"] = True
            return state

    import asyncio
    from salesagent.reasoning.prompts import RESPONSE_SYSTEM_PROMPT
    from salesagent.knowledge.case_store import case_store

    reasoning = state.get("reasoning_output")
    if reasoning is None:
        state["response_text"] = "抱歉，我暂时无法处理您的请求，请稍后再试。"
        return state

    # ── Assemble retrieved knowledge ──────────────────────────────────────
    docs = state.get("retrieved_docs", [])

    # [HOT PATH OPTIMIZATION]
    # If high-confidence knowledge exists for a standard intent, bypass LLM Tactical Reasoning
    if docs and docs[0].get("score", 0) > 0.92:
        top_doc = docs[0].get("content", "")
        log.info("Hot Path Triggered: Semantic match found in Knowledge Base", session_id=state.get("session_id"))
        state["response_text"] = top_doc
        state["response_stream_done"] = True
        if sse_queue:
            await sse_queue.put({"event": "done", "data": {"response": top_doc}})
        return state

    knowledge_text = "\n\n".join(
        f"[{i+1}] {d.get('content', '')}" for i, d in enumerate(docs[:3])
    ) or "无相关知识库信息"

    # ── Retrieve Few-Shot Context (DSP) ──────────────────────────────────
    # Query cases based on the planned tactic/intent
    cases = await case_store.get_similar_cases(
        intent=reasoning.literal_intent,
        stage=state["fsm_stage"].value
    )
    few_shot_text = "\n".join(cases) if cases else "No relevant examples found."

    # ── Build system prompt ───────────────────────────────────────────────
    system_prompt = RESPONSE_SYSTEM_PROMPT.format(
        strategy_plan=reasoning.strategy_plan,
        tactical_instructions=reasoning.tactical_instructions,
        tone=reasoning.tone,
        avoid_tactics=", ".join(reasoning.avoid),
        hidden_concerns="; ".join(reasoning.hidden_concerns),
        few_shot_context=few_shot_text,
        retrieved_knowledge=knowledge_text,
        fsm_stage=state["fsm_stage"].value,
    )

    # Format conversation for the response model
    user_content = "\n".join(
        f"[{m['role'].upper()}]: {m['content']}"
        for m in state.get("messages", [])[-6:]
    )

    full_response = ""
    guard_events: list[dict[str, Any]] = []

    # ── Typing Simulation (PRD NFR) ──────────────────────────────────────────
    import asyncio
    import random
    from salesagent.core.settings import settings

    if not state.get("human_override"):
        delay = random.uniform(settings.typing_sim_delay_min, settings.typing_sim_delay_max)
        log.info("Simulating human typing delay", delay_seconds=delay)
        await asyncio.sleep(delay)

    # ── Stream through Guard ──────────────────────────────────────────────
    token_stream = gateway.stream(  # type: ignore[attr-defined]
        task="response",
        system=system_prompt,
        user=user_content,
        session_id=state.get("session_id", ""),
        use_lite=state.get("use_lite_path", False),
    )

    from salesagent.guard.streaming_guard import StreamingGuard
    guarded_stream = guard.wrap_stream(  # type: ignore[attr-defined]
        token_stream=token_stream,
        session_id=state.get("session_id", ""),
        turn_index=state.get("turn_index", 0),
    )

    async for event in guarded_stream:
        if event["type"] == "token":
            token = event["data"]
            full_response += token
            if sse_queue:
                await sse_queue.put({"event": "token", "data": {"token": token}})
        elif event["type"] == "guard_event":
            guard_events.append(event["data"])
            if sse_queue:
                await sse_queue.put({"event": "guard", "data": event["data"]})

    state["response_text"] = full_response
    state["guard_events"] = guard_events
    state["response_stream_done"] = True

    if sse_queue:
        await sse_queue.put({"event": "done", "data": {"response": full_response}})

    return state


import asyncio  # noqa: E402 (needed for type hint above)
