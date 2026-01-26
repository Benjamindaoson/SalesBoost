# SalesBoost Architecture

## Overview
SalesBoost is a multi-agent sales training platform with a central coordination layer that manages turn-by-turn execution. The system follows a clean architecture style to keep agent roles, orchestration, and services separated.

## Core Components

### 1. Orchestration (`app/agents/coordination/orchestrator.py`)
- **Role**: Session brain and turn loop owner.
- **Responsibilities**:
  - Coordinates agent roles (Intent, NPC, Coach, Evaluator, RAG, Compliance).
  - Persists strategy/adoption results (single write path).
  - Triggers curriculum planning on session completion.

### 2. Agent Roles (`app/agents/roles/`)
- **Intent Gate**: Classifies intent and stage relevance.
- **NPC**: Simulates customer responses.
- **Coach**: Generates coaching advice.
- **Evaluator**: Scores and analyzes performance.
- **RAG**: Retrieves knowledge to ground responses.
- **Compliance**: Safety and rule checks.

### 3. Data Persistence (SQLite/SQLAlchemy)
- **Sessions**: `sessions` table.
- **Messages**: `messages` table.
- **Adoption**: `adoption_records` (advice follow-through).
- **Strategy**: `strategy_decisions` (user strategy vs optimal).
- **Profile**: `user_strategy_profiles`.

## Key Flows

### A. Turn Execution
1. User message -> WebSocket.
2. Orchestrator -> Intent Gate.
3. Orchestrator -> NPC.
4. Orchestrator -> Coach.
5. Orchestrator -> Evaluator.
6. Orchestrator -> Adoption/Strategy tracking.
7. DB commit.

### B. Session Completion
1. Turn loop ends (Stage = COMPLETED).
2. Orchestrator -> CurriculumPlanner.
3. Planner updates `UserStrategyProfile` and next focus.

## Directory Structure
- `app/main.py`: Entry point.
- `app/api/`: REST & WebSocket endpoints.
- `app/agents/roles/`: Agent role implementations.
- `app/agents/coordination/`: Orchestrators and dispatch.
- `app/agents/v3/`: V3 agent variants.
- `app/services/`: Supporting services (ingestion, knowledge, RAG, etc.).
- `app/models/`: DB models.
- `app/schemas/`: Pydantic schemas.
- `tests/`: Pytest suite.
