import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.schemas.blackboard import BlackboardSchema, SalesStageEstimate, CustomerPsychology, StateConfidence, ExternalContext
from app.agents.autonomous.sdr_agent import SDRAgent

async def run_demo():
    print("🚀 Starting AI SDR Demo: Transforming Simulator to Employee...\n")
    
    # 1. Initialize the Brain (Blackboard) with Real World Context
    blackboard = BlackboardSchema(
        session_id="live_call_001",
        user_id="sdr_bot_v1",
        mode="live_shadow",  # New mode!
        stage_estimate=SalesStageEstimate(
            current="Discovery",
            confidence=StateConfidence(value=0.9, method="crm_sync")
        ),
        psychology=CustomerPsychology(confidence=StateConfidence(value=0.5, method="init")),
        external_context=ExternalContext(
            crm_opportunity_id="opp_sf_12345",
            crm_stage_mapped="Prospecting",
            participants=["John Doe (Lead)"]
        )
    )
    
    # 2. Initialize the AI Employee
    sdr = SDRAgent()
    
    # 3. Simulate Interaction
    user_input = "Hi Alex, this sounds interesting. Can you send me some info by email?"
    print(f"🗣️  Lead says: \"{user_input}\"")
    
    # 4. Agent Thinks & Decides
    print("\n🧠 AI SDR Thinking...")
    decision = await sdr.generate_next_step(user_input, blackboard)
    print(f"   Thought: {decision['thought']}")
    print(f"   Planned Response: \"{decision['response_text']}\"")
    print(f"   Planned Action: {decision['action']['type']}")
    
    # 5. Agent Executes Action
    print("\n⚡ AI SDR Executing...")
    await sdr.execute_action(decision['action'], blackboard)
    
    # 6. Verify Result in Blackboard
    print("\n📋 Blackboard Audit Log:")
    for action in blackboard.pending_actions:
        print(f"   - [Status: {action.status}] Action: {action.action_type} | Payload: {action.payload}")
        
    print("\n✅ Demo Complete: The system successfully acted as an Autonomous SDR.")

if __name__ == "__main__":
    asyncio.run(run_demo())
