# SalesBoost - AI Sales Enablement Platform

> **Canonical name**: `sales-boost` (lowercase, kebab-case)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-FF6B6B?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**AI-Powered Sales Enablement: Training, Pipeline, Methodology & Live Assist**

*Multi-Agent Orchestration • Intent Recognition • Hybrid RAG • 4-Tier Memory • FSM State Machine*

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [Innovations](#-core-innovations) • [Contributing](CONTRIBUTING.md)

</div>

---

## What is SalesBoost?

SalesBoost is an **AI-powered sales enablement platform** that helps sales teams win more deals through:

- **AI Sales Training** – Simulate customer conversations with NPC personas, get real-time coach feedback
- **Deal Pipeline Management** – Track deals with methodology frameworks (MEDDPICC, SPIN, Challenger)
- **Battle Prep** – AI-generated prep prompts and talking points before customer calls
- **Live Assist** – Real-time suggestions during calls
- **Post-Call Review** – Session replay and multi-dimensional evaluation
- **Executive Cockpit** – Pipeline overview and team analytics

### Problem We Solve

- Traditional sales training is expensive, inconsistent, and not scalable
- Deals slip due to methodology gaps (e.g., missing Economic Buyer in MEDDPICC)
- Reps lack real-time guidance during high-stakes conversations

### Solution

- **24/7 AI coaching** with SOP-grounded feedback
- **Methodology-aware pipeline** with dimension tracking and gap analysis
- **Intent-aware routing** to the right agent (Coach, NPC, Knowledge, Compliance)
- **Semantic knowledge retrieval** across sales materials

---

## Core Innovations

All items below are **implemented in code** with file paths for verification.

### AI Algorithm

| Innovation | Implementation | Evidence |
|------------|----------------|----------|
| **LLM + Keyword Intent Classification** | LLM when `ENABLE_LLM_INTENT=true`, keyword fallback on failure | [`llm_intent_classifier.py`](backend/app/services/llm_intent_classifier.py), [`intent_routing.py`](backend/app/agents/conversation/intent_routing.py) |
| **Intent Types** | INFORMATIONAL, SOCIAL, OBJECTION, BUYING_SIGNAL, CLARIFICATION, UNKNOWN | [`intent_routing.py`](backend/app/agents/conversation/intent_routing.py) L43-53 |
| **Hybrid RAG (Vector + BM25 + Reranker)** | Dense embeddings + BM25 + BGE Reranker | [`vector_store.py`](backend/app/infra/search/vector_store.py), [`bm25_retriever.py`](backend/app/infra/search/bm25_retriever.py), [`config.py`](backend/app/core/config.py) L183-215 |
| **Embedding Models** | paraphrase-multilingual-MiniLM-L12-v2, BAAI/bge-m3, text2vec-base-chinese, OpenAI | [`embedding_manager.py`](backend/app/infra/search/embedding_manager.py) L37-80 |
| **Self-RAG** | ReflectionAgent: Relevance, Faithfulness, Completeness checks | [`self_rag.py`](backend/app/retrieval/self_rag.py) L63-100 |
| **HyDE** | Hypothetical document generation for improved retrieval | [`hyde_retriever.py`](backend/app/retrieval/hyde_retriever.py) |
| **Agent Memory (3 types)** | Episodic, Semantic, Working memory with vector retrieval | [`agent_memory.py`](backend/app/agents/memory/agent_memory.py) L30-35 |
| **4-Tier Context (S0–S3)** | S0: recent messages (Redis), S1: session summary, S2: user profile, S3: tenant knowledge | [`context_manager/memory.py`](backend/app/context_manager/memory.py) L31-92 |
| **Contextual Bandit** | SimpleContextualBandit + RedisContextualBandit for routing | [`bandit.py`](backend/app/engine/coordinator/bandit.py), [`bandit_redis.py`](backend/app/engine/coordinator/bandit_redis.py) |
| **LLM-as-Judge Reward** | Multi-dimensional scoring (task_progress, quality, satisfaction, efficiency, compliance) | [`llm_reward_service.py`](backend/app/services/llm_reward_service.py) |

### AI Application Development

| Innovation | Implementation | Evidence |
|------------|----------------|----------|
| **Production Coordinator** | Unified facade, routes to DynamicWorkflow or LangGraph | [`production_coordinator.py`](backend/app/engine/coordinator/production_coordinator.py) |
| **Dynamic Workflow (LangGraph)** | Runtime-configurable nodes (intent, knowledge, NPC, coach, compliance), DAG validation | [`dynamic_workflow.py`](backend/app/engine/coordinator/dynamic_workflow.py) L113-220 |
| **FSM State Machine** | SalesStage: OPENING, NEEDS_DISCOVERY, PRODUCT_INTRO, OBJECTION_HANDLING, CLOSING | [`fsm.py`](backend/app/schemas/fsm.py) L10-18, L71-84 |
| **Self-Correcting Tool Execution** | ReflectionAgent + execute_with_correction loop | [`reflection.py`](backend/app/tools/reflection.py) L36-77, [`executor.py`](backend/app/tools/executor.py) L577-650 |
| **Prompt Version Management** | register_prompt, get_prompt_hash, list_versions, load from .md | [`prompt_registry.py`](backend/app/core/prompt_registry.py) |
| **Golden Dataset Regression** | intent_regression, prompt_hash_regression | [`test_golden_regression.py`](backend/tests/unit/test_golden_regression.py) |

### AI System Design

| Innovation | Implementation | Evidence |
|------------|----------------|----------|
| **Model Gateway** | Multi-provider routing (OpenAI, Gemini, SiliconFlow, Anthropic), Shadow Mode, tiktoken cost tracking | [`model_gateway.py`](backend/app/infra/gateway/model_gateway.py) L56-140 |
| **Redis Distributed Semaphore** | Concurrency limit for horizontal scaling | [`model_gateway.py`](backend/app/infra/gateway/model_gateway.py) L21-31, [`redis_semaphore.py`](backend/app/infra/gateway/redis_semaphore.py) |
| **Tenant Middleware** | X-Tenant-ID, token-derived tenant, public path bypass | [`tenant_middleware.py`](backend/app/api/middleware/tenant_middleware.py) |
| **Streaming Guard** | Sensitive pattern detection, content blocking | [`streaming_guard.py`](backend/app/infra/guardrails/streaming_guard.py) |
| **Compliance Agent** | COMPLIANCE_INTERCEPT_WORDS, SECURITY_INJECTION_PATTERNS, safe_rewrite | [`compliance_agent.py`](backend/app/agents/roles/compliance_agent.py), [`config.py`](backend/app/core/config.py) L234-239 |
| **OpenTelemetry** | Distributed tracing, FastAPI instrumentation | [`otel_tracing.py`](backend/app/observability/otel_tracing.py), [`main.py`](backend/main.py) L231-241 |
| **Prometheus Metrics** | Exporter for observability | [`prometheus_exporter.py`](backend/app/observability/prometheus_exporter.py) |
| **Sensitive Data Filter** | Log脱敏 | [`security_filter.py`](backend/app/logging/security_filter.py) |

### AI Product

| Innovation | Implementation | Evidence |
|------------|----------------|----------|
| **Battle Center** | Active deals, pipeline amount, methodology score, encounter count | [`BattleCenter.tsx`](frontend/src/pages/student/BattleCenter.tsx) |
| **Pipeline** | Deal CRUD, stage filter, funnel view, MEDDPICC/SPIN/Challenger | [`Pipeline.tsx`](frontend/src/pages/student/Pipeline.tsx), [`deals.py`](backend/app/api/endpoints/deals.py) |
| **Battle Prep** | Prep prompt, methodology state, key gaps, talking points | [`BattlePrep.tsx`](frontend/src/pages/student/BattlePrep.tsx), [`methodology_engine.py`](backend/app/services/methodology_engine.py) |
| **Live Assist** | Real-time copilot during calls | [`LiveAssist.tsx`](frontend/src/pages/student/LiveAssist.tsx), [`copilot.py`](backend/app/api/endpoints/copilot.py) |
| **Executive Cockpit** | Overview, funnel, methodology stats | [`Cockpit.tsx`](frontend/src/pages/admin/Cockpit.tsx), [`cockpit.py`](backend/app/api/endpoints/cockpit.py) |
| **Methodology Engine** | MEDDPICC, SPIN, Challenger dimensions, probe questions, gap analysis | [`methodology_engine.py`](backend/app/services/methodology_engine.py) L40-120 |
| **Multi-Dimensional Evaluation** | Strategy analyzer, evaluation dimensions | [`strategy_analyzer.py`](backend/app/agents/evaluate/strategy_analyzer.py) |

---

## Project Structure

```
sales-boost/
├── backend/
│   ├── main.py                 # FastAPI entry
│   ├── app/
│   │   ├── agents/             # Coach, NPC, Evaluator, Compliance, Memory, RL
│   │   ├── api/endpoints/      # REST + WebSocket
│   │   ├── engine/coordinator/ # ProductionCoordinator, DynamicWorkflow, Bandit
│   │   ├── infra/             # ModelGateway, VectorStore, BM25, Embedding
│   │   ├── retrieval/         # Self-RAG, HyDE
│   │   ├── services/          # LLM intent, Reward, Methodology, Export
│   │   ├── core/              # config, prompt_registry
│   │   └── context_manager/   # S0-S3 memory
│   ├── tests/
│   └── alembic/
├── frontend/
│   └── src/
│       ├── pages/student/     # BattleCenter, Pipeline, BattlePrep, LiveAssist, Review, Training
│       ├── pages/admin/       # Cockpit, Courses, KnowledgeBase
│       └── services/
├── deployment/docker/
└── docs/
```

---

## Technology Stack

| Layer | Stack |
|-------|-------|
| **Backend** | FastAPI, LangGraph, SQLAlchemy (async), Alembic |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Radix UI, Zustand |
| **AI/LLM** | OpenAI, Google Gemini, SiliconFlow (DeepSeek), Anthropic |
| **Embedding** | sentence-transformers (BGE, paraphrase-multilingual), OpenAI |
| **RAG** | Qdrant (optional), BM25 (rank_bm25), BGE Reranker |
| **Infra** | PostgreSQL / SQLite, Redis, Celery |
| **Observability** | OpenTelemetry, Prometheus, Sentry |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for Redis/PostgreSQL)

### Setup

```bash
git clone https://github.com/Benjamindaoson/SalesBoost.git
cd SalesBoost

# Backend
cd backend
pip install -r requirements.txt
# Set .env: SILICONFLOW_API_KEY or OPENAI_API_KEY, DATABASE_URL, REDIS_URL
python main.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Configuration

Copy `.env.example` to `.env` and set:

```env
ENV_STATE=development
DATABASE_URL=sqlite+aiosqlite:///./storage/salesboost.db
REDIS_URL=redis://localhost:6379/0
SILICONFLOW_API_KEY=your_key   # or OPENAI_API_KEY
SECRET_KEY=your_secret
```

### Run

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## Development Commands

```bash
make help              # List commands
make setup             # Install dependencies
make dev-backend       # Start backend
make dev-frontend      # Start frontend
make test              # Run tests
make test-unit         # Unit tests
make lint              # Ruff + ESLint
```

---

## Architecture

```
User → FastAPI → TenantMiddleware → ProductionCoordinator
                                          ↓
                              DynamicWorkflowCoordinator (LangGraph)
                                          ↓
                    ┌─────────────────────┼─────────────────────┐
                    ↓                     ↓                     ↓
              IntentRouter          NPC Simulator         Coach Agent
                    ↓                     ↓                     ↓
              Knowledge (RAG)        Compliance           Evaluator
                    ↓                     ↓                     ↓
              ModelGateway ←──────── Redis ←──────── ContextManager (S0-S3)
```

---

## Use Cases

1. **Sales Training** – AI coaching with NPC simulation
2. **Pipeline Management** – Deals with MEDDPICC/SPIN/Challenger
3. **Battle Prep** – Pre-call prep prompts and talking points
4. **Live Assist** – Real-time suggestions during calls
5. **Compliance** – Intercept risky phrases, suggest safe alternatives
6. **Knowledge Retrieval** – Semantic search over sales materials

---

## Roadmap

### Q1 2026 ✅
- [x] Multi-agent architecture
- [x] Hybrid RAG (BM25 + Dense + Reranker)
- [x] Production Coordinator
- [x] 4-tier context (S0-S3)
- [x] Methodology engine (MEDDPICC, SPIN, Challenger)
- [x] Battle Center, Pipeline, Live Assist

### Q2 2026 🚧
- [ ] Voice (TTS/STT)
- [ ] Multi-language
- [ ] Mobile

### Q3-Q4 2026 📋
- [ ] Fine-tuned intent model
- [ ] LangGraph checkpointer
- [ ] Cross-industry adaptation

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome PRs, bug reports, and feature ideas.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Acknowledgments

**Technologies**: FastAPI, LangGraph, React, BAAI/BGE, LangChain  
**Inspiration**: AutoGPT, CrewAI, modern sales enablement tools
