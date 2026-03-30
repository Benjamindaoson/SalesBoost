#!/usr/bin/env python3
"""
Test script for State Recovery System
"""

import asyncio
import uuid

# Add project root to path
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_state_snapshot():
    """Test state snapshot functionality"""
    print("Testing State Snapshot Service...")

    try:
        from cognitive.brain.state.snapshot import state_snapshot_service

        await state_snapshot_service.initialize()

        # Create test snapshot
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        snapshot_id = await state_snapshot_service.create_snapshot(
            session_id=session_id,
            user_id=user_id,
            agent_type="test_orchestrator",
            current_stage="test_stage",
            context={"test_key": "test_value"},
            memory={"memory_key": "memory_value"},
            conversation_history=[{"role": "user", "content": "test message"}],
            execution_state={"step": 1},
            ttl_hours=1,
        )

        print(f"Snapshot created: {snapshot_id}")

        # Get snapshot
        snapshot = await state_snapshot_service.get_snapshot(session_id)
        if snapshot:
            print(f"Snapshot retrieved: {snapshot.snapshot_id}")
            print(f"   - Session ID: {snapshot.session_id}")
            print(f"   - User ID: {snapshot.user_id}")
            print(f"   - Current Stage: {snapshot.current_stage}")
        else:
            print("Failed to retrieve snapshot")
            return False

        # Cleanup test data
        await state_snapshot_service.delete_snapshot(session_id)
        print("Snapshot deleted successfully")

        return True

    except Exception as e:
        print(f"State snapshot test failed: {e}")
        return False


async def test_background_tasks():
    """Test background tasks functionality"""
    print("\nTesting Background Tasks...")

    try:
        from cognitive.brain.coordinator.task_executor import background_task_manager

        # Start background tasks
        await background_task_manager.start()
        print("Background tasks started")

        # Check task status
        status = background_task_manager.get_task_status()
        print(f"Background tasks status: {status}")

        # Wait a bit for tasks to run
        await asyncio.sleep(2)

        # Stop background tasks
        await background_task_manager.stop()
        print("Background tasks stopped")

        return True

    except Exception as e:
        print(f"Background tasks test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("State Recovery System Test Suite\n")

    tests = [
        ("State Snapshot", test_state_snapshot),
        ("Background Tasks", test_background_tasks),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running {test_name} Test")
        print("=" * 50)

        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{test_name} test crashed: {e}")
            results.append((test_name, False))

    # Output results
    print(f"\n{'=' * 50}")
    print("TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! State recovery system is ready.")
        return 0
    else:
        print("Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
