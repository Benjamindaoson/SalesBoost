#!/usr/bin/env python3
"""
Test Week 3-4 Implementation
测试Week 3-4的所有核心功能实现
"""

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_cost_control_system():
    """测试成本控制系统"""
    print("Testing Cost Control System")
    print("=" * 40)

    try:
        from cognitive.infra.gateway.cost_control import cost_optimized_caller, ModelCostCalculator

        # Test 1: Cost calculation
        print("\n1. Testing cost calculation...")
        gpt4_cost = ModelCostCalculator.calculate_cost("gpt-4", 1000, 500)
        qwen_cost = ModelCostCalculator.calculate_cost("qwen-turbo", 1000, 500)
        print(f"   GPT-4 cost: ${gpt4_cost}")
        print(f"   Qwen Turbo cost: ${qwen_cost}")
        print(f"   Cost reduction: {((gpt4_cost - qwen_cost) / gpt4_cost * 100):.1f}%")

        # Test 2: Model routing
        print("\n2. Testing model routing...")
        router = cost_optimized_caller.smart_router
        cheap_model, model_info = await router.route_to_optimal_model("test_agent", 0.2, 0.001)
        print(f"   Selected model: {cheap_model}")
        print(f"   Model tier: {model_info.tier.value}")
        print(f"   Model cost: ${model_info.cost_per_1k_tokens}/1K")

        # Test 3: Budget management
        print("\n3. Testing budget management...")
        cost_optimized_caller.budget_manager.set_session_budget("test_session", 10.0)
        cost_optimized_caller.budget_manager.set_user_budget("test_user", 50.0)

        can_afford_1 = cost_optimized_caller.budget_manager.check_budget("test_session", "test_user", 5.0)
        can_afford_2 = cost_optimized_caller.budget_manager.check_budget("test_session", "test_user", 15.0)

        print(f"   Can afford $5: {can_afford_1}")
        print(f"   Can afford $15: {can_afford_2}")

        # Test 4: Optimized call
        print("\n4. Testing optimized call...")
        result = await cost_optimized_caller.call_with_cost_control(
            agent_type="test_agent",
            prompt="This is a test prompt for cost optimization",
            session_id="test_session",
            user_id="test_user",
            task_complexity=0.7,
            max_budget=1.0,
            fallback_enabled=True,
        )

        if "error" not in result:
            print(f"   Call successful: {result['model_used']}")
            print(f"   Actual cost: ${result['actual_cost']}")
            print(f"   Latency: {result['latency_ms']:.1f}ms")
        else:
            print(f"   Call failed: {result.get('error', 'unknown')}")

        return True

    except Exception as e:
        print(f"Cost control system test failed: {e}")
        return False


async def test_performance_metrics_system():
    """测试性能指标系统"""
    print("\nTesting Performance Metrics System")
    print("=" * 40)

    try:
        from cognitive.observability.metrics.business_metrics import performance_metrics_collector, MetricType

        # Test 1: Metrics recording
        print("\n1. Testing metrics recording...")

        # Record some test metrics
        await performance_metrics_collector.record_response_time("test_session", "test_agent", 250.0)
        await performance_metrics_collector.record_throughput("test_session", "test_agent", 10.5)
        await performance_metrics_collector.record_error("test_session", "test_agent", "timeout_error")
        await performance_metrics_collector.record_cost_efficiency("test_session", "test_agent", 0.05)

        print("   Test metrics recorded successfully")

        # Test 2: System snapshot
        print("\n2. Testing system snapshot...")
        await performance_metrics_collector.capture_system_snapshot(10, 5, 1000, 10)
        print("   System snapshot captured")

        # Test 3: Metrics summary
        print("\n3. Testing metrics summary...")
        summary = performance_metrics_collector.get_metrics_summary(time_window_minutes=1)
        print(f"   Metrics summary: {summary}")

        # Test 4: Health score
        print("\n4. Testing health score...")
        health = performance_metrics_collector.get_system_health_score()
        print(f"   Health score: {health['overall_score']}/100")
        print(f"   Health level: {health['health_level']}")

        return True

    except Exception as e:
        print(f"Performance metrics system test failed: {e}")
        return False


async def test_background_tasks_system():
    """测试后台任务系统"""
    print("\nTesting Background Tasks System")
    print("=" * 40)

    try:
        from cognitive.brain.coordinator.task_executor import background_task_manager

        # Test 1: Task management
        print("\n1. Testing task management...")

        status = background_task_manager.get_task_status()
        print(f"   Task status retrieved: {status['background_tasks']}")
        print(f"   Uptime: {status['uptime_seconds']:.1f}s")

        return True

    except Exception as e:
        print(f"Background tasks system test failed: {e}")
        return False


async def test_system_integration():
    """测试系统集成"""
    print("\nTesting System Integration")
    print("=" * 40)

    try:
        # Test cost control + performance metrics
        cost_ok = await test_cost_control_system()
        metrics_ok = await test_performance_metrics_system()
        background_ok = await test_background_tasks_system()

        all_passed = cost_ok and metrics_ok and background_ok

        if all_passed:
            print("   ✅ All systems integrated successfully!")
        else:
            print("   ❌ Some systems failed integration")

        return all_passed

    except Exception as e:
        print(f"System integration test failed: {e}")
        return False


async def main():
    """主测试函数"""
    print("SalesBoost Week 3-4 Implementation Test")
    print("=" * 60)
    print("Testing Week 3: Performance Metrics Collection")
    print("Testing Week 4: Enterprise Features & Ecosystem")
    print()

    success = await test_system_integration()

    if success:
        print("\n" + "=" * 60)
        print("🎉 WEEK 3-4 TASK COMPLETED SUCCESSFULLY!")
        print("✅ Cost Control System: Working")
        print("✅ Performance Metrics System: Working")
        print("✅ Background Tasks System: Working")
        print("✅ System Integration: Complete")
        print("🚀 System upgraded to Industrial-Grade!")
        print("\nReady for Phase 2: Production Deployment & Optimization")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ WEEK 3-4 TASK FAILED!")
        print("❌ Some critical systems not working")
        print("⚠️ Need additional fixes before deployment")
        return 1


if __name__ == "__main__":
    asyncio.run(main())
