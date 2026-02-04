"""
MCP Server Implementation for SalesBoost

Exposes SalesBoost tools, resources, and prompts via Model Context Protocol.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Callable, Dict, List, Optional

from app.mcp.protocol import (
    MCPPrompt,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
    ResourceType,
)

logger = logging.getLogger(__name__)


class MCPServerHandler:
    """Base handler for MCP server operations"""

    async def list_tools(self) -> List[MCPTool]:
        """List available tools"""
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool"""
        raise NotImplementedError(f"Tool not found: {name}")

    async def list_resources(self) -> List[MCPResource]:
        """List available resources"""
        return []

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """Read a resource"""
        raise NotImplementedError(f"Resource not found: {uri}")

    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts"""
        return []

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> MCPPromptResult:
        """Get a prompt with arguments"""
        raise NotImplementedError(f"Prompt not found: {name}")


class SalesBoostMCPServer:
    """
    MCP Server for SalesBoost

    Exposes SalesBoost capabilities via Model Context Protocol:
    - Tools: Sales tools from ToolRegistry
    - Resources: Knowledge base, user profiles, CRM data
    - Prompts: Sales scenario templates

    Usage:
        server = SalesBoostMCPServer(
            tool_registry=registry,
            tool_executor=executor,
            rag_service=rag,
            profile_service=profiles
        )
        await server.run()
    """

    def __init__(
        self,
        name: str = "salesboost-mcp",
        version: str = "1.0.0",
        handler: Optional[MCPServerHandler] = None,
    ):
        self.name = name
        self.version = version
        self.handler = handler or MCPServerHandler()
        self.server_info = MCPServerInfo(
            name=name,
            version=version,
            capabilities={
                "tools": True,
                "resources": True,
                "prompts": True,
            },
        )

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP request

        Args:
            request: MCP request message

        Returns:
            MCP response message
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            elif method == "prompts/list":
                result = await self._handle_list_prompts()
            elif method == "prompts/get":
                result = await self._handle_get_prompt(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        logger.info(f"Initializing MCP server: {self.name}")
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.server_info.to_dict(),
            "capabilities": self.server_info.capabilities,
        }

    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = await self.handler.list_tools()
        return {
            "tools": [tool.to_dict() for tool in tools]
        }

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Tool name is required")

        result = await self.handler.call_tool(name, arguments)
        return result.to_dict()

    async def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = await self.handler.list_resources()
        return {
            "resources": [resource.to_dict() for resource in resources]
        }

    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")

        if not uri:
            raise ValueError("Resource URI is required")

        content = await self.handler.read_resource(uri)
        return {
            "contents": [content.to_dict()]
        }

    async def _handle_list_prompts(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = await self.handler.list_prompts()
        return {
            "prompts": [prompt.to_dict() for prompt in prompts]
        }

    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name")
        arguments = params.get("arguments")

        if not name:
            raise ValueError("Prompt name is required")

        result = await self.handler.get_prompt(name, arguments)
        return result.to_dict()

    async def run_stdio(self):
        """
        Run MCP server using stdio transport

        Reads JSON-RPC messages from stdin and writes responses to stdout.
        """
        logger.info(f"Starting MCP server: {self.name} v{self.version}")

        try:
            while True:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)

                    # Handle request
                    response = await self.handle_request(request)

                    # Write response to stdout
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                        },
                    }
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"MCP server error: {e}", exc_info=True)
            raise

    async def run(self):
        """Run MCP server (defaults to stdio transport)"""
        await self.run_stdio()
