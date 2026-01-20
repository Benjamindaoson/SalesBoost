# Scale Limits Analysis

**Date**: 2026-01-18

## 1. Single Node Limits (Current Architecture)
Based on `python:3.11-slim` container with 4vCPU, 8GB RAM.

| Resource | Bottleneck | Estimated Limit | Explanation |
| :--- | :--- | :--- | :--- |
| **Concurrent WebSocket** | Python GIL / Event Loop | ~1,000 Conn | FastAPI/Uvicorn is efficient, but heavy logic per turn blocks the loop if not careful. |
| **RAG Retrieval** | Vector Search (CPU) | ~50 QPS | `ChromaDB` (embedded) runs in-process. Heavy search blocks the worker. |
| **LLM Orchestration** | Network I/O | Unlimited* | Bound by OpenAI API rate limits, not local CPU. |
| **Database (SQLite)** | Write Lock | ~10 TPS | SQLite locks the file on write. Concurrent turns will timeout. |

## 2. Breaking Points
### Scenario A: 100 Users Training Simultaneously
-   **Status**: ⚠️ Risky with SQLite.
-   **Symptom**: `database is locked` errors.
-   **Fix**: Switch to PostgreSQL (`asyncpg`).

### Scenario B: 1,000 Users
-   **Status**: ❌ Will Crash.
-   **Symptom**: Memory OOM (ChromaDB index + Session State).
-   **Fix**:
    -   External Vector DB (Pinecone/Milvus).
    -   Redis for Session State.
    -   Horizontal Scaling (K8s).

## 3. Scaling Path
1.  **Level 1 (Current)**: Dev / Demo. SQLite, In-Memory. (Limit: 10 concurrent users).
2.  **Level 2 (MVP)**: PostgreSQL, Chroma Persistent. (Limit: 100 concurrent users).
3.  **Level 3 (Prod)**: K8s, Redis Pub/Sub, External Vector DB. (Limit: 10k+ users).

## 4. Latency Budget
-   **Turn Latency**: Currently ~2-3s (mostly LLM).
-   **System Overhead**: ~200ms (RAG + DB + Logic).
-   **Optimization**: System overhead is negligible compared to LLM generation.
