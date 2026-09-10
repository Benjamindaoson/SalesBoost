# SalesAgent V3 Testing Guide

## Setup

1. Install test dependencies:
```bash
pip install -r tests/requirements.txt
```

2. Create test database:
```bash
createdb salesagent_test
```

3. Run migrations on test database:
```bash
alembic upgrade head
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_fsm.py
```

### Run with coverage
```bash
pytest tests/ --cov=engine --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

## Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_chat_flow.py` - Integration tests for chat endpoints
- `test_fsm.py` - Unit tests for FSM state machine
- `test_guard.py` - Unit tests for Guard rules
- `test_memory.py` - Unit tests for Memory decay

## Writing New Tests

Follow these conventions:
- Use `@pytest.mark.asyncio` for async tests
- Use descriptive test names: `test_<feature>_<scenario>`
- Use fixtures from `conftest.py` for DB and HTTP client
- Mock external services (LLM APIs) in unit tests
