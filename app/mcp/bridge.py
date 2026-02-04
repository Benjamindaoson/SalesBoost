"""
MCP Bridge for SalesBoost

Integrates all MCP adapters and provides a unified handler for the MCP server.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.mcp.adapters import (
    MCPPromptAdapter,
    MCPProfileAdapter,
    MCPRAGAdapter,
    MCPToolAdapter,
)
from app.mcp.protocol import (
    MCPPrompt,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPTool,
    MCPToolResult,
)
from app.mcp.server import MCPServerHandler
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPBridge(MCPServerHandler):
    """
    MCP Bridge for SalesBoost

    Integrates all MCP adapters and provides a unified interface
    for the MCP server to access SalesBoost capabilities.

    Usage:
        bridge = MCPBridge(
            tool_registry=registry,
            tool_executor=executor,
            rag_service=rag,
            profile_service=profiles
        )

        server = SalesBoostMCPServer(handler=bridge)
        await server.run()
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        rag_service: Optional[Any] = None,
        profile_service: Optional[Any] = None,
        prompt_templates: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP bridge

        Args:
            tool_registry: Tool registry instance
            tool_executor: Tool executor instance
            rag_service: RAG service instance (optional)
            profile_service: Profile service instance (optional)
            prompt_templates: Custom prompt templates (optional)
        """
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor

        # Initialize adapters
        self.tool_adapter = MCPToolAdapter(tool_registry)
        self.rag_adapter = MCPRAGAdapter(rag_service) if rag_service else None
        self.profile_adapter = (
            MCPProfileAdapter(profile_service) if profile_service else None
        )
        self.prompt_adapter = MCPPromptAdapter(prompt_templates)

        logger.info("MCP Bridge initialized")

    async def list_tools(self) -> List[MCPTool]:
        """
        List available tools

        Returns:
            List of MCP tools from ToolRegistry
        """
        try:
            tools = self.tool_adapter.to_mcp_tools(
                agent_type=None, include_disabled=False
            )
            logger.info(f"Listed {len(tools)} tools")
            return tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """
        Execute a tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            logger.info(f"Calling tool: {name}")

            # Execute tool via ToolExecutor
            result = await self.tool_executor.execute(
                name=name,
                payload=arguments,
                caller_role="mcp_client",
                agent_type="mcp",
            )

            # Check if execution was successful
            if result.get("ok"):
                return MCPToolResult(
                    call_id=result.get("tool_call_id"),
                    content=result.get("result"),
                    isError=False,
                    metadata={
                        "execution_time": result.get("execution_time"),
                        "cache_hit": result.get("cache_hit", False),
                    },
                )
            else:
                # Tool execution failed
                error_info = result.get("error", {})
                return MCPToolResult(
                    call_id=result.get("tool_call_id"),
                    content=error_info.get("message", "Tool execution failed"),
                    isError=True,
                    metadata={
                        "error_code": error_info.get("code"),
                        "error_type": error_info.get("type"),
                    },
                )

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=True)
            return MCPToolResult(
                call_id=None,
                content=str(e),
                isError=True,
                metadata={"error_type": type(e).__name__},
            )

    async def list_resources(self) -> List[MCPResource]:
        """
        List available resources

        Returns:
            List of MCP resources (knowledge, profiles, etc.)
        """
        resources = []

        try:
            # Add RAG resources
            if self.rag_adapter:
                resources.extend(self.rag_adapter.get_resources())

            # Add profile resources
            if self.profile_adapter:
                resources.extend(self.profile_adapter.get_resources())

            logger.info(f"Listed {len(resources)} resources")
            return resources

        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            return []

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """
        Read a resource

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            ValueError: If resource not found or invalid URI
        """
        try:
            logger.info(f"Reading resource: {uri}")

            # Route to appropriate adapter based on URI
            if uri.startswith("salesboost://knowledge/"):
                if not self.rag_adapter:
                    raise ValueError("RAG service not available")
                return await self.rag_adapter.read_resource(uri)

            elif uri.startswith("salesboost://profile/"):
                if not self.profile_adapter:
                    raise ValueError("Profile service not available")
                return await self.profile_adapter.read_resource(uri)

            else:
                raise ValueError(f"Unknown resource URI: {uri}")

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            raise

    async def list_prompts(self) -> List[MCPPrompt]:
        """
        List available prompts

        Returns:
            List of MCP prompts
        """
        try:
            prompts = self.prompt_adapter.get_prompts()
            logger.info(f"Listed {len(prompts)} prompts")
            return prompts
        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            return []

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> MCPPromptResult:
        """
        Get a prompt with arguments

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result with filled template

        Raises:
            ValueError: If prompt not found or missing required arguments
        """
        try:
            logger.info(f"Getting prompt: {name}")
            return await self.prompt_adapter.get_prompt(name, arguments)
        except Exception as e:
            logger.error(f"Error getting prompt {name}: {e}")
            raise
