#!/usr/bin/env python3
"""
集成系统启动脚本

启动完整的MCP-A2A集成系统，包括：
- MCP Orchestrator
- Dynamic Tool Generator
- Service Mesh
- A2A Message Bus
- 多个集成Agent

Usage:
    python scripts/start_integrated_system.py
"""

import asyncio
import logging
import signal
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


async def main():
    """Main entry point"""
    system = None
    agents = []

    try:
        logger.info("=" * 70)
        logger.info("启动MCP-A2A集成系统")
        logger.info("=" * 70)

        # 创建集成系统
        logger.info("\n初始化集成系统...")
        system = await create_integrated_system()
        logger.info("✓ 系统初始化完成")

        # 创建SDR Agents
        logger.info("\n创建SDR Agents...")
        for i in range(2):
            sdr = SDRAgentIntegrated(
                agent_id=f"sdr_{i:03d}",
                message_bus=system.a2a_bus,
                orchestrator=system.orchestrator,
                tool_generator=system.tool_generator,
                service_mesh=system.service_mesh,
            )
            await sdr.initialize()
            agents.append(sdr)
            logger.info(f"  ✓ SDR Agent {i+1} 已启动")

        # 创建Coach Agent
        logger.info("\n创建Coach Agent...")
        coach = CoachAgentA2A(
            agent_id="coach_001",
            message_bus=system.a2a_bus,
        )
        await coach.initialize()
        agents.append(coach)
        logger.info("  ✓ Coach Agent 已启动")

        # 创建Compliance Agent
        logger.info("\n创建Compliance Agent...")
        compliance = ComplianceAgentA2A(
            agent_id="compliance_001",
            message_bus=system.a2a_bus,
        )
        await compliance.initialize()
        agents.append(compliance)
        logger.info("  ✓ Compliance Agent 已启动")

        # 显示系统状态
        logger.info("\n" + "=" * 70)
        logger.info("系统已就绪")
        logger.info("=" * 70)

        status = await system.get_system_status()

        logger.info(f"\n运行中的组件:")
        logger.info(f"  • MCP Orchestrator (AI规划)")
        logger.info(f"  • Dynamic Tool Generator (动态工具)")
        logger.info(f"  • Service Mesh ({status['mesh']['total_nodes']} 节点)")
        logger.info(f"  • A2A Message Bus ({status['a2a']['registered_agents']} agents)")

        logger.info(f"\nAgents:")
        for agent_id in status['agents'].keys():
            logger.info(f"  • {agent_id}")

        logger.info(f"\n能力:")
        logger.info(f"  • 智能工具编排")
        logger.info(f"  • 动态工具生成")
        logger.info(f"  • Agent间通信")
        logger.info(f"  • 分布式路由")
        logger.info(f"  • 成本优化")

        logger.info("\n按 Ctrl+C 停止系统")

        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info("\n收到停止信号")
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"系统错误: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Shutdown
        logger.info("\n关闭系统...")

        for agent in agents:
            try:
                await agent.shutdown()
            except Exception as e:
                logger.error(f"Agent关闭错误: {e}")

        if system:
            await system.shutdown()

        logger.info("✓ 系统已停止")


if __name__ == "__main__":
    asyncio.run(main())
