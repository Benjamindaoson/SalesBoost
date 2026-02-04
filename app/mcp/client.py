"""
MCP Client Implementation for SalesBoost

Connects to external MCP servers and consumes their capabilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

from app.mcp.protocol import (
    MCPPrompt,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPTool,
    MCPToolResult,
)

logger = logging.getLogger(__name__)


class MCPClientSession:
    """
    MCP Client Session

    Manages a connection to a single MCP server via stdio transport.
    """

    def __init__(self, server_name: str, command: str, args: List[str]):
        """
        Initialize MCP client session

        Args:
            server_name: Name of the MCP server
            command: Command to start the server
            args: Command arguments
        """
        self.server_name = server_name
        self.command = command
        self.args = args
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.initialized = False

    async def connect(self):
        """Connect to MCP server"""
        try:
            logger.info(f"Connecting to MCP server: {self.server_name}")

            # Start server process
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Initialize connection
            await self._initialize()

            logger.info(f"Connected to MCP server: {self.server_name}")

        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            raise

    async def _initialize(self):
        """Initialize MCP connection"""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "salesboost-client",
                "version": "1.0.0",
            },
        })

        if "error" in response:
            raise RuntimeError(f"Initialization failed: {response['error']}")

        self.initialized = True
        logger.info(f"MCP server initialized: {response.get('result', {})}")

    async def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send JSON-RPC request to server

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response from server
        """
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Not connected to MCP server")

        # Create request
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # Read response
        response_line = await asyncio.get_event_loop().run_in_executor(
            None, self.process.stdout.readline
        )

        if not response_line:
            raise RuntimeError("No response from MCP server")

        response = json.loads(response_line)
        return response

    async def list_tools(self) -> List[MCPTool]:
        """List available tools from server"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        response = await self._send_request("tools/list")

        if "error" in response:
            raise RuntimeError(f"Error listing tools: {response['error']}")

        tools_data = response.get("result", {}).get("tools", [])
        return [
            MCPTool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
                metadata=tool.get("metadata"),
            )
            for tool in tools_data
        ]

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """
        Call a tool on the server

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })

        if "error" in response:
            return MCPToolResult(
                call_id=None,
                content=response["error"].get("message", "Unknown error"),
                isError=True,
            )

        result_data = response.get("result", {})
        return MCPToolResult(
            call_id=result_data.get("call_id"),
            content=result_data.get("content"),
            isError=result_data.get("isError", False),
            metadata=result_data.get("metadata"),
        )

    async def list_resources(self) -> List[MCPResource]:
        """List available resources from server"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        response = await self._send_request("resources/list")

        if "error" in response:
            raise RuntimeError(f"Error listing resources: {response['error']}")

        resources_data = response.get("result", {}).get("resources", [])
        return [
            MCPResource(
                uri=res["uri"],
                name=res["name"],
                description=res.get("description"),
                mimeType=res.get("mimeType", "application/json"),
                metadata=res.get("metadata"),
            )
            for res in resources_data
        ]

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """
        Read a resource from the server

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        response = await self._send_request("resources/read", {"uri": uri})

        if "error" in response:
            raise RuntimeError(f"Error reading resource: {response['error']}")

        contents = response.get("result", {}).get("contents", [])
        if not contents:
            raise RuntimeError(f"No content returned for resource: {uri}")

        content_data = contents[0]
        return MCPResourceContent(
            uri=content_data["uri"],
            mimeType=content_data["mimeType"],
            text=content_data.get("text"),
            blob=content_data.get("blob"),
            metadata=content_data.get("metadata"),
        )

    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompts from server"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        response = await self._send_request("prompts/list")

        if "error" in response:
            raise RuntimeError(f"Error listing prompts: {response['error']}")

        prompts_data = response.get("result", {}).get("prompts", [])
        return [
            MCPPrompt(
                name=prompt["name"],
                description=prompt["description"],
                arguments=prompt.get("arguments", []),
                metadata=prompt.get("metadata"),
            )
            for prompt in prompts_data
        ]

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> MCPPromptResult:
        """
        Get a prompt from the server

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result
        """
        if not self.initialized:
            raise RuntimeError("Client not initialized")

        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        response = await self._send_request("prompts/get", params)

        if "error" in response:
            raise RuntimeError(f"Error getting prompt: {response['error']}")

        result_data = response.get("result", {})
        return MCPPromptResult(
            messages=result_data.get("messages", []),
            metadata=result_data.get("metadata"),
        )

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.initialized = False
            logger.info(f"Disconnected from MCP server: {self.server_name}")


class MCPClientManager:
    """
    MCP Client Manager

    Manages multiple MCP client connections and provides a unified interface
    for consuming external MCP services.

    Usage:
        manager = MCPClientManager()

        # Connect to external MCP server
        await manager.connect(
            "brave-search",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"]
        )

        # Call tool
        result = await manager.call_tool(
            "brave-search",
            "brave_web_search",
            {"query": "sales techniques"}
        )
    """

    def __init__(self):
        self.clients: Dict[str, MCPClientSession] = {}

    async def connect(
        self, server_name: str, command: str, args: List[str]
    ) -> MCPClientSession:
        """
        Connect to an MCP server

        Args:
            server_name: Name for this server connection
            command: Command to start the server
            args: Command arguments

        Returns:
            Client session
        """
        if server_name in self.clients:
            logger.warning(f"Already connected to {server_name}")
            return self.clients[server_name]

        session = MCPClientSession(server_name, command, args)
        await session.connect()

        self.clients[server_name] = session
        return session

    async def disconnect(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.clients:
            await self.clients[server_name].disconnect()
            del self.clients[server_name]

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name in list(self.clients.keys()):
            await self.disconnect(server_name)

    def get_session(self, server_name: str) -> MCPClientSession:
        """Get a client session by name"""
        if server_name not in self.clients:
            raise ValueError(f"Not connected to server: {server_name}")
        return self.clients[server_name]

    async def list_tools(self, server_name: str) -> List[MCPTool]:
        """List tools from a specific server"""
        session = self.get_session(server_name)
        return await session.list_tools()

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """
        Call a tool on a specific server

        Args:
            server_name: Server name
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        session = self.get_session(server_name)
        return await session.call_tool(tool_name, arguments)

    async def list_resources(self, server_name: str) -> List[MCPResource]:
        """List resources from a specific server"""
        session = self.get_session(server_name)
        return await session.list_resources()

    async def read_resource(self, server_name: str, uri: str) -> MCPResourceContent:
        """
        Read a resource from a specific server

        Args:
            server_name: Server name
            uri: Resource URI

        Returns:
            Resource content
        """
        session = self.get_session(server_name)
        return await session.read_resource(uri)

    async def list_all_tools(self) -> Dict[str, List[MCPTool]]:
        """List tools from all connected servers"""
        all_tools = {}
        for server_name, session in self.clients.items():
            try:
                tools = await session.list_tools()
                all_tools[server_name] = tools
            except Exception as e:
                logger.error(f"Error listing tools from {server_name}: {e}")
        return all_tools
