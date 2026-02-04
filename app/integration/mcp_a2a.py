"""
Integration Module for MCP and A2A

Provides integration points for adding MCP and A2A to existing SalesBoost application.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from app.a2a.message_bus import A2AMessageBus
from app.agents.autonomous.sdr_agent_a2a import SDRAgentA2A
from app.agents.roles.coach_agent_a2a import CoachAgentA2A
from app.agents.roles.compliance_agent_a2a import ComplianceAgentA2A
from app.mcp.bridge import MCPBridge
from app.mcp.client import MCPClientManager
from app.mcp.server import SalesBoostMCPServer
from app.mcp.tool_wrapper import register_all_mcp_tools
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPIntegration:
    """
    MCP Integration Manager

    Manages MCP server and client integration with SalesBoost.

    Usage:
        integration = MCPIntegration(
            tool_registry=registry,
            tool_executor=executor
        )

        # Start MCP server
        await integration.start_server()

        # Connect to external MCP servers
        await integration.connect_client("brave-search", "npx", ["-y", "..."])

        # Register external tools
        await integration.register_external_tools()
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        rag_service: Optional[Any] = None,
        profile_service: Optional[Any] = None,
    ):
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.rag_service = rag_service
        self.profile_service = profile_service

        # MCP components
        self.mcp_server: Optional[SalesBoostMCPServer] = None
        self.mcp_client: Optional[MCPClientManager] = None
        self.mcp_bridge: Optional[MCPBridge] = None

    async def start_server(
        self, name: str = "salesboost-mcp", version: str = "1.0.0"
    ):
        """
        Start MCP server

        Args:
            name: Server name
            version: Server version
        """
        logger.info("Starting MCP server...")

        # Create bridge
        self.mcp_bridge = MCPBridge(
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
            rag_service=self.rag_service,
            profile_service=self.profile_service,
        )

        # Create server
        self.mcp_server = SalesBoostMCPServer(
            name=name, version=version, handler=self.mcp_bridge
        )

        logger.info(f"MCP server started: {name} v{version}")

    async def initialize_client(self):
        """Initialize MCP client manager"""
        if not self.mcp_client:
            self.mcp_client = MCPClientManager()
            logger.info("MCP client manager initialized")

    async def connect_client(self, server_name: str, command: str, args: list):
        """
        Connect to external MCP server

        Args:
            server_name: Name for this connection
            command: Command to start server
            args: Command arguments
        """
        if not self.mcp_client:
            await self.initialize_client()

        logger.info(f"Connecting to MCP server: {server_name}")
        await self.mcp_client.connect(server_name, command, args)
        logger.info(f"Connected to MCP server: {server_name}")

    async def register_external_tools(self):
        """Register tools from all connected MCP servers"""
        if not self.mcp_client:
            logger.warning("No MCP client initialized")
            return

        logger.info("Registering external MCP tools...")
        results = await register_all_mcp_tools(
            registry=self.tool_registry, mcp_client=self.mcp_client
        )

        total_tools = sum(results.values())
        logger.info(f"Registered {total_tools} external MCP tools")
        for server_name, count in results.items():
            logger.info(f"  - {server_name}: {count} tools")

    async def shutdown(self):
        """Shutdown MCP integration"""
        if self.mcp_client:
            await self.mcp_client.disconnect_all()
        logger.info("MCP integration shutdown complete")


class A2AIntegration:
    """
    A2A Integration Manager

    Manages A2A message bus and agent integration with SalesBoost.

    Usage:
        integration = A2AIntegration(redis_url="redis://localhost:6379")

        # Initialize message bus
        await integration.initialize()

        # Create agents
        await integration.create_agents()

        # Get agent by ID
        agent = integration.get_agent("sdr_agent_001")
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.message_bus: Optional[A2AMessageBus] = None
        self.agents: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize message bus"""
        logger.info("Initializing A2A message bus...")

        # Create Redis client
        self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()

        # Create message bus
        self.message_bus = A2AMessageBus(redis_client=self.redis_client)

        logger.info("A2A message bus initialized")

    async def create_agents(
        self,
        enable_sdr: bool = True,
        enable_coach: bool = True,
        enable_compliance: bool = True,
    ):
        """
        Create and initialize agents

        Args:
            enable_sdr: Enable SDR agent
            enable_coach: Enable Coach agent
            enable_compliance: Enable Compliance agent
        """
        if not self.message_bus:
            raise RuntimeError("Message bus not initialized")

        logger.info("Creating A2A agents...")

        # SDR Agent
        if enable_sdr:
            sdr_agent = SDRAgentA2A(
                agent_id="sdr_agent_001", message_bus=self.message_bus
            )
            await sdr_agent.initialize()
            self.agents["sdr_agent_001"] = sdr_agent
            logger.info("SDR Agent created")

        # Coach Agent
        if enable_coach:
            coach_agent = CoachAgentA2A(
                agent_id="coach_agent_001", message_bus=self.message_bus
            )
            await coach_agent.initialize()
            self.agents["coach_agent_001"] = coach_agent
            logger.info("Coach Agent created")

        # Compliance Agent
        if enable_compliance:
            compliance_agent = ComplianceAgentA2A(
                agent_id="compliance_agent_001", message_bus=self.message_bus
            )
            await compliance_agent.initialize()
            self.agents["compliance_agent_001"] = compliance_agent
            logger.info("Compliance Agent created")

        logger.info(f"Created {len(self.agents)} A2A agents")

    def get_agent(self, agent_id: str):
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def get_message_bus(self) -> A2AMessageBus:
        """Get message bus instance"""
        if not self.message_bus:
            raise RuntimeError("Message bus not initialized")
        return self.message_bus

    async def shutdown(self):
        """Shutdown A2A integration"""
        logger.info("Shutting down A2A integration...")

        # Shutdown agents
        for agent_id, agent in self.agents.items():
            try:
                await agent.shutdown()
                logger.info(f"Agent shutdown: {agent_id}")
            except Exception as e:
                logger.error(f"Error shutting down agent {agent_id}: {e}")

        # Shutdown message bus
        if self.message_bus:
            await self.message_bus.shutdown()

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

        logger.info("A2A integration shutdown complete")


async def integrate_mcp_and_a2a(
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    redis_url: str = "redis://localhost:6379",
    rag_service: Optional[Any] = None,
    profile_service: Optional[Any] = None,
) -> tuple[MCPIntegration, A2AIntegration]:
    """
    Integrate both MCP and A2A into SalesBoost

    Args:
        tool_registry: Tool registry instance
        tool_executor: Tool executor instance
        redis_url: Redis connection URL
        rag_service: RAG service instance
        profile_service: Profile service instance

    Returns:
        Tuple of (MCP integration, A2A integration)
    """
    logger.info("Integrating MCP and A2A...")

    # Initialize MCP
    mcp_integration = MCPIntegration(
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        rag_service=rag_service,
        profile_service=profile_service,
    )
    await mcp_integration.start_server()
    await mcp_integration.initialize_client()

    # Initialize A2A
    a2a_integration = A2AIntegration(redis_url=redis_url)
    await a2a_integration.initialize()
    await a2a_integration.create_agents()

    logger.info("MCP and A2A integration complete")

    return mcp_integration, a2a_integration
