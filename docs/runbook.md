# SalesBoost Runbook

## Prerequisites
- Python 3.10+
- SQLite (Built-in)
- Redis (Optional, falls back to memory)

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
