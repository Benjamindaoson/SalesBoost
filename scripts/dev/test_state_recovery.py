#!/usr/bin/env python3
"""
Test script for State Recovery System
测试状态恢复系统功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_state_snapshot():
    """测试状态快照功能"""
    print("Testing State Snapshot Service...")

    try:
        from cognitive.brain.state.snapshot import state_snapshot_service

        await state_snapshot_service.initialize()

        # 创建测试快照
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
        
        # 获取快照
        snapshot = await state_snapshot_service.get_snapshot(session_id)
        if snapshot:
            print(f"Snapshot retrieved: {snapshot.snapshot_id}")
            print(f"   - Session ID: {snapshot.session_id}")
            print(f"   - User ID: {snapshot.user_id}")
            print(f"   - Current Stage: {snapshot.current_stage}")
            print(f"   - Created At: {snapshot.created_at}")
        else:
            print("Failed to retrieve snapshot")
            return False
        
        # 清理测试数据
        await state_snapshot_service.delete_snapshot(session_id)
        print("Snapshot deleted successfully")

        return True

    except Exception as e:
        print(f"State snapshot test failed: {e}")
        return False


async def test_state_recovery():
    """测试状态恢复功能"""
    print("\n🧪 Testing State Recovery Service...")

    try:
        from cognitive.brain.state.recovery import state_recovery_service

        await state_recovery_service.initialize()

        # 创建测试数据
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # 模拟创建快照
        from cognitive.brain.state.snapshot import state_snapshot_service

        snapshot_id = await state_snapshot_service.create_snapshot(
            session_id=session_id,
            user_id=user_id,
            agent_type="session_orchestrator",
            current_stage="greeting",
            context={"customer_name": "Test Customer"},
            memory={"previous_interactions": 3},
            conversation_history=[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}],
            execution_state={"current_step": "processing"},
        )

        print(f"✅ Test snapshot created: {snapshot_id}")

        # 测试恢复
        recovery_info = await state_recovery_service.recover_session_state(session_id, user_id)

        if recovery_info:
            print("✅ Session recovered successfully")
            print(f"   - Session ID: {recovery_info['session_id']}")
            print(f"   - Agent Type: {recovery_info['agent_type']}")
            print(f"   - Current Stage: {recovery_info['current_stage']}")
            print(f"   - Context Keys: {list(recovery_info['context'].keys())}")
            print(f"   - Conversation Length: {len(recovery_info['conversation_history'])}")
        else:
            print("❌ Failed to recover session")
            return False

        # 测试列出可恢复会话
        sessions = await state_recovery_service.list_recoverable_sessions(user_id)
        print(f"✅ Found {len(sessions)} recoverable sessions")

        # 清理测试数据
        await state_snapshot_service.state_snapshot_service.delete_snapshot(session_id)
        print("✅ Test data cleaned up")

        return True

    except Exception as e:
        print(f"❌ State recovery test failed: {e}")
        return False


async def test_background_tasks():
    """测试后台任务功能"""
    print("\n🧪 Testing Background Tasks...")

    try:
        from cognitive.brain.coordinator.task_executor import background_task_manager

        # 启动后台任务
        await background_task_manager.start()
        print("✅ Background tasks started")

        # 检查任务状态
        status = background_task_manager.get_task_status()
        print(f"✅ Background tasks status: {status}")

        # 等待一小段时间让任务运行
        await asyncio.sleep(2)

        # 停止后台任务
        await background_task_manager.stop()
        print("✅ Background tasks stopped")

        return True

    except Exception as e:
        print(f"❌ Background tasks test failed: {e}")
        return False


async def test_websocket_integration():
    """测试WebSocket集成"""
    print("\n🧪 Testing WebSocket Integration...")

    try:
        from api.endpoints.websocket import manager

        # 测试连接管理器
        print("✅ Connection manager initialized")
        print(f"   - Recovery enabled: {manager.recovery_enabled}")

        return True

    except Exception as e:
        print(f"❌ WebSocket integration test failed: {e}")
        return False


async def test_integration():
    """集成测试"""
    print("\n🧪 Running Integration Test...")

    try:
        # 测试完整的状态恢复流程
        session_id = f"integration_test_{uuid.uuid4().hex[:8]}"
        user_id = f"integration_user_{uuid.uuid4().hex[:8]}"

        # 1. 创建快照
        from cognitive.brain.state.snapshot import state_snapshot_service

        await state_snapshot_service.initialize()

        snapshot_id = await state_snapshot_service.create_snapshot(
            session_id=session_id,
            user_id=user_id,
            agent_type="v3_orchestrator",
            current_stage="product_introduction",
            context={"product": "SalesBoost AI", "customer_interest": "cost_optimization"},
            memory={"interaction_count": 5, "customer_mood": "interested"},
            conversation_history=[
                {"role": "user", "content": "Tell me about cost optimization"},
                {"role": "assistant", "content": "Our AI system can reduce costs by 90%+"},
            ],
            execution_state={"last_action": "cost_explanation", "next_action": "demo_request"},
        )

        print(f"✅ Integration snapshot created: {snapshot_id}")

        # 2. 测试恢复
        from cognitive.brain.state.recovery import state_recovery_service

        await state_recovery_service.initialize()

        recovery_info = await state_recovery_service.recover_session_state(session_id, user_id)

        if recovery_info and recovery_info["context"]["product"] == "SalesBoost AI":
            print("✅ Integration test passed: State recovered correctly")
        else:
            print("❌ Integration test failed: State recovery incorrect")
            return False

        # 3. 清理
        await state_snapshot_service.delete_snapshot(session_id)
        print("✅ Integration test cleaned up")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def main():
    """运行所有测试"""
    print("State Recovery System Test Suite\n")

    tests = [
        ("State Snapshot", test_state_snapshot),
        ("State Recovery", test_state_recovery),
        ("Background Tasks", test_background_tasks),
        ("WebSocket Integration", test_websocket_integration),
        ("Integration Test", test_integration),
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
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # 输出结果
    print(f"\n{'=' * 50}")
    print("TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! State recovery system is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
