"""
Integration Module

Provides integration utilities for MCP and A2A systems.
"""

from app.integration.mcp_a2a import (
    MCPIntegration,
    A2AIntegration,
    integrate_mcp_and_a2a,
)

__all__ = [
    "MCPIntegration",
    "A2AIntegration",
    "integrate_mcp_and_a2a",
]
