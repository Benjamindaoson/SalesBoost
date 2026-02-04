# MCP & A2A Integration Guide for SalesBoost

Complete guide for integrating Model Context Protocol (MCP) and Agent-to-Agent (A2A) communication into SalesBoost.

## Table of Contents

1. [Overview](#overview)
2. [MCP Integration](#mcp-integration)
3. [A2A Integration](#a2a-integration)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What is MCP?

Model Context Protocol (MCP) is Anthropic's standard protocol for connecting AI models to external tools and data sources. It provides:

- **Standardized Tool Access**: Expose and consume tools via a standard protocol
- **Resource Management**: Access external data sources (files, databases, APIs)
- **Prompt Templates**: Share reusable prompt templates
- **Interoperability**: Connect with Claude Desktop and other MCP-compatible clients

### What is A2A?

Agent-to-Agent (A2A) communication enables decentralized agent coordination:

- **Direct Messaging**: Agents communicate directly without central orchestration
- **Event Broadcasting**: Agents can broadcast events to all other agents
- **Request-Response**: Synchronous request-response pattern with timeout
- **Agent Discovery**: Agents can discover other agents by capability

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SalesBoost Application                │
├─────────────────────────────────────────────────────────┤
│  MCP Layer                    │  A2A Layer               │
│  ┌──────────┐  ┌──────────┐  │  ┌──────────────────┐   │
│  │ Server   │  │ Client   │  │  │  Message Bus     │   │
│  │ (Expose) │  │ (Consume)│  │  │  (Redis)         │   │
│  └──────────┘  └──────────┘  │  └──────────────────┘   │
│       │              │        │          │              │
├───────┼──────────────┼────────┼──────────┼──────────────┤
│       ▼              ▼        │          ▼              │
│  ┌─────────────────────────┐ │  ┌──────────────────┐   │
│  │  Tool Registry          │ │  │  A2A Agents      │   │
│  │  - Sales Tools          │ │  │  - SDR Agent     │   │
│  │  - Knowledge Base       │ │  │  - Coach Agent   │   │
│  │  - CRM Integration      │ │  │  - Compliance    │   │
│  └─────────────────────────┘ │  └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## MCP Integration

### MCP Server (Exposing SalesBoost Capabilities)

#### Starting the MCP Server

```bash
# Start MCP server with default config
python scripts/start_mcp_server.py

# Start with custom config
python scripts/start_mcp_server.py --config config/mcp_server.yaml
```

#### Exposed Capabilities

**1. Tools** - All tools from ToolRegistry:
- `knowledge_retriever`: Query sales knowledge base
- `profile_reader`: Read customer profiles
- `compliance_check`: Check compliance
- `price_calculator`: Calculate pricing
- `crm_integration`: CRM operations

**2. Resources**:
- `salesboost://knowledge/{topic}`: Knowledge base queries
- `salesboost://profile/{user_id}`: User profiles
- `salesboost://crm/{resource}`: CRM data

**3. Prompts**:
- `objection_handling`: Handle customer objections
- `discovery_questions`: Generate discovery questions
- `value_proposition`: Create value propositions
- `closing_technique`: Closing techniques

#### Using with Claude Desktop

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "salesboost": {
      "command": "python",
      "args": [
        "/path/to/SalesBoost/scripts/start_mcp_server.py"
      ]
    }
  }
}
```

### MCP Client (Consuming External Services)

#### Connecting to External MCP Servers

```python
from app.integration import MCPIntegration
from app.tools.registry import build_default_registry
from app.tools.executor import ToolExecutor

# Initialize
registry = build_default_registry()
executor = ToolExecutor(registry=registry)

mcp = MCPIntegration(
    tool_registry=registry,
    tool_executor=executor
)

# Connect to Brave Search
await mcp.connect_client(
    server_name="brave-search",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-brave-search"]
)

# Register external tools
await mcp.register_external_tools()

# Now agents can use brave-search tools
result = await executor.execute(
    name="mcp_brave-search_brave_web_search",
    payload={"query": "sales techniques 2024"},
    caller_role="sdr_agent"
)
```

#### Supported External MCP Servers

- **Brave Search**: Web search capabilities
- **Filesystem**: File operations
- **GitHub**: GitHub API access
- **PostgreSQL**: Database queries
- **Custom**: Any MCP-compatible server

---

## A2A Integration

### Starting the A2A System

```bash
# Start A2A system with all agents
python scripts/start_a2a_system.py

# Start with custom config
python scripts/start_a2a_system.py --config config/a2a.yaml
```

### Available Agents

#### 1. SDR Agent (Sales Development Representative)

**Capabilities**: `sales`, `objection_handling`, `closing`, `lead_qualification`

**Actions**:
- `generate_response`: Generate sales response
- `handle_objection`: Handle customer objection
- `qualify_lead`: Qualify a lead
- `close_deal`: Attempt to close deal

#### 2. Coach Agent

**Capabilities**: `coaching`, `feedback`, `evaluation`, `suggestion`

**Actions**:
- `get_suggestion`: Get coaching suggestion
- `evaluate_response`: Evaluate sales response
- `provide_feedback`: Provide detailed feedback
- `analyze_conversation`: Analyze entire conversation

#### 3. Compliance Agent

**Capabilities**: `compliance_check`, `risk_monitoring`, `policy_enforcement`, `audit_trail`

**Actions**:
- `check_compliance`: Check content for compliance
- `check_deal`: Check deal for compliance
- `get_violations`: Get violation history
- `get_audit_log`: Get audit log

### Agent Communication Patterns

#### Request-Response

```python
# SDR Agent requests coaching
response = await sdr_agent.send_request(
    to_agent="coach_agent_001",
    action="get_suggestion",
    parameters={
        "customer_message": "I'm not interested",
        "context": {...},
        "stage": "objection_handling"
    },
    timeout=10.0
)

suggestion = response.payload.get("result")
```

#### Event Broadcasting

```python
# SDR Agent broadcasts deal closed event
await sdr_agent.broadcast_event(
    event_type="deal_closed",
    data={
        "deal_value": 50000,
        "customer_id": "cust_123"
    }
)

# All agents receive this event
```

#### Agent Discovery

```python
# Find all agents with coaching capability
coaches = await sdr_agent.discover_agents(capability="coaching")

# Find all SDR agents
sdrs = await sdr_agent.discover_agents(agent_type="SDRAgent")
```

---

## Quick Start

### Complete Integration Example

```python
import asyncio
from app.integration import integrate_mcp_and_a2a
from app.tools.registry import build_default_registry
from app.tools.executor import ToolExecutor

async def main():
    # Build tool registry
    registry = build_default_registry()
    executor = ToolExecutor(registry=registry)

    # Integrate MCP and A2A
    mcp, a2a = await integrate_mcp_and_a2a(
        tool_registry=registry,
        tool_executor=executor,
        redis_url="redis://localhost:6379"
    )

    # Connect to external MCP server
    await mcp.connect_client(
        "brave-search",
        "npx",
        ["-y", "@modelcontextprotocol/server-brave-search"]
    )
    await mcp.register_external_tools()

    # Get agents
    sdr_agent = a2a.get_agent("sdr_agent_001")
    coach_agent = a2a.get_agent("coach_agent_001")

    # Use A2A communication
    response = await sdr_agent.send_request(
        to_agent="coach_agent_001",
        action="get_suggestion",
        parameters={
            "customer_message": "Tell me more",
            "stage": "discovery"
        }
    )

    print(f"Coach suggestion: {response.payload}")

    # Cleanup
    await mcp.shutdown()
    await a2a.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Configuration

### MCP Server Configuration

File: `config/mcp_server.yaml`

```yaml
server:
  name: salesboost-mcp
  version: 1.0.0

capabilities:
  tools: true
  resources: true
  prompts: true

tools:
  enabled: true
  source: tool_registry

resources:
  knowledge:
    enabled: true
    uri_pattern: "salesboost://knowledge/{topic}"

prompts:
  enabled: true
  builtin:
    - objection_handling
    - discovery_questions
```

### MCP Client Configuration

File: `config/mcp_client.yaml`

```yaml
servers:
  brave_search:
    enabled: true
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-brave-search"
    env:
      BRAVE_API_KEY: ${BRAVE_API_KEY}

auto_register:
  enabled: true
  tool_prefix: "mcp_"
```

### A2A Configuration

File: `config/a2a.yaml`

```yaml
message_bus:
  transport: redis
  redis:
    url: redis://localhost:6379

agents:
  sdr_agent:
    enabled: true
    capabilities:
      - sales
      - objection_handling
    auto_start: true

  coach_agent:
    enabled: true
    capabilities:
      - coaching
      - feedback
    auto_start: true
```

---

## Usage Examples

### Example 1: Sales Conversation with A2A

```python
# SDR Agent handles customer message
async def handle_customer_message(sdr_agent, message):
    # Generate response with coach help
    response = await sdr_agent.send_request(
        to_agent="coach_agent_001",
        action="get_suggestion",
        parameters={
            "customer_message": message,
            "stage": "discovery"
        }
    )

    suggestion = response.payload.get("result")

    # Generate actual response
    sales_response = await sdr_agent._generate_response({
        "customer_message": message,
        "coach_suggestion": suggestion
    })

    # Check compliance
    compliance_response = await sdr_agent.send_request(
        to_agent="compliance_agent_001",
        action="check_compliance",
        parameters={
            "content": sales_response["message"]
        }
    )

    if compliance_response.payload["result"]["compliant"]:
        return sales_response
    else:
        # Revise response
        return await revise_response(sales_response)
```

### Example 2: Using External MCP Tools

```python
# Use Brave Search via MCP
async def research_competitor(executor, competitor_name):
    result = await executor.execute(
        name="mcp_brave-search_brave_web_search",
        payload={
            "query": f"{competitor_name} pricing features 2024"
        },
        caller_role="sdr_agent"
    )

    return result["result"]
```

### Example 3: Compliance Monitoring

```python
# Compliance agent monitors all messages
class ComplianceMonitor(ComplianceAgentA2A):
    async def handle_event(self, message):
        if message.payload.get("event_type") == "response_generated":
            # Check every response
            content = message.payload["data"]["response"]["message"]

            check_result = await self._check_compliance({
                "content": content
            })

            if not check_result["compliant"]:
                # Alert the agent
                await self.send_event(
                    to_agent=message.from_agent,
                    event_type="compliance_alert",
                    data={
                        "violations": check_result["violations"],
                        "action_required": "Revise response"
                    }
                )
```

---

## API Reference

### MCP Server API

#### `SalesBoostMCPServer`

```python
server = SalesBoostMCPServer(
    name="salesboost-mcp",
    version="1.0.0",
    handler=bridge
)

await server.run()  # Start server (stdio)
```

#### `MCPBridge`

```python
bridge = MCPBridge(
    tool_registry=registry,
    tool_executor=executor,
    rag_service=rag,
    profile_service=profiles
)

tools = await bridge.list_tools()
result = await bridge.call_tool(name, arguments)
resources = await bridge.list_resources()
content = await bridge.read_resource(uri)
```

### MCP Client API

#### `MCPClientManager`

```python
client = MCPClientManager()

await client.connect(server_name, command, args)
tools = await client.list_tools(server_name)
result = await client.call_tool(server_name, tool_name, arguments)
await client.disconnect(server_name)
```

### A2A API

#### `A2AMessageBus`

```python
bus = A2AMessageBus(redis_client)

await bus.register_agent(agent_id, agent_type, capabilities)
await bus.publish(message)
await bus.subscribe(agent_id, handler)
response = await bus.request(message, timeout)
agents = await bus.discover_agents(capability)
```

#### `A2AAgent`

```python
class MyAgent(A2AAgent):
    async def handle_request(self, message):
        # Handle requests
        return {"result": "..."}

    async def handle_event(self, message):
        # Handle events
        pass

agent = MyAgent(agent_id, message_bus, capabilities)
await agent.initialize()

response = await agent.send_request(to_agent, action, parameters)
await agent.broadcast_event(event_type, data)
agents = await agent.discover_agents(capability)
```

---

## Troubleshooting

### MCP Issues

**Problem**: MCP server not responding

```bash
# Check if server is running
ps aux | grep start_mcp_server

# Check logs
tail -f logs/mcp_server.log

# Test with simple request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python scripts/start_mcp_server.py
```

**Problem**: External MCP server connection fails

```python
# Check server command
await client.connect("test", "echo", ["test"])

# Check environment variables
import os
print(os.environ.get("BRAVE_API_KEY"))
```

### A2A Issues

**Problem**: Agents not receiving messages

```bash
# Check Redis connection
redis-cli ping

# Check agent registration
redis-cli HGETALL a2a:agents

# Check message channels
redis-cli PUBSUB CHANNELS "a2a:*"
```

**Problem**: Message timeout

```python
# Increase timeout
response = await agent.send_request(
    to_agent="other_agent",
    action="slow_action",
    timeout=60.0  # Increase from default 30s
)

# Check if target agent is online
agents = await message_bus.discover_agents()
print([a.agent_id for a in agents])
```

### Performance Issues

**Problem**: High latency

```python
# Enable connection pooling for Redis
redis_client = Redis.from_url(
    redis_url,
    max_connections=50,
    decode_responses=True
)

# Use batch operations
# Instead of multiple publishes, batch them
messages = [msg1, msg2, msg3]
await asyncio.gather(*[bus.publish(msg) for msg in messages])
```

---

## Best Practices

### MCP

1. **Tool Design**: Keep tools focused and single-purpose
2. **Error Handling**: Always return proper error responses
3. **Documentation**: Provide clear tool descriptions
4. **Security**: Validate all inputs, limit resource access

### A2A

1. **Message Design**: Keep payloads small and focused
2. **Timeouts**: Set appropriate timeouts for requests
3. **Error Handling**: Handle agent unavailability gracefully
4. **Monitoring**: Log all agent communications
5. **Cleanup**: Always shutdown agents properly

---

## Next Steps

1. **Extend Agents**: Create custom agents for specific use cases
2. **Add Tools**: Integrate more external MCP servers
3. **Monitoring**: Set up Prometheus metrics
4. **Scaling**: Deploy multiple agent instances
5. **Security**: Add authentication and encryption

---

## Support

- **Documentation**: See `/docs` directory
- **Examples**: See `/examples` directory
- **Tests**: Run `pytest tests/test_mcp_integration.py tests/test_a2a_integration.py`
- **Issues**: Report at GitHub issues

---

**Version**: 1.0.0
**Last Updated**: 2026-02-04
