# Engineering Cleanup Log

**Date**: 2026-01-18

## 1. Code Removal
- **Deleted**: `scripts/test_ws_auto.py` (Superseded by `tests/test_ws_integration.py` and `tests/test_concurrent_sessions.py`).
- **Deleted**: `app/models/analysis_models.py` (Duplicate of `strategy.py`).

## 2. Refactoring
- **RAG Agent**:
    -   **Before**: Hardcoded `_init_mock_knowledge_base` dictionary.
    -   **After**: Connected to `KnowledgeService` (ChromaDB).
    -   **Status**: ✅ Real implementation active.
- **Prompts**:
    -   Extracted `CoachAgent` prompt to `app/prompts/coach_prompt.md`.
    -   Extracted `EvaluatorAgent` prompt to `app/prompts/evaluator_prompt.md`.

## 3. Configuration
- **Linting**: `pyproject.toml` configured with `ruff` and `black`.
- **Dependencies**: Added `chromadb`, `sentence-transformers`, `pytest-asyncio`.

## 4. Anti-Cheat
-   Added "Parroting Penalty" in `AdoptionTracker`.
-   If user verbatim copies the example, `skill_delta` is penalized (0.3x multiplier).

## 5. Directory Structure (Current)
-   `app/agents/`: LLM Agents (Coach, NPC, Evaluator, RAG).
-   `app/services/`: Core Logic (Orchestrator, Tracker, Planner, Knowledge).
-   `app/api/`: Endpoints.
-   `app/prompts/`: Externalized prompts.
-   `tests/`: Comprehensive test suite.
