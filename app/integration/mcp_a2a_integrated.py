"""
MCP-A2A Integration Layer

将MCP 2.0的智能编排能力与A2A多智能体系统深度集成。

核心功能：
1. Agent可以使用MCPOrchestrator进行智能规划
2. Agent可以使用DynamicToolGenerator生成定制工具
3. Agent通过MCPMesh进行分布式协作
4. A2A消息总线和MCP服务网格协同工作

Author: Claude (Anthropic)
Version: 2.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from app.a2a.message_bus import A2AMessageBus
from app.a2a.protocol import A2AMessage, MessageType
from app.mcp.orchestrator import MCPOrchestrator
from app.mcp.dynamic_tools import DynamicToolGenerator
from app.mcp.service_mesh import MCPMesh, RoutingStrategy
from app.mcp.learning_engine import MCPLearningEngine
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPEnabledAgent:
    """
    MCP增强的Agent基类

    为Agent提供MCP能力：
    - 智能工具编排
    - 动态工具生成
    - 服务网格访问
    """

    def __init__(
        self,
        agent_id: str,
        orchestrator: MCPOrchestrator,
        tool_generator: DynamicToolGenerator,
        service_mesh: MCPMesh,
        learning_engine: Optional[MCPLearningEngine] = None,
    ):
        self.agent_id = agent_id
        self.orchestrator = orchestrator
        self.tool_generator = tool_generator
        self.service_mesh = service_mesh
        self.learning_engine = learning_engine

    async def plan_and_execute(
        self,
        intent: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        使用MCP Orchestrator进行智能规划和执行

        Args:
            intent: 意图描述
            context: 上下文
            constraints: 约束条件

        Returns:
            执行结果
        """
        logger.info(f"[{self.agent_id}] Planning: {intent}")

        # AI规划
        plan = await self.orchestrator.plan(intent, context, constraints)

        logger.info(
            f"[{self.agent_id}] Plan created: {len(plan.tool_calls)} tools, "
            f"cost=${plan.estimated_cost:.3f}"
        )

        # Execute
        result = await self.orchestrator.execute(plan)

        logger.info(
            f"[{self.agent_id}] Execution {'succeeded' if result.success else 'failed'}: "
            f"cost=${result.total_cost:.3f}, latency={result.total_latency:.2f}s"
        )

        # Record execution for learning
        if self.learning_engine and result.success:
            for tool_call, tool_result in zip(plan.tool_calls, result.results):
                self.learning_engine.record_execution(
                    tool_name=tool_call.tool_name,
                    parameters=tool_call.parameters,
                    context=context,
                    success=tool_result.get("success", True),
                    latency=tool_result.get("latency", 0.0),
                    cost=tool_result.get("cost", 0.0),
                    quality_score=tool_result.get("quality_score", 0.8),
                )

            # Record tool combination
            tool_names = [tc.tool_name for tc in plan.tool_calls]
            self.learning_engine.record_combination(
                tools=tool_names,
                success=result.success,
                total_cost=result.total_cost,
                total_latency=result.total_latency,
                quality_score=0.8,  # Could be computed from results
            )

        return result

    async def generate_custom_tool(
        self, template_id: str, context: Dict[str, Any]
    ) -> Any:
        """
        动态生成定制化工具

        Args:
            template_id: 工具模板ID
            context: 上下文数据

        Returns:
            生成的工具
        """
        logger.info(f"[{self.agent_id}] Generating tool: {template_id}")

        tool = await self.tool_generator.generate(template_id, context)

        logger.info(f"[{self.agent_id}] Tool generated: {tool.name}")

        return tool

    async def call_mesh_capability(
        self,
        capability: str,
        method: str,
        params: Dict[str, Any],
        strategy: RoutingStrategy = RoutingStrategy.WEIGHTED,
    ) -> Any:
        """
        通过服务网格调用能力

        Args:
            capability: 能力名称
            method: 方法名
            params: 参数
            strategy: 路由策略

        Returns:
            调用结果
        """
        logger.info(f"[{self.agent_id}] Calling mesh capability: {capability}.{method}")

        result = await self.service_mesh.call_capability(
            capability=capability,
            method=method,
            params=params,
            strategy=strategy,
        )

        logger.info(f"[{self.agent_id}] Mesh call completed")

        return result


class IntegratedSystem:
    """
    MCP-A2A集成系统

    完整集成MCP 2.0和A2A多智能体系统。

    Usage:
        system = IntegratedSystem()
        await system.initialize()

        # 创建MCP增强的Agent
        sdr = await system.create_mcp_agent(
            agent_id="sdr_001",
            agent_type="SDRAgent",
            capabilities=["sales", "objection_handling"]
        )

        # Agent使用MCP能力
        result = await sdr.plan_and_execute(
            intent="research customer and create strategy",
            context={"customer": "Acme Corp"}
        )
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        llm_client: Optional[Any] = None,
    ):
        self.redis_url = redis_url
        self.llm_client = llm_client

        # Components
        self.redis_client: Optional[Redis] = None
        self.a2a_bus: Optional[A2AMessageBus] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.orchestrator: Optional[MCPOrchestrator] = None
        self.tool_generator: Optional[DynamicToolGenerator] = None
        self.service_mesh: Optional[MCPMesh] = None
        self.learning_engine: Optional[MCPLearningEngine] = None

        # Agents
        self.agents: Dict[str, Any] = {}

    async def initialize(self):
        """初始化系统"""
        logger.info("Initializing Integrated MCP-A2A System...")

        # 1. Initialize Redis
        self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("✓ Redis connected")

        # 2. Initialize A2A Message Bus
        self.a2a_bus = A2AMessageBus(self.redis_client)
        logger.info("✓ A2A Message Bus initialized")

        # 3. Initialize Tool System
        from app.tools.registry import build_default_registry

        self.tool_registry = build_default_registry()
        self.tool_executor = ToolExecutor(registry=self.tool_registry)
        logger.info("✓ Tool System initialized")

        # 4. Initialize MCP Orchestrator
        if not self.llm_client:
            # Use mock LLM for demo
            self.llm_client = self._create_mock_llm()

        self.orchestrator = MCPOrchestrator(
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
            llm_client=self.llm_client,
        )
        logger.info("✓ MCP Orchestrator initialized")

        # 5. Initialize Dynamic Tool Generator
        self.tool_generator = DynamicToolGenerator()
        logger.info("✓ Dynamic Tool Generator initialized")

        # 6. Initialize Service Mesh
        self.service_mesh = MCPMesh()
        await self.service_mesh.start()
        logger.info("✓ MCP Service Mesh initialized")

        # 7. Initialize Learning Engine
        self.learning_engine = MCPLearningEngine(
            learning_rate=0.1,
            min_samples_for_learning=10,
        )
        logger.info("✓ MCP Learning Engine initialized")

        logger.info("✓ System initialization complete")

    def _create_mock_llm(self):
        """Create mock LLM client for demo"""

        class MockLLMClient:
            async def chat_completion(self, messages, **kwargs):
                class Response:
                    content = '''
{
    "tool_calls": [
        {
            "call_id": "call_1",
            "tool_name": "knowledge_retriever",
            "parameters": {"query": "customer research"},
            "dependencies": [],
            "priority": "high"
        },
        {
            "call_id": "call_2",
            "tool_name": "profile_reader",
            "parameters": {"user_id": "customer_id"},
            "dependencies": [],
            "priority": "normal"
        }
    ],
    "reasoning": "Gather customer information in parallel"
}
'''
                return Response()

        return MockLLMClient()

    async def create_mcp_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MCPEnabledAgent:
        """
        创建MCP增强的Agent

        Args:
            agent_id: Agent ID
            agent_type: Agent类型
            capabilities: 能力列表
            metadata: 元数据

        Returns:
            MCP增强的Agent
        """
        logger.info(f"Creating MCP-enabled agent: {agent_id} ({agent_type})")

        # Register with A2A
        await self.a2a_bus.register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            metadata=metadata or {},
        )

        # Register with Service Mesh
        await self.service_mesh.register_node(
            node_id=agent_id,
            name=f"{agent_type} ({agent_id})",
            endpoint=f"local://{agent_id}",
            capabilities=set(capabilities),
        )

        # Create MCP-enabled agent
        agent = MCPEnabledAgent(
            agent_id=agent_id,
            orchestrator=self.orchestrator,
            tool_generator=self.tool_generator,
            service_mesh=self.service_mesh,
            learning_engine=self.learning_engine,
        )

        self.agents[agent_id] = agent

        logger.info(f"✓ Agent created: {agent_id}")

        return agent

    async def send_a2a_message(
        self, from_agent: str, to_agent: str, message_type: MessageType, payload: Dict
    ):
        """发送A2A消息"""
        message = A2AMessage(
            message_type=message_type,
            from_agent=from_agent,
            to_agent=to_agent,
            conversation_id="integrated_system",
            payload=payload,
        )

        await self.a2a_bus.publish(message)

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        a2a_stats = await self.a2a_bus.get_stats()
        mesh_status = self.service_mesh.get_mesh_status()
        orchestrator_stats = self.orchestrator.get_performance_stats()
        learning_report = self.learning_engine.get_performance_report() if self.learning_engine else {}

        return {
            "a2a": a2a_stats,
            "mesh": mesh_status,
            "orchestrator": orchestrator_stats,
            "learning": learning_report,
            "agents": {
                agent_id: {
                    "type": type(agent).__name__,
                }
                for agent_id, agent in self.agents.items()
            },
        }

    async def shutdown(self):
        """关闭系统"""
        logger.info("Shutting down Integrated System...")

        # Shutdown service mesh
        if self.service_mesh:
            await self.service_mesh.stop()

        # Shutdown A2A bus
        if self.a2a_bus:
            await self.a2a_bus.shutdown()

        # Close Redis
        if self.redis_client:
            await self.redis_client.close()

        logger.info("✓ System shutdown complete")


# Convenience function
async def create_integrated_system(
    redis_url: str = "redis://localhost:6379",
    llm_client: Optional[Any] = None,
) -> IntegratedSystem:
    """
    创建并初始化集成系统

    Args:
        redis_url: Redis URL
        llm_client: LLM client (optional)

    Returns:
        初始化完成的集成系统
    """
    system = IntegratedSystem(redis_url=redis_url, llm_client=llm_client)
    await system.initialize()
    return system
