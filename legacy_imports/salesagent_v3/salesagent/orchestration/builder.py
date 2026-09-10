"""LangGraph builder — assembles the full agent DAG for each FSM stage."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from langgraph.graph import END, START, StateGraph
# CompiledGraph is used for type hinting below.
# In newer versions it's CompiledStateGraph, but we can use 'Any' or the instance type.
from typing import Any
CompiledGraph = Any

from salesagent.orchestration.state import AgentState
from salesagent.orchestration.checkpointer import PostgresCheckpointer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from redis.asyncio import Redis
    from salesagent.llm.gateway import ModelGateway
    from salesagent.guard.streaming_guard import StreamingGuard

log = structlog.get_logger()


def build_graph(
    gateway: ModelGateway,
    guard: StreamingGuard,
    db: AsyncSession,
    redis: Redis | None = None,
) -> CompiledGraph:
    """
    Build and compile the LangGraph StateGraph.

    Execution order:
    1. reasoning_node (Generative plan + CoT)
    2. retrieval_node (Parallel RAG)
    3. strategy_node (Intent Radar + Criticality check)
    4. simulation_node (MCTS-lite Tactical Refinement)
    5. fsm_node (FSM state transition - NEW)
    6. response_node (Streaming + Hot/Cold path)
    7. critic_bypass (Async evaluation)
    """
    from salesagent.orchestration.nodes.reasoning import reasoning_node
    from salesagent.orchestration.nodes.strategy import strategy_node
    from salesagent.orchestration.nodes.retrieval import retrieval_node
    from salesagent.orchestration.nodes.routing import router_node
    from salesagent.orchestration.nodes.simulation import simulation_node
    from salesagent.orchestration.nodes.response import response_node
    from salesagent.orchestration.nodes.analyzer import analyzer_node
    from salesagent.orchestration.nodes.fsm import fsm_node
    from salesagent.orchestration.nodes.critic import critic_node, compliance_node

    # Bind infrastructure dependencies to nodes
    async def _router(state: AgentState) -> str:
        return await router_node(state, db=db, gateway=gateway)

    async def _reasoning(state: AgentState) -> AgentState:
        return await reasoning_node(state, gateway=gateway, redis=redis)

    async def _analyzer(state: AgentState) -> AgentState:
        return await analyzer_node(state, gateway=gateway)

    async def _strategy(state: AgentState) -> AgentState:
        return await strategy_node(state, gateway=gateway)

    async def _retrieval(state: AgentState) -> AgentState:
        return await retrieval_node(state, gateway=gateway, db=db)

    async def _simulation(state: AgentState) -> AgentState:
        return await simulation_node(state, gateway=gateway)

    async def _fsm(state: AgentState) -> AgentState:
        return await fsm_node(state, db=db, redis=redis)

    async def _response(state: AgentState) -> AgentState:
        return await response_node(state, gateway=gateway, guard=guard)

    async def _critic(state: AgentState) -> AgentState:
        # Fire-and-forget: run critic asynchronously without blocking
        asyncio.create_task(critic_node(state, gateway=gateway, db=db))
        asyncio.create_task(compliance_node(state, gateway=gateway, db=db))
        return state

    # ── Build graph ───────────────────────────────────────────────────────
    graph = StateGraph(AgentState)

    graph.add_node("router", _router)
    graph.add_node("reasoning", _reasoning)
    graph.add_node("analyzer", _analyzer)
    graph.add_node("retrieval", _retrieval)
    graph.add_node("strategy", _strategy)
    graph.add_node("simulation", _simulation)
    graph.add_node("fsm", _fsm)
    graph.add_node("response", _response)
    graph.add_node("critic_bypass", _critic)

    # START → Router (分流器)
    graph.set_entry_point("router")

    # Conditional routing: Hot Path vs Cold Path
    graph.add_conditional_edges(
        "router",
        lambda x: x,  # router_node returns "hot" or "cold"
        {
            "hot": "response",
            "cold": "reasoning"
        }
    )

    # Cold Path flow (Tactical Engine 2.0)
    if not (settings.lite_mode or state.get("use_lite_path", False)):
        graph.add_edge("reasoning", "analyzer")
        graph.add_edge("analyzer", "strategy")

        # Retrieval also runs in the cold path to provide context beyond the hot match
        graph.add_edge("router", "retrieval")
        graph.add_edge("retrieval", "strategy")

        # Strategy → Simulation (Tactical Refinement) → FSM → Response
        graph.add_edge("strategy", "simulation")
        graph.add_edge("simulation", "fsm")
        graph.add_edge("fsm", "response")
    else:
        # LITE MODE: Direct path for B2C
        log.info("LangGraph: LITE MODE enabled (B2C optimization)")
        graph.add_edge("reasoning", "response")
        # Ensure retrieval still runs if needed, or skip it
        # User said: 意图识别 -> 响应生成
        # We can keep retrieval if we want FAQ support, but it's optional.
        # Let's keep it minimal for now.

    graph.add_edge("response", "critic_bypass")
    graph.add_edge("critic_bypass", END)

    # ── Compile with Checkpointer & Interrupts ──
    # V3.1: PostgreSQL-based checkpointer for production persistence
    checkpointer = PostgresCheckpointer(db=db)
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["response"]
    )


# Singleton graph cache
_graph_cache: dict[int, CompiledGraph] = {}

def get_or_build_graph(
    gateway: ModelGateway,
    guard: StreamingGuard,
    db: AsyncSession,
    redis: Redis | None = None,
) -> CompiledGraph:
    key = id(gateway)
    if key not in _graph_cache:
        _graph_cache[key] = build_graph(gateway=gateway, guard=guard, db=db, redis=redis)
    return _graph_cache[key]
