"""
MCP Adapters for SalesBoost

Adapters to convert SalesBoost components to MCP format.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.mcp.protocol import (
    MCPPrompt,
    MCPPromptArgument,
    MCPPromptMessage,
    MCPPromptResult,
    MCPResource,
    MCPResourceContent,
    MCPTool,
    MCPToolResult,
    ResourceType,
)
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """
    Adapter to convert SalesBoost tools to MCP tools

    Converts tools from ToolRegistry to MCP tool format.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry

    def to_mcp_tools(
        self, agent_type: Optional[str] = None, include_disabled: bool = False
    ) -> List[MCPTool]:
        """
        Convert tools to MCP format

        Args:
            agent_type: Filter by agent type
            include_disabled: Include disabled tools

        Returns:
            List of MCP tools
        """
        tools = self.registry.list_tools(agent_type, include_disabled)
        mcp_tools = []

        for tool in tools:
            try:
                mcp_tool = self._convert_tool(tool)
                mcp_tools.append(mcp_tool)
            except Exception as e:
                logger.error(f"Error converting tool {tool.name}: {e}")

        return mcp_tools

    def _convert_tool(self, tool: BaseTool) -> MCPTool:
        """Convert a single tool to MCP format"""
        # Get tool schema
        schema = tool.schema()

        # Extract input schema
        input_schema = {
            "type": "object",
            "properties": schema.get("parameters", {}).get("properties", {}),
            "required": schema.get("parameters", {}).get("required", []),
        }

        # Create MCP tool
        return MCPTool(
            name=tool.name,
            description=tool.description or f"Tool: {tool.name}",
            inputSchema=input_schema,
            metadata={
                "allowed_agents": tool.allowed_agents or [],
                "enabled": tool.enabled,
                "category": getattr(tool, "category", "general"),
            },
        )


class MCPRAGAdapter:
    """
    Adapter to expose RAG knowledge base as MCP resources

    Exposes knowledge base content via MCP resource protocol.
    """

    def __init__(self, rag_service):
        """
        Initialize RAG adapter

        Args:
            rag_service: RAG service instance with retrieve() method
        """
        self.rag_service = rag_service

    def get_resources(self) -> List[MCPResource]:
        """Get list of available knowledge resources"""
        return [
            MCPResource(
                uri="salesboost://knowledge/{topic}",
                name="Sales Knowledge Base",
                description="Query the sales knowledge base for information",
                mimeType=ResourceType.JSON.value,
                metadata={
                    "type": "knowledge",
                    "searchable": True,
                },
            ),
            MCPResource(
                uri="salesboost://knowledge/search",
                name="Knowledge Search",
                description="Search the knowledge base",
                mimeType=ResourceType.JSON.value,
                metadata={
                    "type": "search",
                },
            ),
        ]

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """
        Read knowledge resource

        Args:
            uri: Resource URI (e.g., salesboost://knowledge/pricing)

        Returns:
            Resource content
        """
        if not uri.startswith("salesboost://knowledge/"):
            raise ValueError(f"Invalid knowledge URI: {uri}")

        # Extract topic from URI
        topic = uri.replace("salesboost://knowledge/", "")

        if not topic or topic == "search":
            raise ValueError("Topic is required for knowledge query")

        # Query RAG service
        try:
            results = await self.rag_service.retrieve(
                query=topic, top_k=5, filters={}
            )

            # Format results
            content = {
                "topic": topic,
                "results": [
                    {
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0),
                        "metadata": result.get("metadata", {}),
                    }
                    for result in results
                ],
            }

            return MCPResourceContent(
                uri=uri,
                mimeType=ResourceType.JSON.value,
                text=json.dumps(content, indent=2),
                metadata={"result_count": len(results)},
            )

        except Exception as e:
            logger.error(f"Error reading knowledge resource: {e}")
            raise


class MCPProfileAdapter:
    """
    Adapter to expose user profiles as MCP resources

    Exposes user profile data via MCP resource protocol.
    """

    def __init__(self, profile_service):
        """
        Initialize profile adapter

        Args:
            profile_service: Profile service with get_profile() method
        """
        self.profile_service = profile_service

    def get_resources(self) -> List[MCPResource]:
        """Get list of available profile resources"""
        return [
            MCPResource(
                uri="salesboost://profile/{user_id}",
                name="User Profile",
                description="Get user profile information",
                mimeType=ResourceType.JSON.value,
                metadata={
                    "type": "profile",
                },
            ),
        ]

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """
        Read profile resource

        Args:
            uri: Resource URI (e.g., salesboost://profile/user_123)

        Returns:
            Resource content
        """
        if not uri.startswith("salesboost://profile/"):
            raise ValueError(f"Invalid profile URI: {uri}")

        # Extract user_id from URI
        user_id = uri.replace("salesboost://profile/", "")

        if not user_id:
            raise ValueError("User ID is required")

        # Get profile
        try:
            profile = await self.profile_service.get_profile(user_id)

            if not profile:
                raise ValueError(f"Profile not found: {user_id}")

            return MCPResourceContent(
                uri=uri,
                mimeType=ResourceType.JSON.value,
                text=json.dumps(profile, indent=2),
                metadata={"user_id": user_id},
            )

        except Exception as e:
            logger.error(f"Error reading profile resource: {e}")
            raise


class MCPPromptAdapter:
    """
    Adapter to expose sales prompts as MCP prompts

    Provides sales scenario templates via MCP prompt protocol.
    """

    def __init__(self, prompt_templates: Optional[Dict[str, Any]] = None):
        """
        Initialize prompt adapter

        Args:
            prompt_templates: Dictionary of prompt templates
        """
        self.templates = prompt_templates or self._get_default_templates()

    def _get_default_templates(self) -> Dict[str, Any]:
        """Get default sales prompt templates"""
        return {
            "objection_handling": {
                "description": "Generate objection handling response",
                "arguments": [
                    MCPPromptArgument(
                        name="objection_type",
                        description="Type of objection (price, timing, authority, need)",
                        required=True,
                    ),
                    MCPPromptArgument(
                        name="context",
                        description="Additional context about the situation",
                        required=False,
                    ),
                ],
                "template": """You are a sales expert. Help handle this customer objection:

Objection Type: {objection_type}
Context: {context}

Provide a professional, empathetic response that:
1. Acknowledges the concern
2. Reframes the objection
3. Provides value-based reasoning
4. Asks a follow-up question""",
            },
            "discovery_questions": {
                "description": "Generate discovery questions for a prospect",
                "arguments": [
                    MCPPromptArgument(
                        name="industry",
                        description="Prospect's industry",
                        required=True,
                    ),
                    MCPPromptArgument(
                        name="role",
                        description="Prospect's role/title",
                        required=True,
                    ),
                    MCPPromptArgument(
                        name="pain_points",
                        description="Known pain points",
                        required=False,
                    ),
                ],
                "template": """Generate 5 insightful discovery questions for:

Industry: {industry}
Role: {role}
Known Pain Points: {pain_points}

Questions should:
1. Uncover business challenges
2. Understand decision-making process
3. Identify budget and timeline
4. Reveal success criteria
5. Build rapport""",
            },
            "value_proposition": {
                "description": "Create a value proposition",
                "arguments": [
                    MCPPromptArgument(
                        name="product",
                        description="Product/service name",
                        required=True,
                    ),
                    MCPPromptArgument(
                        name="customer_needs",
                        description="Customer's specific needs",
                        required=True,
                    ),
                ],
                "template": """Create a compelling value proposition for:

Product: {product}
Customer Needs: {customer_needs}

Include:
1. Clear problem statement
2. Unique solution
3. Quantifiable benefits
4. Differentiation from competitors""",
            },
            "closing_technique": {
                "description": "Suggest closing techniques",
                "arguments": [
                    MCPPromptArgument(
                        name="sales_stage",
                        description="Current sales stage",
                        required=True,
                    ),
                    MCPPromptArgument(
                        name="buying_signals",
                        description="Observed buying signals",
                        required=False,
                    ),
                ],
                "template": """Recommend closing techniques for:

Sales Stage: {sales_stage}
Buying Signals: {buying_signals}

Provide:
1. Recommended closing technique
2. Exact wording to use
3. Timing considerations
4. Fallback options""",
            },
        }

    def get_prompts(self) -> List[MCPPrompt]:
        """Get list of available prompts"""
        prompts = []

        for name, config in self.templates.items():
            prompt = MCPPrompt(
                name=name,
                description=config["description"],
                arguments=config["arguments"],
                metadata={"category": "sales"},
            )
            prompts.append(prompt)

        return prompts

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> MCPPromptResult:
        """
        Get prompt with filled arguments

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt result with messages
        """
        if name not in self.templates:
            raise ValueError(f"Prompt not found: {name}")

        template_config = self.templates[name]
        template = template_config["template"]
        args = arguments or {}

        # Fill template
        try:
            filled_prompt = template.format(**args)
        except KeyError as e:
            raise ValueError(f"Missing required argument: {e}")

        # Create prompt result
        return MCPPromptResult(
            messages=[
                MCPPromptMessage(role="user", content=filled_prompt)
            ],
            metadata={
                "prompt_name": name,
                "arguments": args,
            },
        )
