import sys
import os
import asyncio
import logging
import json
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.context_manager.engine import ContextManagerEngine
from app.context_manager.memory import ContextMemoryStore
from app.context_manager.state_sync import SalesStateStream
from app.infra.llm.adapters import AdapterFactory, LLMAdapter
import core.redis  # Import core.redis to patch _redis_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_persistence():
    # Force InMemoryCache for testing environment without Redis
    logger.info("Forcing InMemoryCache for testing...")
    core.redis._redis_client = core.redis.InMemoryCache()

    # Setup Mock Adapter
    mock_adapter = AsyncMock(spec=LLMAdapter)
    
    async def mock_chat(messages, config):
        # Flatten messages to string to check content
        content = str(messages)
        
        # Check for Scoring Prompt keywords (matching prompts.py SCORING_PROMPT_TEMPLATE)
        if "Context Importance Scoring" in content or "sales_stage_relevance" in content:
            return json.dumps({
                "sales_stage_relevance": 0.8,
                "decision_payload": 0.7,
                "compliance_risk": 0.0,
                "champion_reusability": 0.6,
                "novelty": 0.5,
                "timeliness": 0.8,
                "final_score": 0.74,
                "persistent": True,
                "reasoning": "High importance due to budget objection which is critical for decision making."
            })
        
        # Check for Compression Prompt keywords (matching prompts.py COMPRESSION_PROMPT_TEMPLATE)
        if "Dual-Channel Compression" in content or "Structured Capability Facts" in content:
            return json.dumps({
                "structured_facts": {
                    "current_stage": "Discovery",
                    "client_profile": {"role": "Team Lead", "concern": "Budget"},
                    "objection_state": {"price": "Concerned"},
                    "compliance_log": [],
                    "next_best_action": "Address budget concern with ROI"
                },
                "narrative_summary": "User expressed budget concerns. NPC countered with ROI argument.",
                "compliance_hit": False
            })
            
        return "{}"

    mock_adapter.chat.side_effect = mock_chat
    
    # Patch AdapterFactory to return our mock
    original_get_adapter = AdapterFactory.get_adapter
    AdapterFactory.get_adapter = MagicMock(return_value=mock_adapter)

    try:
        engine = ContextManagerEngine()
        session_id = "test_session_001"
        user_id = "test_user_001"
        tenant_id = "test_tenant_001"
        
        # Simulate a turn
        logger.info("Processing turn...")
        await engine.process_turn(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            turn_id=1,
            current_stage="Discovery",
            previous_stage="Opening",
            user_input="I am worried about the price being too high for my small team.",
            npc_response="I understand budget is a concern. However, our solution pays for itself in 3 months."
        )
        
        logger.info("Turn processed.")
        
        # Verify Redis Persistence
        memory = ContextMemoryStore()
        
        # Check s1 (Summary)
        logger.info(f"Checking s1 (Summary) for {session_id}...")
        s1_data = await memory.read_json(f"ctx:s1:{session_id}")
        if s1_data:
            logger.info("✅ s1 found!")
            logger.info(f"s1 Content: {json.dumps(s1_data, indent=2, ensure_ascii=False)}")
        else:
            logger.error("❌ s1 NOT found!")

        # Check s2 (Profile)
        logger.info(f"Checking s2 (Profile) for {user_id}...")
        s2_data = await memory.read_json(f"ctx:s2:{user_id}")
        if s2_data:
            logger.info("✅ s2 found!")
            logger.info(f"s2 Content: {json.dumps(s2_data, indent=2, ensure_ascii=False)}")
        else:
            logger.warning("⚠️ s2 NOT found (Check if model extracted profile info).")

        # Check SalesState via Stream
        stream = SalesStateStream()
        latest_state = await stream.get_latest(session_id)
        if latest_state:
            logger.info("✅ SalesState found in Redis!")
            logger.info(f"SalesState Content: {json.dumps(latest_state, indent=2, ensure_ascii=False)}")
            
            # Check Agent Flags
            flags = latest_state.get("agent_flags", {})
            if "compliance_block" in flags:
                logger.info(f"✅ agent_flags.compliance_block verified: {flags['compliance_block']}")
        else:
            logger.error("❌ SalesState NOT found in Redis!")

        blackboard_key = f"blackboard:{session_id}"
        raw_blackboard = getattr(core.redis._redis_client, "_store", {}).get(blackboard_key)
        if raw_blackboard:
            logger.info("✅ Blackboard found in Redis!")
            logger.info(f"Blackboard Content: {json.dumps(json.loads(raw_blackboard), indent=2, ensure_ascii=False)}")
        else:
            logger.error("❌ Blackboard NOT found in Redis!")
            
    finally:
        # Restore original method
        AdapterFactory.get_adapter = original_get_adapter


async def test_director_trace():
    logger.info("Forcing InMemoryCache for director test...")
    core.redis._redis_client = core.redis.InMemoryCache()

    from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
    from app.schemas.blackboard import StateConfidence
    from datetime import datetime

    class Persona:
        description = "Test persona"
        objections = ["price"]

    coordinator = WorkflowCoordinator(
        model_gateway=None,
        budget_manager=None,
        session_director=None,
        persona=Persona(),
        max_history_len=10,
    )
    coordinator.initialize_session("director_session_001", "director_user_001", state=None)  # state unused in current impl

    bb = await coordinator.librarian.get_blackboard("director_session_001", "director_user_001")
    bb.psychology.trust = 0.2
    bb.psychology.resistance = 0.05
    bb.psychology.interest = 0.3
    bb.psychology.confidence = StateConfidence(value=0.9, method="test_seed", last_updated=datetime.utcnow())
    await coordinator.librarian.save_blackboard(bb)

    logger.info("Executing director turn...")
    result = await coordinator.execute_turn(1, "这个方案太贵了，有没有更便宜的？")
    logger.info(f"Director turn ok. Coach payload: {result.coach_advice}")

    blackboard_key = "blackboard:director_session_001"
    raw_blackboard = getattr(core.redis._redis_client, "_store", {}).get(blackboard_key)
    if not raw_blackboard:
        logger.error("❌ Blackboard NOT found after director turn!")
        return

    bb = json.loads(raw_blackboard)
    trace = (bb.get("history") or [])[-1]
    tool_calls = trace.get("tool_calls") or []
    if trace.get("caller_role") != "session_director":
        logger.error(f"❌ caller_role missing/incorrect: {trace.get('caller_role')}")
    else:
        logger.info("✅ caller_role propagated into DecisionTrace")

    if not tool_calls:
        logger.error("❌ tool_calls missing in DecisionTrace")
    else:
        ok_fields = all(("tool_call_id" in tc and "caller_role" in tc) for tc in tool_calls)
        if ok_fields:
            logger.info("✅ tool_call_id/caller_role propagated into tool_calls audit list")
        else:
            logger.error(f"❌ tool_calls missing required fields: {tool_calls}")

    if not bb.get("active_evidence"):
        logger.error("❌ active_evidence missing after director decision")
    else:
        logger.info("✅ active_evidence present after director decision")

    selected_id = (bb.get("selected_strategy") or {}).get("strategy_id")
    if selected_id != "probe_constraints":
        logger.error(f"❌ selected_strategy_id unexpected: {selected_id}")
    else:
        logger.info("✅ strategy arbitration respected Blackboard state (probe_constraints)")

    sanity = result.coach_advice.get("final_sanity") if isinstance(result.coach_advice, dict) else None
    if not sanity or not sanity.get("ok"):
        logger.error(f"❌ final_sanity failed: {sanity}")
    else:
        logger.info("✅ final_sanity passed (strategy/evidence/compliance all satisfied)")

if __name__ == "__main__":
    asyncio.run(test_persistence())
    asyncio.run(test_director_trace())
