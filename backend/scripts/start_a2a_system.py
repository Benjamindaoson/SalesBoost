#!/usr/bin/env python3
"""
A2A System Startup Script

Starts the A2A message bus and all configured agents.

Usage:
    python scripts/start_a2a_system.py [--config CONFIG_FILE]
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from redis.asyncio import Redis

from app.a2a.message_bus import A2AMessageBus
from app.agents.autonomous.sdr_agent_a2a import SDRAgentA2A
from app.agents.roles.coach_agent_a2a import CoachAgentA2A
from app.agents.roles.compliance_agent_a2a import ComplianceAgentA2A

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


async def create_message_bus(config: dict) -> A2AMessageBus:
    """Create and initialize message bus"""
    bus_config = config.get("message_bus", {})
    redis_config = bus_config.get("redis", {})

    # Create Redis client
    redis_url = redis_config.get("url", "redis://localhost:6379")
    redis_client = Redis.from_url(redis_url, decode_responses=True)

    # Test connection
    await redis_client.ping()
    logger.info(f"Connected to Redis: {redis_url}")

    # Create message bus
    message_bus = A2AMessageBus(
        redis_client=redis_client,
        channel_prefix=bus_config.get("channels", {}).get("prefix", "a2a"),
        history_ttl=bus_config.get("history", {}).get("ttl", 3600),
    )

    return message_bus


async def create_agents(message_bus: A2AMessageBus, config: dict):
    """Create and initialize all configured agents"""
    agents = []
    agents_config = config.get("agents", {})

    # SDR Agent
    if agents_config.get("sdr_agent", {}).get("enabled", False):
        logger.info("Creating SDR Agent...")
        sdr_agent = SDRAgentA2A(
            agent_id="sdr_agent_001",
            message_bus=message_bus,
        )
        await sdr_agent.initialize()
        agents.append(sdr_agent)
        logger.info("SDR Agent initialized")

    # Coach Agent
    if agents_config.get("coach_agent", {}).get("enabled", False):
        logger.info("Creating Coach Agent...")
        coach_agent = CoachAgentA2A(
            agent_id="coach_agent_001",
            message_bus=message_bus,
        )
        await coach_agent.initialize()
        agents.append(coach_agent)
        logger.info("Coach Agent initialized")

    # Compliance Agent
    if agents_config.get("compliance_agent", {}).get("enabled", False):
        logger.info("Creating Compliance Agent...")
        compliance_agent = ComplianceAgentA2A(
            agent_id="compliance_agent_001",
            message_bus=message_bus,
        )
        await compliance_agent.initialize()
        agents.append(compliance_agent)
        logger.info("Compliance Agent initialized")

    return agents


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Start A2A System")
    parser.add_argument(
        "--config",
        default="config/a2a.yaml",
        help="Path to configuration file",
    )
    args = parser.parse_args()

    message_bus = None
    agents = []

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = await load_config(args.config)

        # Create message bus
        logger.info("Creating message bus...")
        message_bus = await create_message_bus(config)

        # Create agents
        logger.info("Creating agents...")
        agents = await create_agents(message_bus, config)

        logger.info(f"A2A System started with {len(agents)} agents")
        logger.info("Press Ctrl+C to stop")

        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Shutdown agents
        logger.info("Shutting down agents...")
        for agent in agents:
            try:
                await agent.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down agent: {e}")

        # Shutdown message bus
        if message_bus:
            logger.info("Shutting down message bus...")
            await message_bus.shutdown()

        logger.info("A2A System stopped")


if __name__ == "__main__":
    asyncio.run(main())
