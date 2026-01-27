# SalesBoost Runbook

## Prerequisites
- Python 3.10+
- PostgreSQL 16+ (production)
- Redis (recommended)

## Installation
```bash
pip install -r requirements.txt
pip install chromadb sentence-transformers  # For RAG & Vector Matching
```

## Running the Server
```bash
# Start server (default port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# If 8000 is busy, use 8001
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Running Tests
```bash
# Run all tests
python -m pytest tests -v

# Run specific test
python -m pytest tests/test_ws_turn_loop.py -v
```

## Observability
- Metrics endpoint: `GET /metrics`
- Health endpoint: `GET /health`

## Required Env Vars (Production)
- `SECRET_KEY`
- `ADMIN_PASSWORD_HASH`
- `DATABASE_URL`
- `REDIS_URL`

## Release & Rollback (Docker)
1. **Blue/Green**: deploy a new stack with a different project name (e.g., `salesboost-green`) and switch traffic at the load balancer.
2. **Rollback**: switch traffic back to the previous stack, then decommission the new stack.

## API Usage

### 1. Ingest Knowledge (RAG)
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/text" \
  -H "Content-Type: application/json" \
  -d '{"content": "Price objection handling...", "source": "manual", "stage": "objection_handling"}'
```

### 2. Get User Profile
```bash
curl "http://localhost:8000/api/v1/profile/{user_id}/strategy"
```

## Troubleshooting
- **Port Conflict**: Use `netstat -ano | findstr :8000` to find PID, then `taskkill /F /PID <PID>`.
- **Missing Dependencies**: Ensure `sentence-transformers` is installed for vector matching features.
