
import asyncio
import json
from salesagent.orchestration.nodes.analyzer import analyzer_node
from salesagent.orchestration.state import AgentState
from salesagent.core.settings import settings

class MockGateway:
    async def complete(self, task, system, user, session_id="", response_format="text"):
        return json.dumps({
            "trust_score": 85,
            "urgency": 70,
            "friction_points": ["technical_integration"],
            "intent_cluster": "solution_seeking"
        })

async def test_analyzer():
    print("Testing Analyzer Node...")
    gateway = MockGateway()
    state: AgentState = {
        "session_id": "test_session",
        "messages": [
            {"role": "user", "content": "How do I integrate this with our CRM?"}
        ],
        "user_message": "How do I integrate this with our CRM?"
    }

    # Force mock mode for test
    settings.mock_llm = False

    new_state = await analyzer_node(state, gateway)

    persona = new_state.get("customer_profile", {}).get("persona_vector")
    radar = new_state.get("intent_radar")

    print(f"Persona Vector: {persona}")
    print(f"Intent Radar: {radar}")

    assert persona["trust_score"] == 85
    assert persona["intent_cluster"] == "solution_seeking"
    assert radar["trust"] == 0.85
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test_analyzer())
