"""
Real Anthropic Adapter

使用官方anthropic SDK实现真实的Claude API调用

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from ...infra.gateway.schemas import ModelConfig
from ...infra.llm.interfaces import LLMAdapter

logger = logging.getLogger(__name__)


class AnthropicAdapter(LLMAdapter):
    """
    Anthropic (Claude) API Adapter

    使用官方anthropic SDK调用Claude API

    Supported models:
    - claude-3-5-sonnet-20241022 (recommended)
    - claude-3-opus-20240229
    - claude-3-sonnet-20240229
    - claude-3-haiku-20240307
    """

    def __init__(self, api_key: str):
        """
        Initialize Anthropic adapter

        Args:
            api_key: Anthropic API key (starts with 'sk-ant-')

        Raises:
            ValueError: If API key is invalid
        """
        if not api_key:
            raise ValueError("Anthropic API key is required")

        if api_key in ["dummy-key", "your-key-here", "changeme"]:
            raise ValueError(
                f"Invalid Anthropic API key: {api_key}. "
                "Get your API key from: https://console.anthropic.com/"
            )

        self.client = AsyncAnthropic(api_key=api_key)
        self._provider_name = "anthropic"

        logger.info("AnthropicAdapter initialized successfully")

    @property
    def provider_name(self) -> str:
        """Provider name"""
        return self._provider_name

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> str:
        """
        Send chat completion request to Claude

        Args:
            messages: List of message dicts with 'role' and 'content'
            config: Model configuration
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice strategy

        Returns:
            Response text or tool calls JSON

        Raises:
            Exception: If API call fails
        """
        try:
            # Extract system message if present
            system_message = None
            anthropic_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Build request parameters
            request_params = {
                "model": config.model_name,
                "messages": anthropic_messages,
                "max_tokens": config.max_tokens or 4096,
                "temperature": config.temperature,
            }

            # Add system message if present
            if system_message:
                request_params["system"] = system_message

            # Add tools if provided
            if tools:
                # Convert OpenAI-style tools to Anthropic format
                anthropic_tools = self._convert_tools_to_anthropic_format(tools)
                request_params["tools"] = anthropic_tools

                if tool_choice:
                    request_params["tool_choice"] = self._convert_tool_choice(tool_choice)

            # Make API call
            response = await self.client.messages.create(**request_params)

            # Handle response
            if response.stop_reason == "tool_use":
                # Extract tool calls
                tool_calls = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_calls.append({
                            "id": content_block.id,
                            "name": content_block.name,
                            "arguments": json.dumps(content_block.input),
                        })

                return json.dumps({"tool_calls": tool_calls})

            else:
                # Extract text response
                text_content = ""
                for content_block in response.content:
                    if content_block.type == "text":
                        text_content += content_block.text

                return text_content

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    def _convert_tools_to_anthropic_format(
        self,
        openai_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style tools to Anthropic format

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {...}
            }
        }

        Anthropic format:
        {
            "name": "get_weather",
            "description": "Get weather",
            "input_schema": {...}
        }
        """
        anthropic_tools = []

        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })

        return anthropic_tools

    def _convert_tool_choice(self, openai_tool_choice: Any) -> Dict[str, Any]:
        """
        Convert OpenAI tool_choice to Anthropic format

        OpenAI: "auto", "none", {"type": "function", "function": {"name": "..."}}
        Anthropic: {"type": "auto"}, {"type": "any"}, {"type": "tool", "name": "..."}
        """
        if openai_tool_choice == "auto":
            return {"type": "auto"}
        elif openai_tool_choice == "none":
            return {"type": "auto"}  # Anthropic doesn't have "none", use "auto"
        elif isinstance(openai_tool_choice, dict):
            if openai_tool_choice.get("type") == "function":
                func_name = openai_tool_choice["function"]["name"]
                return {"type": "tool", "name": func_name}

        return {"type": "auto"}  # Default

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ):
        """
        Stream chat completion (for future implementation)

        Args:
            messages: List of messages
            config: Model configuration
            tools: Optional tools
            tool_choice: Optional tool choice

        Yields:
            Response chunks
        """
        # TODO: Implement streaming
        raise NotImplementedError("Streaming not yet implemented for Anthropic adapter")
