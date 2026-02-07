import asyncio
import logging
from dotenv import load_dotenv
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_gemini():
    print("\n=== Testing Google Gemini Integration ===")
    
    gateway = ModelGateway()
    
    if not gateway.google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment.")
        return

    call = ModelCall(
        prompt="Explain how AI works in a few words",
        system_prompt="You are a helpful assistant."
    )
    
    from app.infra.gateway.schemas import AgentType, LatencyMode
    context = RoutingContext(
        session_id="test-gemini-session",
        agent_type=AgentType.NPC,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=10.0,
        latency_mode=LatencyMode.FAST,
        retrieval_confidence=None,
        turn_number=1,
        budget_authorized=True
    )
    
    try:
        print(f"Calling Gemini ({gateway.gemini_model})...")
        response = await gateway.call(call, context)
        print(f"✅ Success! Gemini Response: {response}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_gemini())
