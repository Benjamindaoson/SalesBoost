# SalesBoost Architecture

## Overview
SalesBoost is a Multi-Agent Sales Training Platform.
It uses a **Clean Architecture** approach with a central **Orchestrator** managing the data flow.

## Core Components

### 1. Orchestrator (`app/services/orchestrator.py`)
- **Role**: The "Brain".
- **Responsibilities**:
  - Manages the Turn Loop.
  - Coordinates Agents (Intent, NPC, Coach, Evaluator, RAG).
  - **Writes to DB** (Single Source of Truth for Writes).
  - Triggers **CurriculumPlanner** on session completion.

### 2. Data Persistence (SQLite/SQLAlchemy)
- **Sessions**: `sessions` table (Life-cycle managed).
- **Messages**: `messages` table (Full history).
- **Adoption**: `adoption_records` (Did the user listen?).
- **Strategy**: `strategy_decisions` (User vs Golden Strategy).
- **Profile**: `user_strategy_profiles` (Long-term learning model).

### 3. Feedback Loops
- **Loop 1: Real-time Coaching**: Coach Agent provides immediate advice.
- **Loop 2: Adoption Tracking**: `AdoptionTracker` checks if advice was taken in next turn.
- **Loop 3: Curriculum Planning**: `CurriculumPlanner` analyzes long-term patterns to recommend next scenario.

## Key Flows

### A. Turn Execution
1. User Message -> WebSocket.
2. Orchestrator -> IntentGate (Check relevance).
3. Orchestrator -> NPC (Generate response).
4. Orchestrator -> Coach (Generate advice).
5. Orchestrator -> Evaluator (Score & Analyze).
6. Orchestrator -> **AdoptionTracker** (Check previous advice).
7. Orchestrator -> **StrategyAnalyzer** (Record strategy).
8. DB Commit.
9. Return JSON to Client.

### B. Session Completion
1. Turn Loop Ends (Stage = COMPLETED).
2. Orchestrator -> **CurriculumPlanner**.
3. Planner updates `UserStrategyProfile`.
4. Planner generates `next_training_focus`.
5. Return "Session Complete" + Recommendation.

## Directory Structure
- `app/main.py`: Entry point.
- `app/api/`: REST & WebSocket endpoints.
- `app/services/`: Core logic (Orchestrator, Tracker, Planner).
- `app/agents/`: LLM Wrappers.
- `app/models/`: DB Models.
- `app/schemas/`: Pydantic Models.
- `tests/`: Pytest suite.
