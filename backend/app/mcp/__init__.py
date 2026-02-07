"""
MCP (Model Context Protocol) Integration for SalesBoost

This module provides MCP server and client implementations to expose
SalesBoost capabilities and consume external MCP services.
"""

from ..mcp.protocol import (
    MCPTool,
    MCPResource,
    MCPPrompt,
    MCPToolCall,
    MCPToolResult,
)
from ..mcp.server import SalesBoostMCPServer
from ..mcp.client import MCPClientManager
from ..mcp.bridge import MCPBridge

__all__ = [
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPToolCall",
    "MCPToolResult",
    "SalesBoostMCPServer",
    "MCPClientManager",
    "MCPBridge",
]
