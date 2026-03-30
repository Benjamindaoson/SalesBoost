import asyncio
import logging
from dotenv import load_dotenv
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_siliconflow():
    print("\n=== Testing SiliconFlow Integration ===")
    
    gateway = ModelGateway()
    
    if not gateway.sf_api_key:
        print("❌ Error: SILICONFLOW_API_KEY not found in environment.")
        return

    # Test 1: Default Model (Qwen-7B)
    print(f"\nTest 1: Calling SiliconFlow with Default Model ({gateway.sf_model})...")
    call = ModelCall(
        prompt="请介绍一下你自己",
        system_prompt="你是一个有用的助手"
    )
    
    context = RoutingContext(
        session_id="test-sf-session",
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
        response = await gateway.call(call, context)
        print(f"✅ Success! Response: {response}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 2: Paid Model (GLM-4)
    print("\nTest 2: Calling SiliconFlow with Paid Model (THUDM/glm-4-9b-chat)...")
    from app.infra.gateway.schemas import ModelConfig
    call_paid = ModelCall(
        prompt="你好，请介绍一下你自己",
        system_prompt="你是一个有用的助手",
        config=ModelConfig(provider="siliconflow", model_name="THUDM/glm-4-9b-chat")
    )
    
    try:
        response = await gateway.call(call_paid, context)
        print(f"✅ Success! Response: {response}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_siliconflow())
