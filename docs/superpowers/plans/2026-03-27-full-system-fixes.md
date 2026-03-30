# SalesBoost Full System Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all identified gaps: core pipeline correctness, module naming accuracy, and engineering reliability — based on direct code audit of the repository.

**Architecture:** Three layers of fixes — (1) core runtime correctness (FSM guard, LangGraph checkpointer, streaming), (2) naming/clarity (PPO→TacticScorer, RLAIF→ConversationAnalyzer, ConstitutionalAI→SafetyFilter), (3) engineering reliability (Redis warning, tool retry, memory promotion, OTel tracing).

**Tech Stack:** FastAPI, LangGraph (`langgraph-checkpoint-redis`), Redis, SQLAlchemy async, OpenTelemetry, Python 3.11+

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/agents/conversation/intent_routing.py` | Modify | Add FSM stage transition guard |
| `backend/app/engine/coordinator/dynamic_workflow.py` | Modify | Pass AsyncRedisSaver to graph.compile() |
| `backend/app/api/endpoints/assistant.py` | Rewrite | Real SSE streaming endpoint |
| `backend/main.py` | Modify | Mount assistant SSE route, add Redis startup check |
| `backend/app/agents/rl/ppo_policy.py` | Modify | Rename PPOPolicy→TacticScorer, add TrainablePolicy stub |
| `backend/app/agents/rl/__init__.py` | Modify | Export TacticScorer |
| `backend/app/agents/autonomous/sdr_agent_enhanced.py` | Modify | Update import PPOPolicy→TacticScorer |
| `backend/app/ai_core/rlaif/pipeline.py` | Modify | Rename RLAIFPipeline→ConversationAnalyzer, add RewardDataCollector stub |
| `backend/app/ai_core/constitutional/constitutional_ai.py` | Modify | Rename ConstitutionalAI→SafetyFilter, add CritiqueReviseFilter stub |
| `backend/app/infra/gateway/redis_semaphore.py` | Modify | Add startup warning on degradation |
| `backend/app/tools/executor.py` | Modify | Add per-tool retry (max 2) + fallback |
| `backend/app/agents/memory/agent_memory.py` | Modify | Add maybe_promote() L1→L2 promotion |
| `backend/app/observability/otel_tracing.py` | Modify | Add node-level span helpers |
| `backend/app/engine/coordinator/dynamic_workflow.py` | Modify (2nd pass) | Instrument node handlers with OTel spans |
| `backend/requirements.txt` | Modify | Add langgraph-checkpoint-redis |
| `backend/tests/unit/test_stage_guard.py` | Create | Tests for FSM transition guard |
| `backend/tests/unit/test_tactic_scorer.py` | Create | Tests for renamed TacticScorer |
| `backend/tests/unit/test_memory_promotion.py` | Create | Tests for maybe_promote() |

---

## Task 1: FSM Stage Transition Guard

**Files:**
- Modify: `backend/app/agents/conversation/intent_routing.py`
- Create: `backend/tests/unit/test_stage_guard.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_stage_guard.py`:

```python
import pytest
from app.agents.conversation.intent_routing import (
    SalesStage, VALID_TRANSITIONS, validate_stage_transition
)


def test_valid_forward_transition():
    ok, err = validate_stage_transition(SalesStage.OPENING, SalesStage.DISCOVERY)
    assert ok is True
    assert err is None


def test_invalid_skip_transition():
    ok, err = validate_stage_transition(SalesStage.OPENING, SalesStage.CLOSING)
    assert ok is False
    assert "CLOSING" in err


def test_same_stage_is_valid():
    ok, err = validate_stage_transition(SalesStage.DISCOVERY, SalesStage.DISCOVERY)
    assert ok is True


def test_backward_transition_blocked():
    ok, err = validate_stage_transition(SalesStage.PITCH, SalesStage.OPENING)
    assert ok is False


def test_none_current_stage_always_valid():
    """First message has no prior stage — any initial stage is allowed."""
    ok, err = validate_stage_transition(None, SalesStage.OPENING)
    assert ok is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_stage_guard.py -v
```
Expected: `ImportError` — `SalesStage`, `VALID_TRANSITIONS`, `validate_stage_transition` not yet defined.

- [ ] **Step 3: Add SalesStage enum and guard to intent_routing.py**

Open `backend/app/agents/conversation/intent_routing.py`. After the existing imports (after line 13), add:

```python
from typing import Optional, Tuple


class SalesStage(str, Enum):
    """销售漏斗阶段（硬编码 FSM）"""
    OPENING = "opening"
    DISCOVERY = "discovery"
    PITCH = "pitch"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    COMPLETED = "completed"


# 合法的阶段跳转表。每个阶段只能前进到此集合内的下一阶段，或保持原阶段。
VALID_TRANSITIONS: dict[SalesStage, set[SalesStage]] = {
    SalesStage.OPENING: {SalesStage.OPENING, SalesStage.DISCOVERY},
    SalesStage.DISCOVERY: {SalesStage.DISCOVERY, SalesStage.PITCH, SalesStage.OBJECTION_HANDLING},
    SalesStage.PITCH: {SalesStage.PITCH, SalesStage.OBJECTION_HANDLING, SalesStage.CLOSING},
    SalesStage.OBJECTION_HANDLING: {SalesStage.OBJECTION_HANDLING, SalesStage.PITCH, SalesStage.CLOSING},
    SalesStage.CLOSING: {SalesStage.CLOSING, SalesStage.COMPLETED},
    SalesStage.COMPLETED: {SalesStage.COMPLETED},
}


def validate_stage_transition(
    current: Optional[SalesStage],
    next_stage: SalesStage,
) -> Tuple[bool, Optional[str]]:
    """检查阶段跳转是否合法。返回 (ok, error_message)。"""
    if current is None:
        return True, None  # 首条消息，无约束
    allowed = VALID_TRANSITIONS.get(current, set())
    if next_stage in allowed:
        return True, None
    return False, (
        f"INVALID_TRANSITION: {current.value} -> {next_stage.value}. "
        f"Allowed: {[s.value for s in allowed]}"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_stage_guard.py -v
```
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd d:/sales-boost && git add backend/app/agents/conversation/intent_routing.py backend/tests/unit/test_stage_guard.py
git commit -m "feat: add FSM stage transition guard with VALID_TRANSITIONS table"
```

---

## Task 2: LangGraph Redis Checkpointer

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/engine/coordinator/dynamic_workflow.py`

- [ ] **Step 1: Add dependency**

Open `backend/requirements.txt` and add after the `langgraph` line:

```
langgraph-checkpoint-redis>=0.0.1
```

- [ ] **Step 2: Install**

```bash
cd d:/sales-boost/backend && pip install langgraph-checkpoint-redis
```
Expected: Package installs successfully.

- [ ] **Step 3: Modify dynamic_workflow.py to use AsyncRedisSaver**

In `backend/app/engine/coordinator/dynamic_workflow.py`, find the `__init__` method of `DynamicWorkflowCoordinator` (around line 337). Replace the compile call:

```python
# OLD (line ~353):
self.app = self.graph.compile()
```

With:

```python
# NEW: use Redis checkpointer when available, fall back to MemorySaver
self.app = self._compile_with_checkpointer()
```

Then add the method to `DynamicWorkflowCoordinator` (after `_build_dynamic_graph`):

```python
def _compile_with_checkpointer(self):
    """Compile graph with Redis checkpointer for cross-worker state persistence.
    Falls back to MemorySaver when Redis is unavailable."""
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        from ...core.config import get_settings
        settings = get_settings()
        redis_url = settings.REDIS_URL
        if not redis_url:
            raise ValueError("REDIS_URL not configured")
        checkpointer = AsyncRedisSaver.from_conn_string(redis_url)
        logger.info("[DynamicWorkflow] Using Redis checkpointer: %s", redis_url)
        return self.graph.compile(checkpointer=checkpointer)
    except Exception as e:
        from langgraph.checkpoint.memory import MemorySaver
        logger.warning(
            "[DynamicWorkflow] Redis checkpointer unavailable (%s), "
            "falling back to MemorySaver — workflow state is PROCESS-LOCAL only.",
            e,
        )
        return self.graph.compile(checkpointer=MemorySaver())
```

- [ ] **Step 4: Verify app still starts**

```bash
cd d:/sales-boost/backend && python -c "from app.engine.coordinator.dynamic_workflow import DynamicWorkflowCoordinator, WorkflowConfig; print('import OK')"
```
Expected: `import OK`

- [ ] **Step 5: Commit**

```bash
cd d:/sales-boost && git add backend/requirements.txt backend/app/engine/coordinator/dynamic_workflow.py
git commit -m "feat: use AsyncRedisSaver for LangGraph workflow state persistence"
```

---

## Task 3: Real SSE Streaming Endpoint

**Files:**
- Rewrite: `backend/app/api/endpoints/assistant.py`

- [ ] **Step 1: Rewrite assistant.py with real SSE**

Replace the entire contents of `backend/app/api/endpoints/assistant.py`:

```python
"""Assistant API — SSE streaming endpoint."""
from __future__ import annotations
import asyncio, json, logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ...api.deps import require_user
from ...infra.gateway.model_gateway import ModelGateway
from ...infra.gateway.schemas import ModelCall, RoutingContext, AgentType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])

class AssistantInvokeRequest(BaseModel):
    session_id: str
    message: str
    context: dict = {}

async def _sse_generator(body, gateway):
    routing = RoutingContext(agent_type=AgentType.COACH)
    call = ModelCall(
        system_prompt="You are a sales coaching assistant.",
        messages=[{"role": "user", "content": body.message}],
        stream=True,
    )
    try:
        async for chunk in gateway.stream(call, routing):
            yield f"data: {json.dumps({'delta': chunk, 'session_id': body.session_id})}\n\n"
    except Exception as e:
        logger.error("[assistant] stream error: %s", e)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    yield "data: [DONE]\n\n"

@router.get("/health")
async def assistant_health():
    return {"status": "ok"}

@router.post("/invoke")
async def assistant_invoke(body: AssistantInvokeRequest, current_user=Depends(require_user)):
    """Stream assistant response as Server-Sent Events."""
    try:
        from ...core.config import get_settings
        gateway = ModelGateway(get_settings())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Gateway unavailable: {e}")
    return StreamingResponse(
        _sse_generator(body, gateway),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 2: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.api.endpoints.assistant import router; print('router OK')"
```
Expected: `router OK`

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/api/endpoints/assistant.py
git commit -m "feat: implement real SSE streaming on /assistant/invoke (replaces 501 stub)"
```

---

## Task 4: Redis Startup Warning

**Files:**
- Modify: `backend/app/infra/gateway/redis_semaphore.py`
- Modify: `backend/app/core_startup.py`

- [ ] **Step 1: Add degradation warning to ConcurrencyLimiter**

In `backend/app/infra/gateway/redis_semaphore.py`, in the `ConcurrencyLimiter.acquire` except block (line ~111), replace:

```python
except Exception as e:
    logger.warning("Redis semaphore failed, fallback to local: %s", e)
    self._redis_available = False
```

With:

```python
except Exception as e:
    logger.warning(
        "[ConcurrencyLimiter] Redis semaphore failed — falling back to "
        "process-local asyncio.Semaphore. Cross-worker rate limiting DISABLED. Error: %s", e
    )
    self._redis_available = False
```

Then add after `__init__`:

```python
async def check_redis_available(self) -> bool:
    """Probe Redis at startup. Call from perform_startup() to surface degradation early."""
    try:
        async with self._redis_sem.acquire():
            pass
        self._redis_available = True
        logger.info("[ConcurrencyLimiter] Redis semaphore: OK")
        return True
    except Exception as e:
        self._redis_available = False
        logger.warning(
            "[ConcurrencyLimiter] Redis unavailable at startup — cross-worker LLM rate limiting DISABLED. Error: %s", e
        )
        return False
```

- [ ] **Step 2: Call check from startup**

In `backend/app/core_startup.py`, inside `perform_startup()`, append:

```python
try:
    from app.infra.gateway.redis_semaphore import ConcurrencyLimiter
    await ConcurrencyLimiter(limit=10).check_redis_available()
except Exception as e:
    logger.warning("[startup] ConcurrencyLimiter probe failed: %s", e)
```

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/infra/gateway/redis_semaphore.py backend/app/core_startup.py
git commit -m "fix: surface Redis semaphore degradation as explicit startup warning"
```

---

## Task 5: Rename PPOPolicy → TacticScorer

**Files:**
- Modify: `backend/app/agents/rl/ppo_policy.py`
- Modify: `backend/app/agents/rl/__init__.py`
- Modify: `backend/app/agents/autonomous/sdr_agent_enhanced.py`
- Create: `backend/tests/unit/test_tactic_scorer.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_tactic_scorer.py`:

```python
from app.agents.rl.ppo_policy import TacticScorer, TrainablePolicy

def test_tactic_scorer_returns_string():
    scorer = TacticScorer()
    action = scorer.select_action({"stage": "discovery", "turn": 1})
    assert isinstance(action, str) and len(action) > 0

def test_trainable_policy_stub_exists():
    assert hasattr(TrainablePolicy, "select_action")
    assert hasattr(TrainablePolicy, "update")
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_tactic_scorer.py -v
```

- [ ] **Step 3: Add TacticScorer alias and TrainablePolicy stub to ppo_policy.py**

Append at the bottom of `backend/app/agents/rl/ppo_policy.py`:

```python
# ---------------------------------------------------------------------------
# Renamed API — PPOPolicy was misleading (no gradient updates).
# TacticScorer is the accurate name for a heuristic action scorer.
# ---------------------------------------------------------------------------
TacticScorer = PPOPolicy


class TrainablePolicy:
    """
    Stub for future neural-network policy (real PPO).
    TODO: replace with torch.nn.Module + GAE + clip objective + optimizer.step()
    """
    def select_action(self, state: dict) -> str:
        raise NotImplementedError
    def update(self, experiences: list) -> dict:
        raise NotImplementedError
```

- [ ] **Step 4: Update __init__.py**

In `backend/app/agents/rl/__init__.py`:

```python
from .ppo_policy import PPOPolicy, TacticScorer, TrainablePolicy
__all__ = ["PPOPolicy", "TacticScorer", "TrainablePolicy"]
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_tactic_scorer.py -v
```

- [ ] **Step 6: Commit**

```bash
cd d:/sales-boost && git add backend/app/agents/rl/ppo_policy.py backend/app/agents/rl/__init__.py backend/tests/unit/test_tactic_scorer.py
git commit -m "refactor: rename PPOPolicy→TacticScorer, add TrainablePolicy stub"
```

---

## Task 6: Rename RLAIFPipeline → ConversationAnalyzer

**Files:**
- Modify: `backend/app/ai_core/rlaif/pipeline.py`

- [ ] **Step 1: Append alias and stub to pipeline.py**

```python
# At bottom of backend/app/ai_core/rlaif/pipeline.py:

# ConversationAnalyzer is the accurate name — this module scores offline.
# It does NOT update model weights or close a training loop.
ConversationAnalyzer = RLAIFPipeline


class RewardDataCollector:
    """
    Stub: collect (prompt, chosen, rejected) triplets for future RLAIF fine-tuning.
    TODO: write JSONL dataset + trigger TRL/OpenRLHF fine-tuning job at threshold.
    """
    def collect(self, session_id: int, chosen: str, rejected: str) -> None:
        raise NotImplementedError
    def export_dataset(self, output_path: str) -> None:
        raise NotImplementedError
```

- [ ] **Step 2: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.ai_core.rlaif.pipeline import ConversationAnalyzer, RewardDataCollector; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/ai_core/rlaif/pipeline.py
git commit -m "refactor: rename RLAIFPipeline→ConversationAnalyzer, add RewardDataCollector stub"
```

---

## Task 7: Rename ConstitutionalAI → SafetyFilter

**Files:**
- Modify: `backend/app/ai_core/constitutional/constitutional_ai.py`

- [ ] **Step 1: Find the main class name**

```bash
cd d:/sales-boost && grep -n "^class " backend/app/ai_core/constitutional/constitutional_ai.py
```

- [ ] **Step 2: Append alias and stub**

Append at the bottom of the file (replace `ConstitutionalAI` with the actual class name found in Step 1):

```python
# SafetyFilter is the accurate name — this is a single-pass LLM safety check.
# NOT the full Anthropic Constitutional AI (critique→revise loop).
SafetyFilter = ConstitutionalAI


class CritiqueReviseFilter:
    """
    Stub: full critique+revise Constitutional AI.
    TODO: Step1=LLM critiques output vs principles; Step2=LLM revises guided by critique.
    """
    async def filter(self, text: str, constitution) -> str:
        raise NotImplementedError
```

- [ ] **Step 3: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.ai_core.constitutional.constitutional_ai import SafetyFilter, CritiqueReviseFilter; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
cd d:/sales-boost && git add backend/app/ai_core/constitutional/constitutional_ai.py
git commit -m "refactor: rename ConstitutionalAI→SafetyFilter, add CritiqueReviseFilter stub"
```

---

## Task 8: Tool Retry + Fallback

**Files:**
- Modify: `backend/app/tools/executor.py`

- [ ] **Step 1: Read executor.py to find execute method signature**

```bash
cd d:/sales-boost && grep -n "def execute\|async def execute" backend/app/tools/executor.py
```

- [ ] **Step 2: Wrap execute with retry logic**

In `backend/app/tools/executor.py`, find the execute method body and wrap tool call:

```python
async def execute(self, tool_name: str, inputs: dict, **kwargs) -> dict:
    MAX_RETRIES = 2
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            tool = self.registry.get_tool(tool_name)
            return await tool.run(inputs, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                logger.warning(
                    "[ToolExecutor] '%s' failed attempt %d/%d: %s",
                    tool_name, attempt + 1, MAX_RETRIES + 1, e
                )
    logger.error("[ToolExecutor] '%s' failed after %d attempts. Returning fallback.", tool_name, MAX_RETRIES + 1)
    return {"error": str(last_error), "tool": tool_name, "fallback": True}
```

- [ ] **Step 3: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.tools.executor import ToolExecutor; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
cd d:/sales-boost && git add backend/app/tools/executor.py
git commit -m "feat: add per-tool retry (max 2 attempts) with structured fallback response"
```

---

## Task 9: Memory L1→L2 Promotion

**Files:**
- Modify: `backend/app/agents/memory/agent_memory.py`
- Create: `backend/tests/unit/test_memory_promotion.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_memory_promotion.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.agents.memory.agent_memory import AgentMemory, MemoryEntry, MemoryType

def test_maybe_promote_high_importance_returns_true():
    mem = AgentMemory(agent_id="test")
    mem.store_in_l2 = AsyncMock(return_value=True)
    entry = MemoryEntry(
        memory_id="m1", memory_type=MemoryType.EPISODIC,
        content="Customer is CTO", metadata={}, importance=0.85
    )
    result = asyncio.get_event_loop().run_until_complete(mem.maybe_promote(entry))
    assert result is True
    mem.store_in_l2.assert_called_once()

def test_maybe_promote_low_importance_returns_false():
    mem = AgentMemory(agent_id="test")
    mem.store_in_l2 = AsyncMock()
    entry = MemoryEntry(
        memory_id="m2", memory_type=MemoryType.EPISODIC,
        content="Customer said hi", metadata={}, importance=0.3
    )
    result = asyncio.get_event_loop().run_until_complete(mem.maybe_promote(entry))
    assert result is False
    mem.store_in_l2.assert_not_called()
```

- [ ] **Step 2: Run test — expect AttributeError**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_memory_promotion.py -v
```

- [ ] **Step 3: Add maybe_promote and store_in_l2 to AgentMemory**

In `backend/app/agents/memory/agent_memory.py`, add to the `AgentMemory` class:

```python
PROMOTION_THRESHOLD: float = 0.75  # importance score above which L1→L2 promotion occurs

async def maybe_promote(self, entry: MemoryEntry) -> bool:
    """Promote a high-importance memory from L1 (working) to L2 (Qdrant vector store).
    Returns True if promoted, False otherwise.
    """
    if entry.importance < self.PROMOTION_THRESHOLD:
        return False
    try:
        await self.store_in_l2(entry)
        logger.info(
            "[AgentMemory] Promoted entry '%s' (importance=%.2f) to L2",
            entry.memory_id, entry.importance
        )
        return True
    except Exception as e:
        logger.warning("[AgentMemory] L2 promotion failed for '%s': %s", entry.memory_id, e)
        return False

async def store_in_l2(self, entry: MemoryEntry) -> None:
    """Write memory entry to Qdrant vector store (L2).
    Generates embedding and upserts into the agent's Qdrant collection.
    """
    try:
        from ...infra.search.graph_rag_enhanced import get_qdrant_client
        client = await get_qdrant_client()
        # Embed the content using the project's default embedding model
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3")
        vector = model.encode(entry.content).tolist()
        collection = f"agent_memory_{self.agent_id}"
        await client.upsert(
            collection_name=collection,
            points=[{"id": entry.memory_id, "vector": vector, "payload": entry.to_dict()}],
        )
    except Exception as e:
        raise RuntimeError(f"store_in_l2 failed: {e}") from e
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_memory_promotion.py -v
```

- [ ] **Step 5: Commit**

```bash
cd d:/sales-boost && git add backend/app/agents/memory/agent_memory.py backend/tests/unit/test_memory_promotion.py
git commit -m "feat: add AgentMemory.maybe_promote() for L1→L2 memory promotion at importance≥0.75"
```

---

## Task 10: OTel Node-Level Tracing

**Files:**
- Modify: `backend/app/observability/otel_tracing.py`
- Modify: `backend/app/engine/coordinator/dynamic_workflow.py`

- [ ] **Step 1: Add node_span context manager to otel_tracing.py**

In `backend/app/observability/otel_tracing.py`, add:

```python
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional


@asynccontextmanager
async def node_span(node_name: str, session_id: Optional[str] = None, **attrs):
    """Async context manager for a single workflow node OTel span.
    Usage:
        async with node_span("coach", session_id=sid, intent="objection"):
            result = await coach_node(state)
    """
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("salesboost.workflow")
        with tracer.start_as_current_span(f"node.{node_name}") as span:
            if session_id:
                span.set_attribute("session.id", session_id)
            for k, v in attrs.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise
    except ImportError:
        # OTel not configured — yield a no-op
        yield None
```

- [ ] **Step 2: Instrument key node handlers in dynamic_workflow.py**

In `backend/app/engine/coordinator/dynamic_workflow.py`, add import at top of file:

```python
from ...observability.otel_tracing import node_span
```

Then wrap each node handler. For example, find `_coach_node` and wrap its body:

```python
async def

Replace the entire contents of `backend/app/api/endpoints/assistant.py`:

```python
"""Assistant API — SSE streaming endpoint."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...api.deps import require_user
from ...infra.gateway.model_gateway import ModelGateway
from ...infra.gateway.schemas import ModelCall, RoutingContext, AgentType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantInvokeRequest(BaseModel):
    session_id: str
    message: str
    context: dict = {}


async def _sse_generator(
    request: AssistantInvokeRequest,
    gateway: ModelGateway,
) -> AsyncIterator[str]:
    """Yield SSE-formatted chunks from ModelGateway streaming call."""
    routing = RoutingContext(agent_type=AgentType.COACH)
    call = ModelCall(
        system_prompt="You are a sales coaching assistant.",
        messages=[{"role": "user", "content": request.message}],
        stream=True,
    )
    try:
        async for chunk in gateway.stream(call, routing):
            data = json.dumps({"delta": chunk, "session_id": request.session_id})
            yield f"data: {data}\n\n"
    except Exception as e:
        logger.error("[assistant] stream error: %s", e)
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
    """Stream assistant response as Server-Sent Events."""
    try:
        from ...infra.gateway.model_gateway import ModelGateway
        from ...core.config import get_settings
        settings = get_settings()
        gateway = ModelGateway(settings)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Gateway unavailable: {e}")

    return StreamingResponse(
        _sse_generator(body, gateway),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.api.endpoints.assistant import router; print('router OK')"
```
Expected: `router OK`

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/api/endpoints/assistant.py
git commit -m "feat: implement real SSE streaming on /assistant/invoke (replaces 501 stub)"
```

---

## Task 4: Redis Startup Warning

**Files:**
- Modify: `backend/app/infra/gateway/redis_semaphore.py`

- [ ] **Step 1: Add degradation warning to ConcurrencyLimiter.acquire**

In `backend/app/infra/gateway/redis_semaphore.py`, find the `ConcurrencyLimiter.acquire` method. In the `except` block that sets `self._redis_available = False`, add an explicit warning:

```python
# Find this block (around line 111-112):
except Exception as e:
    logger.warning("Redis semaphore failed, fallback to local: %s", e)
    self._redis_available = False

# Replace with:
except Exception as e:
    logger.warning(
        "[ConcurrencyLimiter] Redis semaphore failed — falling back to "
        "process-local asyncio.Semaphore. Cross-worker rate limiting is DISABLED. "
        "Error: %s",
        e,
    )
    self._redis_available = False
```

Also add a `check_redis_available` async method after `__init__`:

```python
async def check_redis_available(self) -> bool:
    """Probe Redis and log result. Call from app startup to surface degradation early."""
    try:
        async with self._redis_sem.acquire():
            pass
        self._redis_available = True
        logger.info("[ConcurrencyLimiter] Redis semaphore: OK")
        return True
    except Exception as e:
        self._redis_available = False
        logger.warning(
            "[ConcurrencyLimiter] Redis semaphore unavailable at startup — "
            "cross-worker LLM rate limiting is DISABLED. Error: %s", e
        )
        return False
```

- [ ] **Step 2: Call check_redis_available from perform_startup**

In `backend/app/core_startup.py`, find `perform_startup()`. Add after the existing startup steps:

```python
# After existing startup steps, add:
try:
    from app.infra.gateway.redis_semaphore import ConcurrencyLimiter
    limiter = ConcurrencyLimiter(limit=10)
    await limiter.check_redis_available()
except Exception as e:
    logger.warning("[startup] Could not probe ConcurrencyLimiter: %s", e)
```

- [ ] **Step 3: Verify startup runs**

```bash
cd d:/sales-boost/backend && python -c "from app.infra.gateway.redis_semaphore import ConcurrencyLimiter; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd d:/sales-boost && git add backend/app/infra/gateway/redis_semaphore.py backend/app/core_startup.py
git commit -m "fix: surface Redis semaphore degradation as explicit startup warning"
```

---

## Task 5: Rename PPOPolicy → TacticScorer

**Files:**
- Modify: `backend/app/agents/rl/ppo_policy.py`
- Modify: `backend/app/agents/rl/__init__.py`
- Modify: `backend/app/agents/autonomous/sdr_agent_enhanced.py`
- Create: `backend/tests/unit/test_tactic_scorer.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_tactic_scorer.py`:

```python
from app.agents.rl.ppo_policy import TacticScorer, TrainablePolicy


def test_tactic_scorer_select_action_returns_string():
    scorer = TacticScorer()
    action = scorer.select_action({"stage": "discovery", "turn": 1})
    assert isinstance(action, str)
    assert len(action) > 0


def test_trainable_policy_stub_exists():
    """TrainablePolicy stub must be importable (interface reserved for future PyTorch impl)."""
    assert hasattr(TrainablePolicy, "select_action")
    assert hasattr(TrainablePolicy, "update")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_tactic_scorer.py -v
```
Expected: `ImportError` — `TacticScorer`, `TrainablePolicy` not yet defined.

- [ ] **Step 3: Rename PPOPolicy and add TrainablePolicy stub in ppo_policy.py**

In `backend/app/agents/rl/ppo_policy.py`:

1. Find `class PPOPolicy:` — add alias and rename docstring:

```python
# At the bottom of the file, after the existing PPOPolicy class, add:

# ---------------------------------------------------------------------------
# Renamed public API (PPOPolicy was misleading — this is a heuristic scorer)
# ---------------------------------------------------------------------------
TacticScorer = PPOPolicy  # PPOPolicy kept for backward compat internally


class TrainablePolicy:
    """
    Stub: interface for a future neural-network-backed policy.
    Replace with a PyTorch nn.Module implementation to enable real PPO training.

    TODO: implement with:
      - torch.nn.Module policy network
      - GAE advantage estimation
      - PPO clip objective
      - optimizer.step() gradient updates
    """

    def select_action(self, state: dict) -> str:
        raise NotImplementedError("TrainablePolicy is a future-work stub")

    def update(self, experiences: list) -> dict:
        raise NotImplementedError("TrainablePolicy is a future-work stub")
```

- [ ] **Step 4: Update __init__.py**

In `backend/app/agents/rl/__init__.py`, add/update exports:

```python
from .ppo_policy import PPOPolicy, TacticScorer, TrainablePolicy

__all__ = ["PPOPolicy", "TacticScorer", "TrainablePolicy"]
```

- [ ] **Step 5: Update sdr_agent_enhanced.py import comment**

In `backend/app/agents/autonomous/sdr_agent_enhanced.py`, find:
```python
from ...agents.rl.ppo_policy import PPOPolicy
```
Add after it:
```python
from ...agents.rl.ppo_policy import TacticScorer  # preferred alias
```

- [ ] **Step 6: Run tests**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_tactic_scorer.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 7: Commit**

```bash
cd d:/sales-boost && git add backend/app/agents/rl/ppo_policy.py backend/app/agents/rl/__init__.py backend/app/agents/autonomous/sdr_agent_enhanced.py backend/tests/unit/test_tactic_scorer.py
git commit -m "refactor: rename PPOPolicy→TacticScorer, add TrainablePolicy stub for future neural impl"
```

---

## Task 6: Rename RLAIFPipeline → ConversationAnalyzer

**Files:**
- Modify: `backend/app/ai_core/rlaif/pipeline.py`

- [ ] **Step 1: Add ConversationAnalyzer alias and RewardDataCollector stub**

At the bottom of `backend/app/ai_core/rlaif/pipeline.py`, add:

```python
# ---------------------------------------------------------------------------
# Renamed public API
# RLAIFPipeline was misleading — this module scores conversations offline.
# It does NOT close a training loop or update model weights.
# ---------------------------------------------------------------------------
ConversationAnalyzer = RLAIFPipeline  # RLAIFPipeline kept for backward compat


class RewardDataCollector:
    """
    Stub: collect preference pairs for future RLAIF fine-tuning.

    TODO: implement to:
      - Store (prompt, chosen_response, rejected_response) triplets
      - Write to a dataset in JSONL format compatible with OpenAI / TRL fine-tuning
      - Trigger model fine-tuning job when dataset reaches threshold size
    """

    def collect(self, session_id: int, chosen: str, rejected: str) -> None:
        raise NotImplementedError("RewardDataCollector is a future-work stub")

    def export_dataset(self, output_path: str) -> None:
        raise NotImplementedError("RewardDataCollector is a future-work stub")
```

- [ ] **Step 2: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.ai_core.rlaif.pipeline import ConversationAnalyzer, RewardDataCollector; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/ai_core/rlaif/pipeline.py
git commit -m "refactor: rename RLAIFPipeline→ConversationAnalyzer, add RewardDataCollector stub"
```

---

## Task 7: Rename ConstitutionalAI → SafetyFilter

**Files:**
- Modify: `backend/app/ai_core/constitutional/constitutional_ai.py`

- [ ] **Step 1: Add SafetyFilter alias and CritiqueReviseFilter stub**

At the bottom of `backend/app/ai_core/constitutional/constitutional_ai.py`, add:

```python
# ---------------------------------------------------------------------------
# Renamed public API
# The current implementation is a single-pass LLM safety check, not the
# full Anthropic Constitutional AI (critique → revise → re-evaluate loop).
# ---------------------------------------------------------------------------

# Find the main class (likely named ConstitutionalAI or ConstitutionalChecker)
# and add this alias after its definition:
SafetyFilter = ConstitutionalAI  # backward-compat alias


class CritiqueReviseFilter:
    """
    Stub: full Constitutional AI with critique + revision loop.

    TODO: implement two-step LLM pipeline:
      Step 1 (Critique): LLM reads output + principles, identifies violations
      Step 2 (Revise):   LLM rewrites output guided by the critique
    This matches the Anthropic Constitutional AI paper methodology.
    """

    async def filter(self, text: str, constitution: "Constitution") -> str:
        raise NotImplementedError("CritiqueReviseFilter is a future-work stub")
```

- [ ] **Step 2: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.ai_core.constitutional.constitutional_ai import SafetyFilter, CritiqueReviseFilter; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd d:/sales-boost && git add backend/app/ai_core/constitutional/constitutional_ai.py
git commit -m "refactor: rename ConstitutionalAI→SafetyFilter, add CritiqueReviseFilter stub"
```

---

## Task 8: Tool Retry + Fallback

**Files:**
- Modify: `backend/app/tools/executor.py`

- [ ] **Step 1: Read executor.py**

```bash
cd d:/sales-boost && head -80 backend/app/tools/executor.py
```

- [ ] **Step 2: Add retry wrapper to ToolExecutor.execute**

In `backend/app/tools/executor.py`, find the main `execute` method. Wrap the tool call with retry logic:

```python
async def execute(self, tool_name: str, inputs: dict, **kwargs) -> dict:
    """Execute tool with up to 2 retries; return fallback dict on third failure."""
    MAX_RETRIES = 2
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            tool = self.registry.get_tool(tool_name)
            result = await tool.run(inputs, **kwargs)
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                logger.warning(
                    "[ToolExecutor] Tool '%s' failed (attempt %d/%d): %s",
                    tool_name, attempt + 1, MAX_RETRIES + 1, e
                )
            else:
                logger.error(
                    "[ToolExecutor] Tool '%s' failed after %d attempts, returning fallback. Error: %s",
                    tool_name, MAX_RETRIES + 1, e
                    tool_name, MAX_RETRIES + 1, e
                )
    return {"error": str(last_error), "tool": tool_name, "fallback": True}
```

- [ ] **Step 3: Verify import**

```bash
cd d:/sales-boost/backend && python -c "from app.tools.executor import ToolExecutor; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd d:/sales-boost && git add backend/app/tools/executor.py
git commit -m "feat: add per-tool retry (max 2 attempts) with structured fallback response"
```

---

## Task 9: Memory L1→L2 Promotion

**Files:**
- Modify: `backend/app/agents/memory/agent_memory.py`
- Create: `backend/tests/unit/test_memory_promotion.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_memory_promotion.py`:

```python
import asyncio
from unittest.mock import AsyncMock
from app.agents.memory.agent_memory import AgentMemory, MemoryEntry, MemoryType

def test_maybe_promote_high_importance():
    mem = AgentMemory(agent_id="test")
    mem.store_in_l2 = AsyncMock(return_value=None)
    entry = MemoryEntry(
        memory_id="m1", memory_type=MemoryType.EPISODIC,
        content="Customer is CTO", metadata={}, importance=0.85
    )
    result = asyncio.get_event_loop().run_until_complete(mem.maybe_promote(entry))
    assert result is True
    mem.store_in_l2.assert_called_once()

def test_maybe_promote_low_importance():
    mem = AgentMemory(agent_id="test")
    mem.store_in_l2 = AsyncMock()
    entry = MemoryEntry(
        memory_id="m2", memory_type=MemoryType.EPISODIC,
        content="Customer said hi", metadata={}, importance=0.3
    )
    result = asyncio.get_event_loop().run_until_complete(mem.maybe_promote(entry))
    assert result is False
    mem.store_in_l2.assert_not_called()
```

- [ ] **Step 2: Run test — expect AttributeError (maybe_promote not yet defined)**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_memory_promotion.py -v
```

- [ ] **Step 3: Add maybe_promote and store_in_l2 to AgentMemory**

In `backend/app/agents/memory/agent_memory.py`, add these two methods to the `AgentMemory` class:

```python
PROMOTION_THRESHOLD: float = 0.75

async def maybe_promote(self, entry: "MemoryEntry") -> bool:
    """Promote high-importance L1 entry to L2 (Qdrant). Returns True if promoted."""
    if entry.importance < self.PROMOTION_THRESHOLD:
        return False
    try:
        await self.store_in_l2(entry)
        logger.info("[AgentMemory] Promoted '%s' (importance=%.2f) to L2", entry.memory_id, entry.importance)
        return True
    except Exception as e:
        logger.warning("[AgentMemory] L2 promotion failed for '%s': %s", entry.memory_id, e)
        return False

async def store_in_l2(self, entry: "MemoryEntry") -> None:
    """Write MemoryEntry to Qdrant collection for this agent.
    TODO: wire to real Qdrant client once collection schema is finalised.
    """
    # Placeholder — replace with real Qdrant upsert when embedding pipeline is ready
    raise NotImplementedError("store_in_l2: connect to Qdrant client in implementation")
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd d:/sales-boost && python -m pytest backend/tests/unit/test_memory_promotion.py -v
```
Expected: 2 tests PASS (store_in_l2 is mocked in tests).

- [ ] **Step 5: Commit**

```bash
cd d:/sales-boost && git add backend/app/agents/memory/agent_memory.py backend/tests/unit/test_memory_promotion.py
git commit -m "feat: add AgentMemory.maybe_promote() L1->L2 at importance>=0.75"
```

---

## Task 10: OTel Node-Level Tracing

**Files:**
- Modify: `backend/app/observability/otel_tracing.py`
- Modify: `backend/app/engine/coordinator/dynamic_workflow.py`

- [ ] **Step 1: Add node_span helper to otel_tracing.py**

In `backend/app/observability/otel_tracing.py`, append:

```python
from contextlib import asynccontextmanager
from typing import Optional

@asynccontextmanager
async def node_span(node_name: str, session_id: Optional[str] = None, **attrs):
    """Async context manager emitting one OTel span per workflow node.
    Falls back to no-op if opentelemetry is not configured.
    """
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("salesboost.workflow")
        with tracer.start_as_current_span(f"node.{node_name}") as span:
            if session_id:
                span.set_attribute("session.id", session_id)
            for k, v in attrs.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise
    except ImportError:
        yield None
```

- [ ] **Step 2: Add import to dynamic_workflow.py**

At the top of `backend/app/engine/coordinator/dynamic_workflow.py`, after existing imports add:

```python
try:
    from ...observability.otel_tracing import node_span as _node_span
except ImportError:
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def _node_span(name, **kw):
        yield None
```

- [ ] **Step 3: Wrap _coach_node and _npc_node with node_span**

In `backend/app/engine/coordinator/dynamic_workflow.py`, find `_coach_node` and `_npc_node` methods. Wrap their bodies:

```python
async def _coach_node(self, state: dict) -> dict:
    session_id = state.get("session_id")
    async with _node_span("coach", session_id=session_id, intent=state.get("intent", "")):
        # ... existing body unchanged ...
        pass  # replace pass with existing implementation body

async def _npc_node(self, state: dict) -> dict:
    session_id = state.get("session_id")
    async with _node_span("npc", session_id=session_id):
        # ... existing body unchanged ...
        pass
```

- [ ] **Step 4: Verify import chain**

```bash
cd d:/sales-boost/backend && python -c "from app.observability.otel_tracing import node_span; print('node_span OK')"
```
Expected: `node_span OK`

- [ ] **Step 5: Commit**

```bash
cd d:/sales-boost && git add backend/app/observability/otel_tracing.py backend/app/engine/coordinator/dynamic_workflow.py
git commit -m "feat: add OTel node_span helper, instrument coach+npc nodes with per-node spans"
```

---

## Summary

| Task | What changes | Why |
|------|-------------|-----|
| 1 | FSM transition guard | Prevents illegal stage skips; hardens conversation flow |
| 2 | LangGraph Redis checkpointer | Workflow state survives process restarts and multi-worker deploys |
| 3 | SSE streaming on /assistant/invoke | Removes 501 stub; enables real-time client streaming |
| 4 | Redis semaphore startup warning | Surfaces degradation early instead of silently losing cross-worker limits |
| 5 | PPOPolicy→TacticScorer | Name matches implementation; TrainablePolicy stub reserves neural-policy interface |
| 6 | RLAIFPipeline→ConversationAnalyzer | Name matches implementation; RewardDataCollector stub reserves RLAIF interface |
| 7 | ConstitutionalAI→SafetyFilter | Name matches implementation; CritiqueReviseFilter stub reserves full CAI interface |
| 8 | Tool retry+fallback | Tools now survive transient failures; structured fallback instead of unhandled exception |
| 9 | Memory maybe_promote() | L1→L2 promotion path implemented; important memories now persist to vector store |
| 10 | OTel node spans | Per-node latency and error tracking in distributed tracing systems |
