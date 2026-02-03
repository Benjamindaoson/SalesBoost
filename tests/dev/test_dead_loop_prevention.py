#!/usr/bin/env python3
"""
Test Dead Loop Prevention System
测试Agent死循环防护系统
"""

import asyncio
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_dead_loop_prevention():
    """测试死循环防护功能"""
    print("Testing Dead Loop Prevention System")
    print("=" * 50)

    try:
        # Import the system
        from cognitive.brain.coordinator.loop_guard import dead_loop_detector, loop_intervention_handler, LoopDetectionLevel

        # Test 1: Start execution tracking
        print("\n1. Testing execution tracking...")
        session_id = "test_session_loop"
        execution_id = await dead_loop_detector.start_execution(
            session_id=session_id,
            max_depth=10,  # Reduced for testing
            max_time_seconds=30.0,  # Reduced for testing
        )
        print(f"   Execution started: {execution_id[:8]}...")

        # Test 2: Check safe state
        print("\n2. Testing safe execution state...")
        can_continue = await dead_loop_detector.increment_depth(session_id, "test_step_1")
        if can_continue:
            print("   Safe execution - depth increment allowed")
        else:
            print("   Execution blocked at depth check")
            return False

        # Test 3: Record some states
        print("\n3. Testing state recording...")
        for i in range(3):
            state_data = {
                "agent_type": "test_agent",
                "current_stage": f"stage_{i}",
                "last_action": f"action_{i}",
                "iteration": i,
            }
            detection_level = await dead_loop_detector.record_state(session_id, state_data)
            print(f"   State {i} recorded - Detection level: {detection_level.value}")

        # Test 4: Get execution status
        print("\n4. Testing execution status...")
        status = dead_loop_detector.get_execution_status(session_id)
        if status:
            print(f"   Current status: {status['risk_level']} risk")
            print(f"   Depth: {status['current_depth']}/{status['max_depth_limit']}")
            print(f"   Time: {status['elapsed_time_seconds']:.1f}s/{status['max_time_limit']}s")
        else:
            print("   Failed to get execution status")
            return False

        # Test 5: Simulate approaching limits
        print("\n5. Testing limit approach...")
        for i in range(5, 8):
            can_continue = await dead_loop_detector.increment_depth(session_id, f"step_{i}")
            if not can_continue:
                print(f"   Execution blocked at depth {i}")
                break

            state_data = {
                "agent_type": "test_agent",
                "current_stage": "repeating_stage",  # Same stage to trigger loop detection
                "last_action": f"repeating_action_{i}",
                "iteration": i,
            }
            detection_level = await dead_loop_detector.record_state(session_id, state_data)
            print(f"   Step {i}: {detection_level.value}")

            if detection_level in [LoopDetectionLevel.CRITICAL, LoopDetectionLevel.BLOCKED]:
                print(f"   Loop detected at level: {detection_level.value}")
                break

        # Test 6: Get current execution status after loop
        print("\n6. Testing post-loop status...")
        status = dead_loop_detector.get_execution_status(session_id)
        if status and status["risk_level"] in ["MEDIUM", "HIGH"]:
            print("   Risk level properly elevated after loop detection")
        else:
            print("   Risk level not properly updated")
            return False

        # Test 7: Handle intervention
        print("\n7. Testing intervention handling...")
        current_state = dead_loop_detector.active_executions.get(session_id)
        if current_state:
            detection_level = await dead_loop_detector.check_execution_limits(session_id)
            intervention = await loop_intervention_handler.handle_intervention(
                session_id, detection_level, current_state
            )
            print(f"   Intervention result: {intervention['status']}")
            print(f"   Action taken: {intervention.get('action', 'none')}")

        # Test 8: End execution
        print("\n8. Testing execution end...")
        summary = await dead_loop_detector.end_execution(session_id)
        if "error" not in summary:
            print("   Execution ended successfully")
            print(f"   Final depth: {summary['total_depth']}")
            print(f"   Total time: {summary['execution_time_seconds']:.2f}s")
            print(f"   Loop detected: {summary['loop_detected']}")
        else:
            print("   Failed to end execution")
            return False

        # Test 9: Verify cleanup
        print("\n9. Testing cleanup verification...")
        status_after = dead_loop_detector.get_execution_status(session_id)
        if status_after is None:
            print("   Execution state properly cleaned up")
        else:
            print("   Execution state not cleaned up")
            return False

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("Dead loop prevention system is working correctly!")
        return True

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_extreme_scenarios():
    """测试极端场景"""
    print("\nTesting Extreme Scenarios")
    print("=" * 30)

    try:
        from cognitive.brain.coordinator.loop_guard import dead_loop_detector, LoopDetectionLevel

        # Test extreme depth
        print("\n1. Testing extreme depth scenario...")
        session_id = "extreme_depth_test"
        await dead_loop_detector.start_execution(session_id, max_depth=5, max_time_seconds=10)

        # Push to limit
        for i in range(10):
            can_continue = await dead_loop_detector.increment_depth(session_id, f"step_{i}")
            if not can_continue:
                print(f"   Depth limit properly enforced at step {i}")
                break

        summary = await dead_loop_detector.end_execution(session_id)
        if summary.get("max_depth_reached"):
            print("   Extreme depth test passed")
        else:
            print("   Extreme depth test failed")
            return False

        # Test time limit
        print("\n2. Testing time limit scenario...")
        session_id = "time_limit_test"
        await dead_loop_detector.start_execution(session_id, max_depth=100, max_time_seconds=2)

        # Wait a bit to trigger time limit
        await asyncio.sleep(3)

        detection_level = await dead_loop_detector.check_execution_limits(session_id)
        if detection_level == LoopDetectionLevel.BLOCKED:
            print("   Time limit properly enforced")
        else:
            print(f"   Time limit not enforced: {detection_level}")
            return False

        await dead_loop_detector.end_execution(session_id)

        return True

    except Exception as e:
        print(f"\nExtreme scenario test failed: {e}")
        return False


async def main():
    """主测试函数"""
    print("SalesBoost Dead Loop Prevention - System Test")
    print("Testing Week 2 implementation: Agent Dead Loop Prevention")
    print()

    # Core functionality test
    success = await test_dead_loop_prevention()

    if not success:
        print("\nWEEK 2 TASK FAILED!")
        print("Need to fix dead loop prevention before proceeding")
        return 1

    # Extreme scenarios test
    success = await test_extreme_scenarios()

    if success:
        print("\nWEEK 2 TASK COMPLETED SUCCESSFULLY!")
        print("Agent dead loop prevention mechanism is working!")
        print("Ready for Week 3: Performance Metrics Collection")
        return 0
    else:
        print("\nWEEK 2 EXTREME SCENARIOS FAILED!")
        print("Dead loop prevention needs improvement")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
