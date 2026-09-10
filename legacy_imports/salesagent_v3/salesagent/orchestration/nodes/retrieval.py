"""Retrieval Node — Dense retrieval + SelfRAG filter + reranking."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from salesagent.orchestration.state import AgentState

log = structlog.get_logger()


async def retrieval_node(state: AgentState, gateway: object, db: object) -> AgentState:
    """
    Retrieve relevant knowledge chunks for the current user query.
    Runs in parallel with Reasoning via LangGraph fan-out.
    """
    try:
        from salesagent.knowledge.retriever import KnowledgeRetriever
        from salesagent.core.settings import settings

        retriever = KnowledgeRetriever(db=db, gateway=gateway)
        docs = await retriever.retrieve(
            query=state.get("user_message", ""),
            top_k=settings.retrieval_top_k,
        )
        state["retrieved_docs"] = docs
        log.debug("Retrieval complete", session_id=state.get("session_id"), chunks=len(docs))
    except Exception as exc:
        log.warning("Retrieval node failed", error=str(exc))
        state["retrieved_docs"] = []

    return state
