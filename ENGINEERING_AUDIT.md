# Engineering Audit Report

**Date**: 2026-01-18
**Auditor**: Staff Engineer

## 1. System Execution Path (Verified)

The system follows a clean "Orchestrator-driven" architecture.

1.  **Entry**: `app/api/endpoints/websocket.py` handles the connection lifecycle.
2.  **Session**: A new `SessionOrchestrator` is instantiated for each WebSocket connection.
3.  **Turn Loop**:
    -   `Orchestrator.process_turn` is the central coordinator.
    -   **Agents**: Intent -> (RAG | Compliance) -> NPC -> Coach -> Evaluator.
    -   **Feedback Loops**:
        -   **Adoption**: `AdoptionTracker` checks if previous advice was taken.
        -   **Strategy**: `StrategyAnalyzer` records strategy decisions.
        -   **Curriculum**: `CurriculumPlanner` updates user profile at session end.
4.  **Persistence**:
    -   Async SQLAlchemy with SQLite (`salesboost.db`).
    -   Transactional writes per turn (`Message`, `StrategyDecision`, `AdoptionRecord`).

## 2. Findings & Issues

### 🔴 Critical: Fake RAG Implementation
-   **Status**: `FAILED` (Fake Implementation)
-   **File**: `app/agents/rag_agent.py`
-   **Issue**: The agent uses a hardcoded `_init_mock_knowledge_base` dictionary. It **does not** connect to the `KnowledgeService` (ChromaDB) found in `app/services/knowledge_service.py`.
-   **Impact**: Any documents uploaded via the API are ignored by the Coach.
-   **Action Required**: Rewrite `RAGAgent` to inject and use `KnowledgeService`.

### ⚠️ Warning: Concurrency Risks
-   **Status**: Needs Verification
-   **Component**: `ConnectionManager` in `websocket.py`
-   **Issue**: Uses global dictionaries (`active_connections`, `orchestrators`). While acceptable for a single-process server, it relies on `session_id` uniqueness.
-   **Action Required**: Stress test with `tests/test_concurrent_sessions.py`.

### ⚠️ Warning: Dead Code / Tech Debt
-   **Redis**: `app/core/redis.py` is initialized in `main.py` but appears unused in the core logic (Orchestrator uses in-memory state).
-   **Scripts**: `scripts/` contains manual testing scripts (`test_ws_auto.py`) that should be superseded by `pytest`.

## 3. Cleanup Plan

1.  **RAG**: Connect `RAGAgent` to `KnowledgeService`. Remove mock data.
2.  **Tests**: Establish a reliable `pytest` harness for WebSocket (replacing manual scripts).
3.  **Linting**: Apply `ruff` and `black`.

## 4. True Capabilities vs. Claims

| Feature | Claimed | Actual | Verdict |
| :--- | :--- | :--- | :--- |
| **Session Isolation** | Yes | Likely (New instance per conn) | ✅ Pass (Pending Load Test) |
| **RAG Knowledge** | Yes | **NO** (Uses hardcoded dict) | ❌ **FAIL** (Must Fix) |
| **Learning Loop** | Yes | Yes (DB records exist) | ✅ Pass |
| **Anti-Cheat** | Yes | Basic String Match | ⚠️ Weak (Needs Vector/LLM) |

---
**Next Immediate Action**: Fix RAG implementation and then run Concurrency Tests.
