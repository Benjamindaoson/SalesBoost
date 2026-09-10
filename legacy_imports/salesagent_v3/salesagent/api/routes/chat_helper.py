"""Helper function to process chat messages (used by workers)."""
from __future__ import annotations

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.orchestration.builder import build_graph
from salesagent.llm.gateway import ModelGateway
from salesagent.guard.streaming_guard import StreamingGuard


async def process_chat_message(
    session_id: str,
    user_message: str,
    db: AsyncSession,
    redis: aioredis.Redis,
) -> str:
    """Process a chat message through the AI engine.

    Args:
        session_id: Session ID
        user_message: User's message content
        db: Database session
        redis: Redis client

    Returns:
        AI response text
    """
    # Initialize components
    gateway = ModelGateway()
    guard = StreamingGuard(gateway=gateway)

    # Build graph
    graph = build_graph(gateway=gateway, guard=guard, db=db, redis=redis)

    # Prepare initial state
    initial_state = {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [],
        "response_text": "",
    }

    # Run graph
    config = {"configurable": {"thread_id": session_id}}
    final_state = await graph.ainvoke(initial_state, config)

    return final_state.get("response_text", "")
