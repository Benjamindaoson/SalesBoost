#!/usr/bin/env python3
"""
Quick verification of state recovery system
"""

import asyncio
import uuid
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def quick_test():
    """Quick test of core functionality"""
    print("Quick State Recovery Verification")

    try:
        # Test import
        from cognitive.brain.state.snapshot import simple_state_snapshot_service

        print("✓ Import successful")

        # Test initialization
        await simple_state_snapshot_service.initialize()
        print("✓ Initialization successful")

        # Test snapshot creation
        session_id = f"quick_test_{uuid.uuid4().hex[:8]}"
        snapshot_id = await simple_state_snapshot_service.create_snapshot(
            session_id=session_id,
            user_id="test_user",
            agent_type="test",
            current_stage="test_stage",
            context={"test": "data"},
            memory={},
            conversation_history=[],
            execution_state={},
            ttl_hours=1,
        )
        print(f"✓ Snapshot created: {snapshot_id[:8]}...")

        # Test snapshot retrieval
        snapshot = await simple_state_snapshot_service.get_snapshot(session_id)
        if snapshot:
            print("✓ Snapshot retrieved successfully")
        else:
            print("✗ Snapshot retrieval failed")
            return False

        # Test cleanup
        await simple_state_snapshot_service.delete_snapshot(session_id)
        print("✓ Snapshot deleted successfully")

        # Test stats
        stats = simple_state_snapshot_service.get_stats()
        print(f"✓ Service stats: {stats}")

        # Stop service
        await simple_state_snapshot_service.stop()
        print("✓ Service stopped successfully")

        print("\n🎉 State recovery system is working!")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(quick_test())
