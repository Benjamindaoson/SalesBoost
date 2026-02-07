#!/usr/bin/env python3
"""
MCP Server Startup Script

Starts the SalesBoost MCP server to expose capabilities via Model Context Protocol.

Usage:
    python scripts/start_mcp_server.py [--config CONFIG_FILE]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.mcp.server import SalesBoostMCPServer
from app.mcp.bridge import MCPBridge
from app.tools.registry import build_default_registry
from app.tools.executor import ToolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def load_config(config_file: str):
    """Load configuration from YAML file"""
    import yaml

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


async def initialize_services():
    """Initialize required services"""
    # Build tool registry
    registry = build_default_registry()

    # Create tool executor
    executor = ToolExecutor(registry=registry)

    # TODO: Initialize RAG service
    rag_service = None

    # TODO: Initialize profile service
    profile_service = None

    return registry, executor, rag_service, profile_service


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Start SalesBoost MCP Server")
    parser.add_argument(
        "--config",
        default="config/mcp_server.yaml",
        help="Path to configuration file",
    )
    args = parser.parse_args()

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = await load_config(args.config)

        # Initialize services
        logger.info("Initializing services...")
        registry, executor, rag_service, profile_service = await initialize_services()

        # Create MCP bridge
        logger.info("Creating MCP bridge...")
        bridge = MCPBridge(
            tool_registry=registry,
            tool_executor=executor,
            rag_service=rag_service,
            profile_service=profile_service,
        )

        # Create MCP server
        server_config = config.get("server", {})
        server = SalesBoostMCPServer(
            name=server_config.get("name", "salesboost-mcp"),
            version=server_config.get("version", "1.0.0"),
            handler=bridge,
        )

        # Start server
        logger.info("Starting MCP server...")
        logger.info("Server is ready to accept connections via stdio")
        await server.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
