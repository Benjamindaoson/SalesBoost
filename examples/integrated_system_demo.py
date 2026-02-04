#!/usr/bin/env python3
"""
完整的MCP-A2A集成演示

这是一个完全可运行的端到端示例，展示：
1. MCP 2.0和A2A多智能体系统的深度集成
2. SDR Agent使用MCP进行智能规划
3. Agent间通过A2A通信
4. 动态工具生成
5. 服务网格路由

运行要求：
- Redis运行在localhost:6379
- Python 3.9+

Usage:
    python examples/integrated_system_demo.py
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
from app.agents.roles.coach_agent_a2a import CoachAgentA2A
from app.agents.roles.compliance_agent_a2a import ComplianceAgentA2A

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_integrated_research():
    """演示集成的客户研究"""
    logger.info("=" * 70)
    logger.info("DEMO 1: 集成的智能客户研究")
    logger.info("=" * 70)

    # 创建集成系统
    logger.info("\n--- 初始化集成系统 ---")
    system = await create_integrated_system()

    # 创建SDR Agent（MCP增强）
    logger.info("\n--- 创建MCP增强的SDR Agent ---")
    sdr = SDRAgentIntegrated(
        agent_id="sdr_integrated_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
    )
    await sdr.initialize()
    logger.info("✓ SDR Agent创建完成")

    # 创建Coach Agent
    logger.info("\n--- 创建Coach Agent ---")
    coach = CoachAgentA2A(
        agent_id="coach_integrated_001",
        message_bus=system.a2a_bus,
    )
    await coach.initialize()
    logger.info("✓ Coach Agent创建完成")

    # 创建Compliance Agent
    logger.info("\n--- 创建Compliance Agent ---")
    compliance = ComplianceAgentA2A(
        agent_id="compliance_integrated_001",
        message_bus=system.a2a_bus,
    )
    await compliance.initialize()
    logger.info("✓ Compliance Agent创建完成")

    # 执行智能研究
    logger.info("\n--- 执行智能客户研究 ---")
    logger.info("客户: Acme Corp (SaaS公司)")
    logger.info("目标: 研究客户并制定个性化销售策略")

    result = await sdr.research_and_strategize("Acme Corp")

    if result["success"]:
        logger.info("\n✓ 研究完成!")
        logger.info(f"  成本: ${result['metrics']['cost']:.3f}")
        logger.info(f"  耗时: {result['metrics']['latency']:.2f}秒")
        logger.info(f"\n策略:")
        logger.info(f"  方法: {result['strategy']['approach']}")
        logger.info(f"  关键点: {', '.join(result['strategy']['key_points'])}")
        logger.info(f"  下一步: {', '.join(result['strategy']['next_steps'])}")
    else:
        logger.error(f"✗ 研究失败: {result.get('error')}")

    # 清理
    await sdr.shutdown()
    await coach.shutdown()
    await compliance.shutdown()
    await system.shutdown()


async def demo_integrated_conversation():
    """演示集成的销售对话"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 2: 集成的销售对话流程")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建Agents
    sdr = SDRAgentIntegrated(
        agent_id="sdr_conv_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
    )
    await sdr.initialize()

    coach = CoachAgentA2A(
        agent_id="coach_conv_001",
        message_bus=system.a2a_bus,
    )
    await coach.initialize()

    compliance = ComplianceAgentA2A(
        agent_id="compliance_conv_001",
        message_bus=system.a2a_bus,
    )
    await compliance.initialize()

    logger.info("✓ 所有Agent已就绪")

    # 模拟对话
    conversation = [
        {
            "customer": "Hi, I'm interested in your product",
            "context": {"industry": "SaaS", "tier": "growth", "stage": "discovery"},
        },
        {
            "customer": "What's the pricing?",
            "context": {"industry": "SaaS", "tier": "growth", "stage": "pitch"},
        },
        {
            "customer": "That seems expensive",
            "context": {"industry": "SaaS", "tier": "growth", "stage": "objection"},
        },
    ]

    logger.info("\n--- 开始销售对话 ---")

    for i, turn in enumerate(conversation, 1):
        logger.info(f"\n[Turn {i}] 客户: {turn['customer']}")

        # SDR生成响应（使用MCP能力）
        response_result = await sdr.generate_response_with_mcp({
            "customer_message": turn["customer"],
            "context": turn["context"],
        })

        if response_result["success"]:
            logger.info(f"  SDR: {response_result['response']}")

            if response_result.get("coach_suggestion"):
                logger.info(f"  💡 Coach建议: {response_result['coach_suggestion'].get('recommended_approach', 'N/A')}")

            if response_result.get("compliant"):
                logger.info(f"  ✓ Compliance: 通过")
        else:
            logger.error(f"  ✗ 响应生成失败")

        await asyncio.sleep(0.5)

    # 处理异议
    logger.info("\n--- 处理价格异议 ---")
    objection_result = await sdr.handle_objection_with_mcp({
        "objection": "That seems expensive",
        "objection_type": "price",
    })

    if objection_result["success"]:
        logger.info(f"✓ 异议处理完成")
        logger.info(f"  成本: ${objection_result['metrics']['cost']:.3f}")
        logger.info(f"  耗时: {objection_result['metrics']['latency']:.2f}秒")

    # 清理
    await sdr.shutdown()
    await coach.shutdown()
    await compliance.shutdown()
    await system.shutdown()


async def demo_dynamic_pricing():
    """演示动态定价"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 3: 动态定价工具生成")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建SDR
    sdr = SDRAgentIntegrated(
        agent_id="sdr_pricing_001",
        message_bus=system.a2a_bus,
        orchestrator=system.orchestrator,
        tool_generator=system.tool_generator,
        service_mesh=system.service_mesh,
    )
    await sdr.initialize()

    # 创建Compliance
    compliance = ComplianceAgentA2A(
        agent_id="compliance_pricing_001",
        message_bus=system.a2a_bus,
    )
    await compliance.initialize()

    logger.info("✓ Agents已就绪")

    # 关闭交易（包含动态定价）
    logger.info("\n--- 关闭交易 ---")
    logger.info("客户: Enterprise客户, Finance行业")
    logger.info("基础价格: $100/单位, 数量: 1000")

    deal_result = await sdr.close_deal_with_mcp({
        "deal_info": {
            "customer_tier": "enterprise",
            "industry": "Finance",
            "relationship_score": 0.8,
            "base_price": 100,
            "quantity": 1000,
            "value": 100000,
        }
    })

    if deal_result["success"]:
        logger.info("\n✓ 交易成功!")
        logger.info(f"  最终价格: ${deal_result['deal_value']:,.0f}")

        pricing = deal_result["pricing_details"]
        logger.info(f"\n  定价明细:")
        logger.info(f"    基础价格: ${pricing['base_price']:,.0f}")
        logger.info(f"    数量: {pricing['quantity']}")
        logger.info(f"    层级折扣: {pricing['tier_discount']:.1%}")
        logger.info(f"    批量折扣: {pricing['volume_discount']:.1%}")
        logger.info(f"    关系折扣: {pricing['relationship_discount']:.1%}")
        logger.info(f"    总折扣: {pricing['total_discount']:.1%}")
        logger.info(f"    单价: ${pricing['price_per_unit']:.2f}")

        logger.info(f"\n  下一步: {', '.join(deal_result['next_steps'])}")
    else:
        logger.error(f"✗ 交易失败: {deal_result.get('reason')}")

    # 清理
    await sdr.shutdown()
    await compliance.shutdown()
    await system.shutdown()


async def demo_system_status():
    """演示系统状态监控"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 4: 系统状态监控")
    logger.info("=" * 70)

    # 创建系统
    logger.info("\n--- 初始化系统 ---")
    system = await create_integrated_system()

    # 创建多个Agents
    agents = []
    for i in range(3):
        sdr = SDRAgentIntegrated(
            agent_id=f"sdr_status_{i:03d}",
            message_bus=system.a2a_bus,
            orchestrator=system.orchestrator,
            tool_generator=system.tool_generator,
            service_mesh=system.service_mesh,
        )
        await sdr.initialize()
        agents.append(sdr)

    logger.info(f"✓ 创建了{len(agents)}个SDR Agents")

    # 执行一些操作
    logger.info("\n--- 执行操作 ---")
    for i, agent in enumerate(agents):
        logger.info(f"Agent {i+1} 执行研究...")
        await agent.research_and_strategize(f"Customer_{i+1}")

    # 获取系统状态
    logger.info("\n--- 系统状态 ---")
    status = await system.get_system_status()

    logger.info(f"\nA2A消息总线:")
    logger.info(f"  注册Agent数: {status['a2a']['registered_agents']}")
    logger.info(f"  活跃订阅: {status['a2a']['active_subscriptions']}")

    logger.info(f"\nMCP服务网格:")
    logger.info(f"  总节点数: {status['mesh']['total_nodes']}")
    logger.info(f"  在线节点: {status['mesh']['online_nodes']}")
    logger.info(f"  总请求数: {status['mesh']['total_requests']}")
    logger.info(f"  成功率: {status['mesh']['success_rate']:.1%}")

    logger.info(f"\nMCP编排器:")
    if status['orchestrator']:
        logger.info(f"  总执行次数: {status['orchestrator']['total_executions']}")
        logger.info(f"  成功率: {status['orchestrator']['success_rate']:.1%}")
        logger.info(f"  平均成本: ${status['orchestrator']['average_cost']:.3f}")
        logger.info(f"  平均延迟: {status['orchestrator']['average_latency']:.2f}秒")

    logger.info(f"\nAgents:")
    for agent_id, agent_info in status['agents'].items():
        logger.info(f"  {agent_id}: {agent_info['type']}")

    # 清理
    for agent in agents:
        await agent.shutdown()
    await system.shutdown()


async def main():
    """运行所有演示"""
    try:
        logger.info("\n" + "=" * 70)
        logger.info("MCP-A2A完整集成演示")
        logger.info("=" * 70)
        logger.info("\n这是一个完全可运行的端到端示例")
        logger.info("展示MCP 2.0和多智能体系统的深度集成\n")

        # 运行演示
        await demo_integrated_research()
        await demo_integrated_conversation()
        await demo_dynamic_pricing()
        await demo_system_status()

        logger.info("\n" + "=" * 70)
        logger.info("所有演示完成! 🎉")
        logger.info("=" * 70)

        logger.info("\n关键特性:")
        logger.info("  ✓ MCP智能编排 - AI自动规划工具链")
        logger.info("  ✓ 动态工具生成 - 根据上下文定制工具")
        logger.info("  ✓ A2A通信 - Agent间协作")
        logger.info("  ✓ 服务网格 - 分布式路由")
        logger.info("  ✓ 成本优化 - 实时成本追踪")
        logger.info("  ✓ 并行执行 - 智能并行优化")

        logger.info("\n这是真正可用的MCP-A2A集成系统! 🚀")

    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
