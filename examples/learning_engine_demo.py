#!/usr/bin/env python3
"""
MCP Learning Engine演示

展示MCP学习引擎如何从执行历史中学习，持续优化系统性能。

核心功能：
1. 工具性能追踪
2. 工具组合效果分析
3. 上下文-工具映射学习
4. 智能工具推荐
5. 成本-质量预测

运行要求：
- Redis运行在localhost:6379
- Python 3.9+

Usage:
    python examples/learning_engine_demo.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.integration.mcp_a2a_integrated import create_integrated_system
from app.agents.autonomous.sdr_agent_integrated import SDRAgentIntegrated

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_learning_from_executions():
    """演示从执行中学习"""
    logger.info("=" * 70)
    logger.info("DEMO 1: 从执行历史中学习")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建SDR Agent
    sdr = SDRAgentIntegrated(
        agent_id="sdr_learning_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
        learning_engine=system.learning_engine,
    )
    await sdr.initialize()

    logger.info("✓ Agent已就绪")

    # 执行多次研究，让系统学习
    logger.info("\n--- 执行多次客户研究（让系统学习）---")

    customers = [
        ("Acme Corp", {"industry": "SaaS", "tier": "enterprise"}),
        ("TechStart Inc", {"industry": "SaaS", "tier": "startup"}),
        ("Finance Co", {"industry": "Finance", "tier": "enterprise"}),
        ("Retail Plus", {"industry": "Retail", "tier": "growth"}),
        ("Cloud Systems", {"industry": "SaaS", "tier": "enterprise"}),
    ]

    for i, (customer_name, context) in enumerate(customers, 1):
        logger.info(f"\n[执行 {i}/5] 研究: {customer_name}")

        result = await sdr.research_and_strategize(customer_name)

        if result["success"]:
            logger.info(
                f"  ✓ 完成 - 成本: ${result['metrics']['cost']:.3f}, "
                f"耗时: {result['metrics']['latency']:.2f}s"
            )
        else:
            logger.info(f"  ✗ 失败")

        await asyncio.sleep(0.3)

    # 获取学习报告
    logger.info("\n--- 学习报告 ---")
    learning_report = system.learning_engine.get_performance_report()

    logger.info(f"\n总执行次数: {learning_report['total_executions']}")
    logger.info(f"追踪的工具数: {learning_report['tools_tracked']}")
    logger.info(f"追踪的组合数: {learning_report['combinations_tracked']}")

    logger.info(f"\n工具性能:")
    for tool_name, perf in learning_report["tool_performance"].items():
        logger.info(f"  {tool_name}:")
        logger.info(f"    调用次数: {perf['calls']}")
        logger.info(f"    成功率: {perf['success_rate']:.1%}")
        logger.info(f"    平均延迟: {perf['avg_latency']:.2f}s")
        logger.info(f"    平均成本: ${perf['avg_cost']:.3f}")
        logger.info(f"    平均质量: {perf['avg_quality']:.2f}")

    if learning_report["best_combinations"]:
        logger.info(f"\n最佳工具组合:")
        for combo in learning_report["best_combinations"][:3]:
            logger.info(f"  {' + '.join(combo['tools'])}:")
            logger.info(f"    执行次数: {combo['executions']}")
            logger.info(f"    成功率: {combo['success_rate']:.1%}")
            logger.info(f"    平均质量: {combo['avg_quality']:.2f}")

    # 清理
    await sdr.shutdown()
    await system.shutdown()


async def demo_intelligent_recommendations():
    """演示智能工具推荐"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 2: 智能工具推荐")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建SDR Agent
    sdr = SDRAgentIntegrated(
        agent_id="sdr_recommend_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
        learning_engine=system.learning_engine,
    )
    await sdr.initialize()

    # 先执行一些操作让系统学习
    logger.info("\n--- 训练阶段：执行多次操作 ---")
    for i in range(10):
        await sdr.research_and_strategize(f"Customer_{i}")
        if i % 3 == 0:
            logger.info(f"  已完成 {i+1}/10 次训练")

    logger.info("✓ 训练完成")

    # 获取推荐
    logger.info("\n--- 获取智能推荐 ---")

    scenarios = [
        {
            "intent": "research enterprise SaaS customer",
            "context": {"industry": "SaaS", "tier": "enterprise"},
            "description": "Enterprise SaaS客户研究",
        },
        {
            "intent": "qualify startup lead",
            "context": {"industry": "SaaS", "tier": "startup"},
            "description": "Startup线索资格审查",
        },
        {
            "intent": "handle price objection",
            "context": {"stage": "objection", "objection_type": "price"},
            "description": "处理价格异议",
        },
    ]

    for scenario in scenarios:
        logger.info(f"\n场景: {scenario['description']}")
        logger.info(f"  意图: {scenario['intent']}")
        logger.info(f"  上下文: {scenario['context']}")

        # 获取推荐
        recommendations = system.learning_engine.recommend_tools(
            intent=scenario["intent"],
            context=scenario["context"],
            top_k=3,
        )

        logger.info(f"\n  推荐工具:")
        for tool_name, score in recommendations:
            logger.info(f"    {tool_name}: {score:.3f}")

        # 获取组合推荐
        combination = system.learning_engine.recommend_tool_combination(
            intent=scenario["intent"],
            context=scenario["context"],
        )

        if combination:
            logger.info(f"\n  推荐组合: {' + '.join(combination)}")

            # 预测成本和质量
            predicted_cost = system.learning_engine.predict_cost(
                tools=combination,
                context=scenario["context"],
            )
            predicted_quality = system.learning_engine.predict_quality(
                tools=combination,
                context=scenario["context"],
            )

            logger.info(f"  预测成本: ${predicted_cost:.3f}")
            logger.info(f"  预测质量: {predicted_quality:.2f}")

    # 清理
    await sdr.shutdown()
    await system.shutdown()


async def demo_cost_quality_optimization():
    """演示成本-质量优化"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 3: 成本-质量优化")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建SDR Agent
    sdr = SDRAgentIntegrated(
        agent_id="sdr_optimize_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
        learning_engine=system.learning_engine,
    )
    await sdr.initialize()

    # 训练
    logger.info("\n--- 训练阶段 ---")
    for i in range(15):
        await sdr.research_and_strategize(f"Customer_{i}")

    logger.info("✓ 训练完成")

    # 测试不同约束下的推荐
    logger.info("\n--- 测试不同约束 ---")

    test_cases = [
        {
            "name": "无约束",
            "max_cost": None,
            "min_quality": None,
        },
        {
            "name": "低成本优先",
            "max_cost": 0.10,
            "min_quality": None,
        },
        {
            "name": "高质量优先",
            "max_cost": None,
            "min_quality": 0.8,
        },
        {
            "name": "平衡模式",
            "max_cost": 0.20,
            "min_quality": 0.7,
        },
    ]

    context = {"industry": "SaaS", "tier": "enterprise"}

    for test_case in test_cases:
        logger.info(f"\n{test_case['name']}:")
        if test_case["max_cost"]:
            logger.info(f"  最大成本: ${test_case['max_cost']:.2f}")
        if test_case["min_quality"]:
            logger.info(f"  最小质量: {test_case['min_quality']:.2f}")

        recommendations = system.learning_engine.recommend_tools(
            intent="research customer",
            context=context,
            max_cost=test_case["max_cost"],
            min_quality=test_case["min_quality"],
            top_k=3,
        )

        if recommendations:
            logger.info(f"  推荐:")
            for tool_name, score in recommendations:
                # 获取工具指标
                if tool_name in system.learning_engine.tool_metrics:
                    metrics = system.learning_engine.tool_metrics[tool_name]
                    logger.info(
                        f"    {tool_name}: score={score:.3f}, "
                        f"cost=${metrics.avg_cost:.3f}, "
                        f"quality={metrics.avg_quality:.2f}"
                    )
        else:
            logger.info(f"  ⚠️ 没有满足约束的工具")

    # 清理
    await sdr.shutdown()
    await system.shutdown()


async def demo_knowledge_persistence():
    """演示知识持久化"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 4: 知识持久化")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建SDR Agent
    sdr = SDRAgentIntegrated(
        agent_id="sdr_persist_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
        learning_engine=system.learning_engine,
    )
    await sdr.initialize()

    # 训练
    logger.info("\n--- 训练阶段 ---")
    for i in range(20):
        await sdr.research_and_strategize(f"Customer_{i}")
        if (i + 1) % 5 == 0:
            logger.info(f"  已完成 {i+1}/20 次训练")

    logger.info("✓ 训练完成")

    # 导出知识
    logger.info("\n--- 导出学习到的知识 ---")
    knowledge_file = project_root / "data" / "mcp_learned_knowledge.json"
    knowledge_file.parent.mkdir(parents=True, exist_ok=True)

    system.learning_engine.export_knowledge(str(knowledge_file))
    logger.info(f"✓ 知识已导出到: {knowledge_file}")

    # 获取当前性能报告
    report_before = system.learning_engine.get_performance_report()
    logger.info(f"\n导出前统计:")
    logger.info(f"  总执行次数: {report_before['total_executions']}")
    logger.info(f"  追踪的工具数: {report_before['tools_tracked']}")

    # 创建新系统并导入知识
    logger.info("\n--- 创建新系统并导入知识 ---")
    await sdr.shutdown()
    await system.shutdown()

    # 新系统
    system2 = await create_integrated_system()
    logger.info("✓ 新系统已创建")

    # 导入知识
    system2.learning_engine.import_knowledge(str(knowledge_file))
    logger.info("✓ 知识已导入")

    # 验证
    report_after = system2.learning_engine.get_performance_report()
    logger.info(f"\n导入后统计:")
    logger.info(f"  追踪的工具数: {report_after['tools_tracked']}")
    logger.info(f"  学习的模式数: {report_after['learned_patterns']['context_patterns']}")

    logger.info("\n✓ 知识成功迁移到新系统!")

    # 清理
    await system2.shutdown()


async def main():
    """运行所有演示"""
    try:
        logger.info("\n" + "=" * 70)
        logger.info("MCP Learning Engine 完整演示")
        logger.info("=" * 70)
        logger.info("\n展示MCP学习引擎如何从执行中学习并持续优化\n")

        # 运行演示
        await demo_learning_from_executions()
        await demo_intelligent_recommendations()
        await demo_cost_quality_optimization()
        await demo_knowledge_persistence()

        logger.info("\n" + "=" * 70)
        logger.info("所有演示完成! 🎉")
        logger.info("=" * 70)

        logger.info("\n核心能力:")
        logger.info("  ✓ 工具性能追踪 - 记录每次执行的指标")
        logger.info("  ✓ 智能推荐 - 基于历史数据推荐最佳工具")
        logger.info("  ✓ 组合优化 - 发现工具协同效应")
        logger.info("  ✓ 成本-质量权衡 - 在约束下优化选择")
        logger.info("  ✓ 上下文学习 - 学习哪些工具适合哪些场景")
        logger.info("  ✓ 知识持久化 - 导出/导入学习到的知识")

        logger.info("\n这是真正的自学习MCP系统! 🚀")
        logger.info("系统会从每次使用中学习，持续自我优化!")

    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
