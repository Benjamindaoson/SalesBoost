
import pytest
import asyncio
from unittest.mock import MagicMock
from cognitive.skills.v3.npc_generator_v3 import NPCGeneratorV3
from cognitive.infra.gateway.model_gateway import ModelGateway
from cognitive.infra.gateway.model_gateway.budget import BudgetManager
from models.config_models import CustomerPersona
from cognitive.skills.roles.npc_agent import PersonaProfile
from schemas.fsm import FSMState, SalesStage
from schemas.agent_outputs import IntentGateOutput

@pytest.mark.asyncio
async def test_npc_generator_stream():
    # 1. Setup Mock Gateway
    mock_gateway = MagicMock(spec=ModelGateway)
    
    # Mock chat_stream to yield tokens and then metadata
    async def mock_chat_stream(*args, **kwargs):
        tokens = ["Hello", " ", "Salesperson", ".", "\n", "###METADATA###", "\n", '{"response": "Hello Salesperson.", "mood_before": 0.5, "mood_after": 0.6, "mood_change_reason": "good greeting", "expressed_signals": ["smile"], "persona_consistency": 1.0}']
        for token in tokens:
            await asyncio.sleep(0.01) # Simulate delay
            yield token

    mock_gateway.chat_stream = mock_chat_stream

    # 2. Setup Dependencies
    mock_budget_manager = MagicMock(spec=BudgetManager)
    mock_budget_manager.get_remaining_budget.return_value = 10.0
    
    persona = CustomerPersona(
        name="TestCustomer",
        occupation="Manager",
        personality_traits=["Direct"],
        communication_style="Professional"
    )
    
    profile = PersonaProfile(
        name="TestCustomer",
        industry="Tech",
        objection_style="Price",
        difficulty_level="Medium"
    )

    # 3. Initialize Generator
    generator = NPCGeneratorV3(
        model_gateway=mock_gateway,
        budget_manager=mock_budget_manager,
        persona=persona
    )
    # Inject persona profile into internal agent
    generator.npc_agent.set_persona(profile)
    # Inject mock gateway into agent's global context (this is tricky as agent uses global 'model_gateway' import)
    # But wait, BaseAgent uses 'from cognitive.infra.gateway.model_gateway import model_gateway'
    # We need to patch that global instance.
    
    # Patching global model_gateway
    with pytest.MonkeyPatch.context() as m:
        from cognitive.skills.roles import base
        m.setattr(base, "model_gateway", mock_gateway)
        
        # 4. Prepare Inputs
        fsm_state = FSMState(current_stage=SalesStage.OPENING, history=[])
        intent_result = IntentGateOutput(
            detected_intent="greeting",
            is_aligned=True,
            confidence=0.9,
            alignment_reason="aligned",
            detected_slots=[],
            missing_slots=[]
        )
        
        # 5. Run Stream
        received_tokens = []
        received_result = None
        
        print("\n--- Starting Stream ---")
        async for chunk in generator.generate_stream(
            user_message="Hi there!",
            conversation_history=[],
            fsm_state=fsm_state,
            intent_result=intent_result,
            session_id="test_session",
            turn_number=1,
            retrieval_confidence=1.0
        ):
            if chunk["type"] == "token":
                print(f"Token: {chunk['content']}")
                received_tokens.append(chunk["content"])
            elif chunk["type"] == "result":
                print(f"Result: {chunk['data']}")
                received_result = chunk["data"]
        
        # 6. Verify
        full_text = "".join(received_tokens)
        assert "Hello Salesperson." in full_text
        assert received_result is not None
        assert received_result.mood_after == 0.6
        print("\n--- Test Passed ---")

if __name__ == "__main__":
    asyncio.run(test_npc_generator_stream())
