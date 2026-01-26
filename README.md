# SalesBoost

SalesBoost is a multi-agent sales coaching platform built on FastAPI, Hybrid Control FSM, and RAG. The backend separates agent roles, coordination, and supporting services so the system is easy to reason about and extend.

## Highlights

- Multi-agent roles: Intent Gate, NPC, Coach, Evaluator, RAG, Compliance
- Coordination layer for session orchestration (V2 + V3)
- LLM router with multi-provider support (Qwen/GLM/OpenAI)
- Hybrid Control FSM for deterministic stage transitions
- Ingestion + knowledge services for retrieval-augmented generation

## Project Structure

```
SalesBoost/
?? app/
?  ?? agents/
?  ?  ?? roles/                # Agent role implementations
?  ?  ?? coordination/         # Orchestrators and dispatch
?  ?  ?? v3/                   # V3 agent variants
?  ?? api/                     # REST + WebSocket endpoints
?  ?? core/                    # Config, DB, Redis, LLM routing
?  ?? fsm/                     # Hybrid Control FSM
?  ?? models/                  # SQLAlchemy models
?  ?? schemas/                 # Pydantic schemas
?  ?? services/                # Business and infrastructure services
?  ?? sales_simulation/        # Offline simulation + datasets
?  ?? tasks/                   # Background tasks
?? docs/                       # Architecture and guides
?? scripts/                    # CLI and maintenance utilities
?? frontend/                   # React client
?? alembic/                    # DB migrations
?? requirements.txt
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for OpenAPI docs.

## LLM Configuration

Set provider keys in `.env`:

```env
DASHSCOPE_API_KEY=your_dashscope_key
ZHIPU_API_KEY=your_zhipu_key
OPENAI_API_KEY=optional
```

Model mapping can be overridden via:

```env
LLM_MODEL_INTENT_GATE=qwen-turbo
LLM_MODEL_NPC=qwen-plus
LLM_MODEL_COACH=qwen-max
LLM_MODEL_EVALUATOR=glm-4
LLM_MODEL_RAG=glm-4-flash
LLM_MODEL_COMPLIANCE=qwen-turbo
```

## Docs

- `docs/architecture.md`
- `docs/runbook.md`
- `docs/usage_examples.md`
- `docs/rag/` (integration, advanced usage, optimization)
- `docs/ingestion/` (guide and v2 design)
- `docs/system_design/agentic_architecture_v3.md`
- `docs/ops/model_gateway.md`

## Simulation

Offline multi-agent simulation tooling lives in `app/sales_simulation/`.
See `docs/simulation/demo.md` and `app/sales_simulation/README.md` for usage.

## Tests

```bash
pytest
```

## License

MIT. See `LICENSE`.
