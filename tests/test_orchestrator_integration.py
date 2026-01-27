
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.engine.coordinator.workflow_coordinator import SalesOrchestrator
from app.infra.gateway.model_gateway import ModelGateway, AgentType
from app.infra.gateway.model_gateway.budget import BudgetManager
from app.agents.coordination.session_director_v3 import SessionDirectorV3
from app.models.config_models import CustomerPersona
from app.schemas.fsm import FSMState, SalesStage
from app.core.redis import InMemoryCache
from app.engine.state.write_ahead_log import wal_manager

# Mock data
MOCK_NPC_RESPONSE = "Hello Salesperson."
MOCK_METADATA = '{"mood_before": 0.5, "mood_after": 0.6, "mood_change_reason": "greeting", "expressed_signals": ["smile"], "persona_consistency": 1.0, "response": "Hello Salesperson."}'
MOCK_STREAM_TOKENS = ["Hello", " ", "Sales", "person", ".", "\n", "###METADATA###", "\n", MOCK_METADATA]

@pytest.fixture
def mock_model_gateway():
    gateway = AsyncMock(spec=ModelGateway)
    
    async def mock_chat_stream(*args, **kwargs):
        for token in MOCK_STREAM_TOKENS:
            await asyncio.sleep(0.01)
            yield token
            
    gateway.chat_stream.side_effect = mock_chat_stream
    gateway.chat.return_value = {
        "content": "Coach advice",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        "cost_usd": 0.001,
        "latency_ms": 100
    }
    gateway.get_stats.return_value = {"call_stats": {}}
    return gateway

@pytest.fixture
def mock_budget_manager():
    bm = MagicMock(spec=BudgetManager)
    bm.is_authorized.return_value = True
    bm.get_remaining_budget.return_value = 10.0
    return bm

@pytest.fixture
def mock_session_director():
    director = AsyncMock(spec=SessionDirectorV3)
    return director

@pytest.fixture
def mock_persona():
    return CustomerPersona(
        id="p1",
        scenario_id="s1",
        name="Test Persona",
        occupation="Tester",
        personality_traits="Critical, Detailed",
        communication_style="Professional",
        buying_motivation="Test system",
        main_concerns="Bugs",
        initial_mood=0.5,
        difficulty_level="intermediate"
    )

@pytest.mark.asyncio
async def test_orchestrator_execute_turn_stream(
    mock_model_gateway, 
    mock_budget_manager, 
    mock_session_director, 
    mock_persona
):
    # 1. Setup WAL with InMemoryCache
    wal_manager.redis = InMemoryCache()
    wal_manager._redis_initialized = True
    
    # 2. Patch global dependencies
    with patch("app.agents.roles.base.model_gateway", mock_model_gateway), \
         patch("app.security.runtime_guard.runtime_guard.check_input", return_value=("allow", None)), \
         patch("app.security.runtime_guard.runtime_guard.check_output", return_value=("allow", "Hello Salesperson.", None)), \
         patch("app.agents.study.knowledge_retriever.knowledge_engine.retrieve", return_value=[]):
        
        # 3. Initialize Orchestrator
        orchestrator = SalesOrchestrator(
            model_gateway=mock_model_gateway,
            budget_manager=mock_budget_manager,
            session_director=mock_session_director,
            persona=mock_persona
        )
        
        session_id = "test_session_stream"
        fsm_state = FSMState(current_stage=SalesStage.OPENING, turn_count=0, npc_mood=0.5)
        orchestrator.initialize_session(session_id, "user1", fsm_state)
        
        # 4. Execute Turn Stream
        tokens_received = []
        result_received = None
        
        async for chunk in orchestrator.execute_turn_stream(
            turn_number=1,
            user_message="Hello",
            db=None
        ):
            if chunk["type"] == "token":
                tokens_received.append(chunk["content"])
            elif chunk["type"] == "result":
                result_received = chunk["data"]
            elif chunk["type"] == "error":
                pytest.fail(f"Received error chunk: {chunk['message']}")
        
        # 5. Verify Tokens
        full_text = "".join(tokens_received)
        assert "Hello Salesperson." in full_text
        # Note: Depending on buffering logic, we might get "Hello Salesperson.\n" or similar.
        # The MOCK_STREAM_TOKENS has "\n" then "###METADATA###".
        # The separator is NOT yielded as token.
        assert "###METADATA###" not in full_text
        
        # 6. Verify Result
        assert result_received is not None
        assert result_received.fast_path_result.npc_reply.response == "Hello Salesperson."
        assert result_received.fast_path_result.npc_reply.mood_after == 0.6
        
        # 7. Verify WAL Logs
        events = await wal_manager.get_events(session_id)
        assert len(events) >= 2 # USER_INPUT, FAST_PATH_RESULT
        assert events[0]["type"] == "USER_INPUT"
        assert events[1]["type"] == "FAST_PATH_RESULT"
