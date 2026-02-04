"""
Test Suite for MCP Integration

Tests for MCP server, client, and adapters.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.mcp.protocol import MCPTool, MCPResource, MCPPrompt
from app.mcp.server import SalesBoostMCPServer, MCPServerHandler
from app.mcp.client import MCPClientManager, MCPClientSession
from app.mcp.adapters import MCPToolAdapter, MCPRAGAdapter, MCPPromptAdapter
from app.mcp.bridge import MCPBridge
from app.mcp.tool_wrapper import MCPToolWrapper
from app.tools.registry import ToolRegistry
from app.tools.base import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing"""

    def __init__(self):
        super().__init__(
            name="mock_tool",
            description="A mock tool for testing",
            allowed_agents=["*"],
        )

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query string"}
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(self, **kwargs):
        return {"success": True, "result": f"Executed with {kwargs}"}


@pytest.fixture
def tool_registry():
    """Create a tool registry with mock tools"""
    registry = ToolRegistry()
    registry.register(MockTool())
    return registry


@pytest.fixture
def tool_executor():
    """Create a mock tool executor"""
    executor = AsyncMock()
    executor.execute = AsyncMock(
        return_value={
            "ok": True,
            "result": {"data": "test result"},
            "tool_call_id": "test_123",
            "execution_time": 0.1,
        }
    )
    return executor


class TestMCPToolAdapter:
    """Tests for MCPToolAdapter"""

    def test_to_mcp_tools(self, tool_registry):
        """Test converting tools to MCP format"""
        adapter = MCPToolAdapter(tool_registry)
        mcp_tools = adapter.to_mcp_tools()

        assert len(mcp_tools) == 1
        assert isinstance(mcp_tools[0], MCPTool)
        assert mcp_tools[0].name == "mock_tool"
        assert mcp_tools[0].description == "A mock tool for testing"

    def test_convert_tool_schema(self, tool_registry):
        """Test tool schema conversion"""
        adapter = MCPToolAdapter(tool_registry)
        tools = tool_registry.list_tools()
        mcp_tool = adapter._convert_tool(tools[0])

        assert mcp_tool.inputSchema["type"] == "object"
        assert "query" in mcp_tool.inputSchema["properties"]


class TestMCPServer:
    """Tests for MCP Server"""

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize request"""
        server = SalesBoostMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_handle_list_tools(self, tool_registry, tool_executor):
        """Test tools/list request"""
        from app.mcp.bridge import MCPBridge

        bridge = MCPBridge(
            tool_registry=tool_registry, tool_executor=tool_executor
        )
        server = SalesBoostMCPServer(handler=bridge)

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        response = await server.handle_request(request)

        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 1

    @pytest.mark.asyncio
    async def test_handle_call_tool(self, tool_registry, tool_executor):
        """Test tools/call request"""
        from app.mcp.bridge import MCPBridge

        bridge = MCPBridge(
            tool_registry=tool_registry, tool_executor=tool_executor
        )
        server = SalesBoostMCPServer(handler=bridge)

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "mock_tool", "arguments": {"query": "test"}},
        }

        response = await server.handle_request(request)

        assert "result" in response
        assert response["result"]["isError"] is False


class TestMCPClient:
    """Tests for MCP Client"""

    @pytest.mark.asyncio
    async def test_client_manager_connect(self):
        """Test connecting to MCP server"""
        manager = MCPClientManager()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stdout.readline.return_value = '{"jsonrpc":"2.0","id":1,"result":{}}\n'
            mock_popen.return_value = mock_process

            session = await manager.connect("test-server", "echo", ["test"])

            assert "test-server" in manager.clients
            assert isinstance(session, MCPClientSession)


class TestMCPBridge:
    """Tests for MCP Bridge"""

    @pytest.mark.asyncio
    async def test_list_tools(self, tool_registry, tool_executor):
        """Test listing tools via bridge"""
        bridge = MCPBridge(
            tool_registry=tool_registry, tool_executor=tool_executor
        )

        tools = await bridge.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "mock_tool"

    @pytest.mark.asyncio
    async def test_call_tool(self, tool_registry, tool_executor):
        """Test calling tool via bridge"""
        bridge = MCPBridge(
            tool_registry=tool_registry, tool_executor=tool_executor
        )

        result = await bridge.call_tool("mock_tool", {"query": "test"})

        assert result.isError is False
        tool_executor.execute.assert_called_once()


class TestMCPPromptAdapter:
    """Tests for MCP Prompt Adapter"""

    def test_get_prompts(self):
        """Test getting prompt list"""
        adapter = MCPPromptAdapter()
        prompts = adapter.get_prompts()

        assert len(prompts) > 0
        assert all(isinstance(p, MCPPrompt) for p in prompts)

    @pytest.mark.asyncio
    async def test_get_prompt(self):
        """Test getting filled prompt"""
        adapter = MCPPromptAdapter()

        result = await adapter.get_prompt(
            "objection_handling",
            {"objection_type": "price", "context": "Enterprise deal"},
        )

        assert len(result.messages) > 0
        assert "price" in result.messages[0].content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
