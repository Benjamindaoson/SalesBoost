#!/usr/bin/env python3
"""
Direct test of state snapshot service without complex imports
"""

import asyncio
import uuid

# Direct import to avoid circular dependencies
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_state_snapshot_directly():
    """Test state snapshot directly"""
    print("Direct State Snapshot Test")

    # Import the service class directly
    from cognitive.brain.state.snapshot import SimpleStateSnapshotService

    # Create instance
    service = SimpleStateSnapshotService()

    try:
        # Initialize
        await service.initialize()
        print("✓ Service initialized")

        # Test data
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        user_id = "test_user"

        # Create snapshot
        snapshot_id = await service.create_snapshot(
            session_id=session_id,
            user_id=user_id,
            agent_type="test",
            current_stage="test_stage",
            context={"test": "data"},
            memory={"memory": "test"},
            conversation_history=[{"role": "user", "content": "hello"}],
            execution_state={"step": 1},
            ttl_hours=1,
        )
        print(f"✓ Snapshot created: {snapshot_id}")

        # Retrieve snapshot
        snapshot = await service.get_snapshot(session_id)
        if snapshot:
            print("✓ Snapshot retrieved successfully")
            print(f"  Session ID: {snapshot.session_id}")
            print(f"  User ID: {snapshot.user_id}")
            print(f"  Stage: {snapshot.current_stage}")
        else:
            print("✗ Failed to retrieve snapshot")
            return False

        # Get stats
        stats = service.get_stats()
        print(f"✓ Service stats: {stats}")

        # Cleanup
        await service.delete_snapshot(session_id)
        print("✓ Snapshot deleted")

        # Stop service
        await service.stop()
        print("✓ Service stopped")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    success = await test_state_snapshot_directly()

    if success:
        print("\nState recovery system core functionality is working!")
        return 0
    else:
        print("\nState recovery test failed")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
