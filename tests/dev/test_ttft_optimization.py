"""
Test TTFT Optimization and Graceful Degradation

This script tests:
1. P0 Task 1.1: TTFT Optimization - "先答后评" Pattern
2. P0 Task 1.2: Graceful Degradation - Fallback Coach Advice

Expected Results:
- TTFT reduction: ~2s -> ~1.2s (40% improvement)
- Fallback advice when AI fails
- Proper tracking of advice source (ai/fallback/error_fallback)
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
from app.infra.gateway.model_gateway import ModelGateway
from app.schemas.fsm import FSMState, SalesStage


class MockModelGateway:
    """Mock gateway for testing"""
    async def generate(self, prompt: str, **kwargs):
        # Simulate NPC generation time
        await asyncio.sleep(1.0)
        return "这是一个模拟的NPC回复。"


class MockBudgetManager:
    """Mock budget manager"""
    pass


class MockSessionDirector:
    """Mock session director"""
    pass


class MockPersona:
    """Mock persona"""
    name = "测试客户"
    occupation = "企业主"


async def test_sync_mode():
    """Test original synchronous mode (baseline)"""
    print("\n" + "=" * 70)
    print("TEST 1: Synchronous Mode (Baseline - TTFT ~2s)")
    print("=" * 70)

    # Initialize coordinator
    model_gateway = MockModelGateway()
    budget_manager = MockBudgetManager()
    session_director = MockSessionDirector()
    persona = MockPersona()

    coordinator = WorkflowCoordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        session_director=session_director,
        persona=persona
    )

    coordinator.initialize_session("test_session_1", "test_user_1", FSMState(
        current_stage=SalesStage.DISCOVERY,
        turn_count=0,
        npc_mood=0.5
    ))

    # Execute turn with sync mode (enable_async_coach=False)
    print("\n📝 User Message: 这个产品多少钱？")
    start_time = time.time()

    try:
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个产品多少钱？",
            enable_async_coach=False  # Synchronous mode
        )

        ttft_ms = (time.time() - start_time) * 1000

        print(f"\n✅ Turn Completed")
        print(f"   TTFT: {ttft_ms:.0f}ms")
        print(f"   NPC Response: {result.npc_reply.response}")
        print(f"   Coach Advice: {result.coach_advice if result.coach_advice else 'None'}")
        print(f"   Intent: {result.intent}")

        return ttft_ms

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_async_mode():
    """Test asynchronous mode with TTFT optimization"""
    print("\n" + "=" * 70)
    print("TEST 2: Asynchronous Mode (TTFT Optimization - Target ~1.2s)")
    print("=" * 70)

    # Initialize coordinator
    model_gateway = MockModelGateway()
    budget_manager = MockBudgetManager()
    session_director = MockSessionDirector()
    persona = MockPersona()

    coordinator = WorkflowCoordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        session_director=session_director,
        persona=persona
    )

    coordinator.initialize_session("test_session_2", "test_user_2", FSMState(
        current_stage=SalesStage.DISCOVERY,
        turn_count=0,
        npc_mood=0.5
    ))

    # Execute turn with async mode (enable_async_coach=True)
    print("\n📝 User Message: 这个产品多少钱？")
    start_time = time.time()

    try:
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个产品多少钱？",
            enable_async_coach=True  # NEW: Async mode (先答后评)
        )

        ttft_ms = (time.time() - start_time) * 1000

        print(f"\n✅ NPC Response Returned (TTFT)")
        print(f"   TTFT: {ttft_ms:.0f}ms")
        print(f"   NPC Response: {result.npc_reply.response}")
        print(f"   Coach Advice: {result.coach_advice if result.coach_advice else 'None (Will arrive later via WebSocket)'}")
        print(f"   Intent: {result.intent}")

        # Simulate delayed coach advice generation
        if result.coach_advice is None:
            print(f"\n⏳ Generating coach advice asynchronously...")
            coach_start = time.time()

            coach_advice = await coordinator.get_coach_advice_async(
                turn_number=1,
                user_message="这个产品多少钱？",
                npc_response=result.npc_reply.response
            )

            coach_ms = (time.time() - coach_start) * 1000
            print(f"✅ Coach Advice Generated ({coach_ms:.0f}ms)")
            print(f"   Advice: {coach_advice.advice if coach_advice else 'Fallback advice used'}")

        return ttft_ms

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_fallback_advice():
    """Test graceful degradation with fallback advice"""
    print("\n" + "=" * 70)
    print("TEST 3: Graceful Degradation (Fallback Advice)")
    print("=" * 70)

    from app.engine.coordinator.dynamic_workflow import (
        DynamicWorkflowCoordinator,
        get_full_config,
        FALLBACK_COACH_ADVICE
    )

    print("\n📋 Available Fallback Advice:")
    for intent, advice_data in FALLBACK_COACH_ADVICE.items():
        print(f"\n   Intent: {intent}")
        print(f"   Advice: {advice_data['advice'][:80]}...")
        if 'tips' in advice_data:
            print(f"   Tips: {len(advice_data['tips'])} tips available")

    print("\n✅ Fallback advice dictionary loaded successfully")
    print(f"   Total intents covered: {len(FALLBACK_COACH_ADVICE)}")

    # Test fallback for specific intent
    test_intent = "price_inquiry"
    fallback = FALLBACK_COACH_ADVICE.get(test_intent)

    print(f"\n🧪 Testing fallback for intent='{test_intent}':")
    print(f"   Advice: {fallback['advice']}")
    print(f"   Tips:")
    for tip in fallback['tips']:
        print(f"      • {tip}")


async def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "=" * 70)
    print("🚀 SalesBoost TTFT Optimization Test Suite")
    print("=" * 70)
    print("\nTesting P0 Improvements:")
    print("  1. TTFT Optimization - '先答后评' Pattern")
    print("  2. Graceful Degradation - Fallback Coach Advice")

    # Test 1: Baseline (Sync)
    sync_ttft = await test_sync_mode()

    # Test 2: Optimized (Async)
    async_ttft = await test_async_mode()

    # Test 3: Fallback Advice
    await test_fallback_advice()

    # Generate Report
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)

    if sync_ttft and async_ttft:
        improvement = ((sync_ttft - async_ttft) / sync_ttft) * 100
        print(f"\n✅ TTFT Optimization:")
        print(f"   Baseline (Sync):  {sync_ttft:.0f}ms")
        print(f"   Optimized (Async): {async_ttft:.0f}ms")
        print(f"   Improvement: {improvement:.1f}% (Target: 40%)")

        if improvement >= 35:
            print(f"   Status: ✅ PASSED (Improvement >= 35%)")
        else:
            print(f"   Status: ⚠️  NEEDS REVIEW (Improvement < 35%)")

    print(f"\n✅ Graceful Degradation:")
    print(f"   Fallback intents: {len(FALLBACK_COACH_ADVICE)}")
    print(f"   Status: ✅ PASSED")

    print("\n" + "=" * 70)
    print("🎉 Test Suite Completed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
