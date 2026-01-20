# Engineering TODOs

## High Priority (Stability)
- [ ] **Fix CI/Test Environment**: The current WebSocket integration test (`tests/test_ws_integration.py`) fails in the local shell environment due to subprocess/port binding issues. Needs a Dockerized test runner.
- [ ] **Optimize RAG**: Currently using local ChromaDB. Move to a separate service for production.
- [ ] **Frontend Integration**: The backend is ready (Profile API, WebSocket Feedback), but no UI exists to display it.

## Medium Priority (Features)
- [ ] **Voice Support**: Add STT/TTS to the WebSocket stream.
- [ ] **Multi-User Scaling**: Move from SQLite to PostgreSQL.
- [ ] **Admin Dashboard**: View global usage stats.

## Low Priority (Tech Debt)
- [ ] **Type Checking**: Run `mypy` strict mode.
- [ ] **Logging**: Implement structured logging (JSON) for ELK stack.
