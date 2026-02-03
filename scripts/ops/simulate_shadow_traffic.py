import asyncio
import logging
import sys
import os
import random
import traceback

print("Script started...")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from app.infra.gateway.model_gateway import ModelGateway
    from app.infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode, ModelConfig
    from app.infra.llm.adapters import AdapterFactory, OpenAIAdapter, GeminiAdapter
except Exception as e:
    print(f"Import Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Imports successful...")

# Setup logging to console and file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

async def simulate_traffic():
    print("--- Starting Shadow Mode Traffic Simulation ---")
    
    # Mock adapters to avoid real API calls (save money/time)
    # But we want to test the *Shadow* logic, so we might want to let it try or mock the network call.
    # Let's mock the 'chat' method of the adapters to just return dummy text + sleep.
    
    original_chat_openai = OpenAIAdapter.chat
    original_chat_gemini = GeminiAdapter.chat
    
    async def mock_chat(self, messages, config):
        await asyncio.sleep(random.uniform(0.1, 0.5))
        return f"Mock response from {config.provider}/{config.model_name}"
        
    OpenAIAdapter.chat = mock_chat
    GeminiAdapter.chat = mock_chat
    
    gateway = ModelGateway()
    
    # Create a context that is likely to trigger shadow (we can force it by patching router if needed, 
    # but we want to test the 1% logic too. 
    # To see it trigger, we need MANY calls or we can patch random temporarily).
    
    # Let's patch random.random to return 0.0 to FORCE shadow for this test
    original_random = random.random
    random.random = lambda: 0.0 # Always < 0.01
    
    print("Force-enabled Shadow Mode (random=0.0)")
    
    tasks = []
    for i in range(5):
        context = RoutingContext(
            session_id=f"test-session-{i}",
            agent_type=AgentType.COACH,
            turn_importance=0.8,
            risk_level="low",
            budget_remaining=10.0,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=0.9,
            turn_number=i,
            budget_authorized=True
        )
        
        call = ModelCall(
            prompt=f"Hello, this is request {i}",
            config=ModelConfig(provider="openai", model_name="gpt-4")
        )
        
        print(f"Sending request {i}...")
        # We await the main call, but shadow is background
        response = await gateway.call(call, context)
        print(f"Main response: {response}")
    
    # Restore random
    random.random = original_random
    
    # Wait for shadow tasks (they are background tasks in asyncio loop)
    print("Waiting for background shadow tasks...")
    await asyncio.sleep(2) 
    
    print("--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(simulate_traffic())
