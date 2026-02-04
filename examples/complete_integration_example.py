#!/usr/bin/env python3
"""
Complete MCP & A2A Integration Example

Demonstrates full integration of MCP and A2A systems in SalesBoost.

This example shows:
1. Starting MCP server and client
2. Initializing A2A message bus and agents
3. Agent-to-agent communication
4. Using external MCP tools
5. Complete sales conversation flow

Usage:
    python examples/complete_integration_example.py
"""

import asyncio
import logging
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
from app.integration import MCPIntegration, A2AIntegration
from app.tools.registry import build_default_registry
from app.tools.executor import ToolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_a2a_communication():
    """Demonstrate A2A agent communication"""
    logger.info("=" * 60)
    logger.info("DEMO: A2A Agent Communication")
    logger.info("=" * 60)

    # Initialize A2A
    redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
    await redis_client.ping()
    logger.info("✓ Connected to Redis")

    message_bus = A2AMessageBus(redis_client)

    # Create agents
    sdr_agent = SDRAgentA2A(agent_id="sdr_demo", message_bus=message_bus)
    coach_agent = CoachAgentA2A(agent_id="coach_demo", message_bus=message_bus)
    compliance_agent = ComplianceAgentA2A(
        agent_id="compliance_demo", message_bus=message_bus
    )

    await sdr_agent.initialize()
    await coach_agent.initialize()
    await compliance_agent.initialize()
    logger.info("✓ Agents initialized")

    # Demo 1: SDR requests coaching
    logger.info("\n--- Demo 1: SDR requests coaching ---")
    response = await sdr_agent.send_request(
        to_agent="coach_demo",
        action="get_suggestion",
        parameters={
            "customer_message": "I'm not sure if this is right for us",
            "context": {"industry": "SaaS", "company_size": "50-100"},
            "stage": "discovery",
        },
        timeout=10.0,
    )

    suggestion = response.payload.get("result", {})
    logger.info(f"Coach suggestion received:")
    logger.info(f"  Approach: {suggestion.get('recommended_approach')}")
    logger.info(f"  Key points: {suggestion.get('key_points', [])[:2]}")

    # Demo 2: Generate response and check compliance
    logger.info("\n--- Demo 2: Generate response with compliance check ---")

    # Generate response
    sales_response = await sdr_agent._generate_response({
        "customer_message": "What's your pricing?",
        "context": {},
        "stage": "pitch",
    })
    logger.info(f"Generated response: {sales_response['message'][:100]}...")

    # Check compliance
    compliance_response = await sdr_agent.send_request(
        to_agent="compliance_demo",
        action="check_compliance",
        parameters={"content": sales_response["message"]},
        timeout=5.0,
    )

    compliance_result = compliance_response.payload.get("result", {})
    logger.info(f"Compliance check:")
    logger.info(f"  Compliant: {compliance_result.get('compliant')}")
    logger.info(f"  Risk level: {compliance_result.get('risk_level')}")

    # Demo 3: Broadcast event
    logger.info("\n--- Demo 3: Broadcast deal closed event ---")
    await sdr_agent.broadcast_event(
        event_type="deal_closed",
        data={
            "deal_value": 50000,
            "customer_id": "demo_customer",
            "technique": "assumptive_close",
        },
    )
    logger.info("✓ Event broadcasted to all agents")

    # Give agents time to process event
    await asyncio.sleep(1)

    # Demo 4: Agent discovery
    logger.info("\n--- Demo 4: Agent discovery ---")
    coaches = await sdr_agent.discover_agents(capability="coaching")
    logger.info(f"Found {len(coaches)} coach agents: {coaches}")

    compliance_agents = await sdr_agent.discover_agents(capability="compliance_check")
    logger.info(f"Found {len(compliance_agents)} compliance agents: {compliance_agents}")

    # Cleanup
    await sdr_agent.shutdown()
    await coach_agent.shutdown()
    await compliance_agent.shutdown()
    await message_bus.shutdown()
    await redis_client.close()

    logger.info("\n✓ A2A demo completed successfully")


async def demo_mcp_integration():
    """Demonstrate MCP integration"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO: MCP Integration")
    logger.info("=" * 60)

    # Build tool registry
    registry = build_default_registry()
    executor = ToolExecutor(registry=registry)
    logger.info("✓ Tool registry initialized")

    # Create MCP integration
    mcp = MCPIntegration(
        tool_registry=registry,
        tool_executor=executor,
    )

    # Start MCP server (in background)
    await mcp.start_server(name="salesboost-demo", version="1.0.0")
    logger.info("✓ MCP server started")

    # Initialize MCP client
    await mcp.initialize_client()
    logger.info("✓ MCP client initialized")

    # Demo: List available tools
    logger.info("\n--- Available SalesBoost Tools (via MCP) ---")
    tools = await mcp.mcp_bridge.list_tools()
    for tool in tools[:5]:  # Show first 5
        logger.info(f"  - {tool.name}: {tool.description}")

    # Demo: List available resources
    logger.info("\n--- Available Resources (via MCP) ---")
    resources = await mcp.mcp_bridge.list_resources()
    for resource in resources:
        logger.info(f"  - {resource.uri}: {resource.name}")

    # Demo: List available prompts
    logger.info("\n--- Available Prompts (via MCP) ---")
    prompts = await mcp.mcp_bridge.list_prompts()
    for prompt in prompts:
        logger.info(f"  - {prompt.name}: {prompt.description}")

    # Demo: Get a prompt
    logger.info("\n--- Demo: Get objection handling prompt ---")
    prompt_result = await mcp.mcp_bridge.get_prompt(
        "objection_handling",
        {"objection_type": "price", "context": "Enterprise deal, $100k ARR"},
    )
    logger.info(f"Prompt generated with {len(prompt_result.messages)} messages")
    logger.info(f"First 200 chars: {prompt_result.messages[0].content[:200]}...")

    # Cleanup
    await mcp.shutdown()

    logger.info("\n✓ MCP demo completed successfully")


async def demo_complete_sales_flow():
    """Demonstrate complete sales conversation flow with MCP and A2A"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO: Complete Sales Conversation Flow")
    logger.info("=" * 60)

    # Initialize everything
    registry = build_default_registry()
    executor = ToolExecutor(registry=registry)

    redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
    await redis_client.ping()

    message_bus = A2AMessageBus(redis_client)

    # Create agents
    sdr_agent = SDRAgentA2A(agent_id="sdr_flow", message_bus=message_bus)
    coach_agent = CoachAgentA2A(agent_id="coach_flow", message_bus=message_bus)
    compliance_agent = ComplianceAgentA2A(
        agent_id="compliance_flow", message_bus=message_bus
    )

    await sdr_agent.initialize()
    await coach_agent.initialize()
    await compliance_agent.initialize()

    # Simulate sales conversation
    conversation = [
        "Hi, I'm interested in your product",
        "What does it cost?",
        "That seems expensive",
        "Can you give me a discount?",
    ]

    logger.info("\n--- Simulating Sales Conversation ---")

    for i, customer_message in enumerate(conversation, 1):
        logger.info(f"\n[Turn {i}] Customer: {customer_message}")

        # Step 1: Get coaching suggestion
        coach_response = await sdr_agent.send_request(
            to_agent="coach_flow",
            action="get_suggestion",
            parameters={
                "customer_message": customer_message,
                "stage": "discovery" if i <= 2 else "objection_handling",
            },
            timeout=5.0,
        )

        suggestion = coach_response.payload.get("result", {})
        logger.info(f"  Coach: {suggestion.get('recommended_approach', 'N/A')}")

        # Step 2: Generate response
        sales_response = await sdr_agent._generate_response({
            "customer_message": customer_message,
            "coach_suggestion": suggestion,
            "stage": "discovery" if i <= 2 else "objection_handling",
        })

        # Step 3: Check compliance
        compliance_response = await sdr_agent.send_request(
            to_agent="compliance_flow",
            action="check_compliance",
            parameters={"content": sales_response["message"]},
            timeout=5.0,
        )

        compliance_result = compliance_response.payload.get("result", {})

        if compliance_result.get("compliant"):
            logger.info(f"  SDR: {sales_response['message']}")
            logger.info(f"  ✓ Compliance: OK")
        else:
            logger.info(f"  ✗ Compliance: FAILED")
            logger.info(f"    Violations: {compliance_result.get('violations', [])}")

        await asyncio.sleep(0.5)  # Simulate conversation pace

    # Final: Close deal
    logger.info("\n--- Attempting to Close Deal ---")
    close_result = await sdr_agent._close_deal({
        "deal_info": {"value": 50000, "discount": 15},
        "closing_technique": "assumptive",
    })

    if close_result.get("success"):
        logger.info(f"✓ Deal closed! Value: ${close_result['deal_value']}")
        logger.info(f"  Next steps: {close_result['next_steps']}")
    else:
        logger.info(f"✗ Deal not closed: {close_result.get('reason')}")

    # Cleanup
    await sdr_agent.shutdown()
    await coach_agent.shutdown()
    await compliance_agent.shutdown()
    await message_bus.shutdown()
    await redis_client.close()

    logger.info("\n✓ Complete sales flow demo finished")


async def main():
    """Run all demos"""
    try:
        logger.info("Starting MCP & A2A Integration Demos")
        logger.info("=" * 60)

        # Run demos
        await demo_a2a_communication()
        await demo_mcp_integration()
        await demo_complete_sales_flow()

        logger.info("\n" + "=" * 60)
        logger.info("All demos completed successfully! 🎉")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
