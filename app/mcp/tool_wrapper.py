"""
MCP Tool Wrapper

Wraps external MCP tools as SalesBoost tools for integration with ToolRegistry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.mcp.client import MCPClientManager
from app.mcp.protocol import MCPTool
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class MCPToolWrapper(BaseTool):
    """
    Wrapper for external MCP tools

    Allows external MCP tools to be used as SalesBoost tools
    through the ToolRegistry and ToolExecutor.

    Usage:
        # Create wrapper
        tool = MCPToolWrapper(
            mcp_client=client_manager,
            server_name="brave-search",
            mcp_tool=tool_schema
        )

        # Register with ToolRegistry
        registry.register(tool)

        # Execute via ToolExecutor
        result = await executor.execute(
            name=tool.name,
            payload={"query": "sales techniques"}
        )
    """

    def __init__(
        self,
        mcp_client: MCPClientManager,
        server_name: str,
        mcp_tool: MCPTool,
        allowed_agents: Optional[List[str]] = None,
    ):
        """
        Initialize MCP tool wrapper

        Args:
            mcp_client: MCP client manager
            server_name: Name of the MCP server
            mcp_tool: MCP tool schema
            allowed_agents: List of allowed agent types
        """
        self.mcp_client = mcp_client
        self.server_name = server_name
        self.mcp_tool = mcp_tool

        # Generate unique name with server prefix
        tool_name = f"mcp_{server_name}_{mcp_tool.name}"

        # Initialize base tool
        super().__init__(
            name=tool_name,
            description=mcp_tool.description,
            allowed_agents=allowed_agents or ["*"],
            enabled=True,
        )

        # Store input schema
        self._input_schema = mcp_tool.inputSchema

    def schema(self) -> Dict[str, Any]:
        """
        Get tool schema

        Returns:
            Tool schema in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._input_schema,
            },
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute MCP tool

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            logger.info(f"Executing MCP tool: {self.name}")

            # Call MCP tool via client
            result = await self.mcp_client.call_tool(
                server_name=self.server_name,
                tool_name=self.mcp_tool.name,
                arguments=kwargs,
            )

            # Check for errors
            if result.isError:
                return {
                    "success": False,
                    "error": result.content,
                    "metadata": result.metadata,
                }

            # Return successful result
            return {
                "success": True,
                "result": result.content,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error(f"Error executing MCP tool {self.name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }


async def register_mcp_tools(
    registry,
    mcp_client: MCPClientManager,
    server_name: str,
    allowed_agents: Optional[List[str]] = None,
) -> int:
    """
    Register all tools from an MCP server to ToolRegistry

    Args:
        registry: ToolRegistry instance
        mcp_client: MCP client manager
        server_name: Name of the MCP server
        allowed_agents: List of allowed agent types for these tools

    Returns:
        Number of tools registered
    """
    try:
        logger.info(f"Registering MCP tools from server: {server_name}")

        # List tools from server
        tools = await mcp_client.list_tools(server_name)

        # Register each tool
        count = 0
        for mcp_tool in tools:
            try:
                # Create wrapper
                wrapper = MCPToolWrapper(
                    mcp_client=mcp_client,
                    server_name=server_name,
                    mcp_tool=mcp_tool,
                    allowed_agents=allowed_agents,
                )

                # Register with registry
                registry.register(wrapper)
                count += 1

                logger.info(f"Registered MCP tool: {wrapper.name}")

            except Exception as e:
                logger.error(f"Error registering tool {mcp_tool.name}: {e}")

        logger.info(f"Registered {count} MCP tools from {server_name}")
        return count

    except Exception as e:
        logger.error(f"Error registering MCP tools from {server_name}: {e}")
        return 0


async def register_all_mcp_tools(
    registry,
    mcp_client: MCPClientManager,
    allowed_agents: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Register tools from all connected MCP servers

    Args:
        registry: ToolRegistry instance
        mcp_client: MCP client manager
        allowed_agents: List of allowed agent types for these tools

    Returns:
        Dictionary mapping server names to number of tools registered
    """
    results = {}

    for server_name in mcp_client.clients.keys():
        count = await register_mcp_tools(
            registry=registry,
            mcp_client=mcp_client,
            server_name=server_name,
            allowed_agents=allowed_agents,
        )
        results[server_name] = count

    return results
