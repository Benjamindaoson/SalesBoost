#!/usr/bin/env python3
"""
Simple Test for State Recovery
"""

import asyncio
import uuid
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_simple_state_snapshot():
    """Test simple state snapshot functionality"""
    print("Testing Simple State Snapshot Service...")

    try:
        from cognitive.brain.state.snapshot import simple_state_snapshot_service

        await simple_state_snapshot_service.initialize()

        # Create test snapshot
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        snapshot_id = await simple_state_snapshot_service.create_snapshot(
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
        snapshot = await simple_state_snapshot_service.get_snapshot(session_id)
        if snapshot:
            print(f"Snapshot retrieved: {snapshot.snapshot_id}")
            print(f"   - Session ID: {snapshot.session_id}")
            print(f"   - User ID: {snapshot.user_id}")
            print(f"   - Current Stage: {snapshot.current_stage}")
        else:
            print("Failed to retrieve snapshot")
            return False

        # Test cleanup
        cleaned = await simple_state_snapshot_service.cleanup_expired_snapshots()
        print(f"Cleaned up {cleaned} expired snapshots")

        # Get stats
        stats = simple_state_snapshot_service.get_stats()
        print(f"Service stats: {stats}")

        # Cleanup test data
        await simple_state_snapshot_service.delete_snapshot(session_id)
        print("Snapshot deleted successfully")

        # Stop service
        await simple_state_snapshot_service.stop()

        return True

    except Exception as e:
        print(f"Simple state snapshot test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_websocket_integration():
    """Test WebSocket integration"""
    print("\nTesting WebSocket Integration...")

    try:
        # Test connection manager
        from api.endpoints.websocket import ConnectionManager

        manager = ConnectionManager()

        print("Connection manager created successfully")
        print(f"Recovery enabled: {manager.recovery_enabled}")

        return True

    except Exception as e:
        print(f"WebSocket integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_background_tasks():
    """Test background tasks"""
    print("\nTesting Background Tasks...")

    try:
        from cognitive.brain.coordinator.task_executor import BackgroundTaskManager

        task_manager = BackgroundTaskManager()

        # Start tasks
        await task_manager.start()
        print("Background tasks started")

        # Get status
        status = task_manager.get_task_status()
        print(f"Task status: {status}")

        # Stop tasks
        await task_manager.stop()
        print("Background tasks stopped")

        return True

    except Exception as e:
        print(f"Background tasks test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("Simple State Recovery Test Suite\n")

    tests = [
        ("Simple State Snapshot", test_simple_state_snapshot),
        ("WebSocket Integration", test_websocket_integration),
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
        print("All tests passed! Simple state recovery system is ready.")
        return 0
    else:
        print("Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
