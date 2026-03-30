
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
from app.infra.gateway.model_gateway import ModelGateway
from app.schemas.fsm import FSMState, SalesStage

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_workflow():
    print("Initializing WorkflowCoordinator with LangGraph...")
    
    # Mock Dependencies
    mock_gateway = MagicMock(spec=ModelGateway)
    # Mock gateway methods to return something valid
    # intent classifier, npc, coach all use gateway
    # For intent:
    mock_gateway.call = AsyncMock(return_value="price_inquiry") 
    
    # Mock budget manager etc
    mock_budget = MagicMock()
    mock_director = MagicMock()
    mock_persona = {
        "name": "John Doe",
        "role": "Purchasing Manager",
        "company": "Acme Corp"
    }
    
    # Initialize
    coordinator = WorkflowCoordinator(
        model_gateway=mock_gateway,
        budget_manager=mock_budget,
        session_director=mock_director,
        persona=mock_persona
    )
    
    # Initialize Session
    state = FSMState(current_stage=SalesStage.DISCOVERY, turn_count=0, npc_mood=0.5)
    coordinator.initialize_session("test_session", "user_1", state)
    
    print("Executing Turn 1...")
    # We need to mock the internal components behavior because we are not running real LLMs
    # But DynamicWorkflowCoordinator instantiates real components (NPCGenerator, etc).
    # These components will call model_gateway.
    # So we just need to ensure model_gateway returns valid strings that can be parsed.
    
    # NPCGenerator expects a response
    # CoachAgent expects a response
    # Intent expects a response
    
    # To make it simple, let's just run it and see if it crashes on imports or graph construction.
    # If it hits the network/gateway, it will use our mock.
    
    # Mocking gateway.call is tricky because different agents expect different formats.
    # But let's try.
    mock_gateway.call.return_value = "Hello, I am interested in your product." 
    
    # Run
    try:
        result = await coordinator.execute_turn(1, "How much does it cost?")
        print("\nTurn Result:")
        print(f"Intent: {result.intent}")
        print(f"NPC Reply: {result.npc_reply.response}")
        print(f"Stage: {result.stage}")
        print(f"Trace: {result.trace}")
        print("\nSUCCESS: WorkflowCoordinator ran successfully with LangGraph!")
    except Exception as e:
        print(f"\nFAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_workflow())
