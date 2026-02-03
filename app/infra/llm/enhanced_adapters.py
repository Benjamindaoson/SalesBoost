"""
Enhanced LLM Adapters with Function Calling Support
"""
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.infra.llm.interfaces import LLMAdapter
from app.infra.gateway.schemas import ModelConfig

logger = logging.getLogger(__name__)


class EnhancedOpenAIAdapter(LLMAdapter):
    """OpenAI Adapter with Function Calling support"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """
        Chat with optional tool calling

        Returns:
            str: Normal text response
            OR
            dict: {"type": "tool_calls", "tool_calls": [...], "message": {...}}
        """
        params = {
            "model": config.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**params)
        message = response.choices[0].message

        # Check for tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ],
                "message": message.model_dump()
            }

        # Normal text response
        return message.content

    async def stream(self, messages: List[Dict[str, str]], config: ModelConfig):
        """Streaming not needed for this implementation"""
        raise NotImplementedError("Use chat() instead")

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except:
            return False


class AdapterFactory:
    """Factory for creating LLM adapters"""

    @staticmethod
    def get_adapter(provider: str, **kwargs) -> LLMAdapter:
        """Get adapter for provider"""
        if provider.lower() in ["openai", "deepseek"]:
            return EnhancedOpenAIAdapter(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")
