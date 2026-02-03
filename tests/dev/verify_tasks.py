import sys
import os
import random
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.infra.llm.router import SmartRouter
from app.infra.llm.adapters import AdapterFactory
from app.infra.gateway.schemas import RoutingContext, AgentType, ModelConfig, LatencyMode
from core.config import settings

async def verify_shadow_mode():
    print("\n--- Verifying Shadow Mode 1% ---")
    router = SmartRouter()
    context = RoutingContext(
        session_id="test",
        agent_type=AgentType.COACH,
        risk_level="low",
        budget_remaining=10.0,
        turn_importance=0.5,
        latency_mode=LatencyMode.FAST,
        retrieval_confidence=0.8,
        turn_number=1,
        budget_authorized=True
    )
    primary = ModelConfig(provider="openai", model_name="gpt-4")
    
    count = 0
    trials = 10000
    for _ in range(trials):
        shadow = router.select_shadow_model(context, primary)
        if shadow:
            count += 1
            
    percentage = (count / trials) * 100
    print(f"Shadow triggered {count}/{trials} times ({percentage:.2f}%)")
    if 0.5 <= percentage <= 1.5:
        print("PASS: Shadow mode is approx 1%")
    else:
        print("WARNING: Shadow mode percentage seems off (expected ~1%)")

async def verify_siliconflow_adapter():
    print("\n--- Verifying SiliconFlow Adapter ---")
    # Force settings
    settings.SILICONFLOW_API_KEY = "test-key"
    
    adapter = AdapterFactory.get_adapter("siliconflow")
    if adapter:
        print(f"Adapter found: {type(adapter)}")
        print(f"Provider name: {adapter.provider_name}")
        # Check internal client base_url if possible, or just assume success if object exists
        # OpenAIAdapter stores client. Using reflection to check base_url if needed
        try:
             print(f"Base URL: {adapter.client.base_url}")
        except:
             pass
        print("PASS: SiliconFlow adapter loaded")
    else:
        print("FAIL: SiliconFlow adapter not found")

if __name__ == "__main__":
    asyncio.run(verify_shadow_mode())
    asyncio.run(verify_siliconflow_adapter())
