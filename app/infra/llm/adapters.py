import os
import json
import logging
from typing import List, Dict, Optional, Any
from app.infra.gateway.schemas import ModelConfig
from app.infra.llm.interfaces import LLMAdapter
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str = None, provider_name: str = "openai"):
        self._provider_name = provider_name
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> str:
        try:
            payload = {
                "model": config.model_name,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }
            if tools:
                payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

            response = await self.client.chat.completions.create(**payload)
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls and not message.content:
                return json.dumps(
                    {
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                            for tc in tool_calls
                        ]
                    },
                    ensure_ascii=True,
                )
            return message.content
        except Exception as e:
            logger.error(f"{self.provider_name} call failed: {e}")
            raise e

    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ):
        try:
            payload = {
                "model": config.model_name,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream": True,
            }
            if tools:
                payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

            stream = await self.client.chat.completions.create(**payload)
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"{self.provider_name} stream failed: {e}")
            raise e

    async def health_check(self) -> bool:
        try:
            # Minimal call to check connectivity
            await self.client.models.list()
            return True
        except Exception:
            return False

class GeminiAdapter(LLMAdapter):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._model_name = "gemini-2.0-flash"

    @property
    def provider_name(self) -> str:
        return "google"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> str:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.model_name or self._model_name}:generateContent?key={self._api_key}"
        
        # Combine system prompt and user prompt for Gemini
        prompt_text = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_text += f"System: {content}\n\n"
            else:
                prompt_text += f"User: {content}\n\n"
            
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text.strip()}]
            }],
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API Error: {response.text}")
            data = response.json()
            try:
                return data['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                raise RuntimeError("Invalid Gemini response format")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ):
        # Gemini REST streaming is complex (SSE). 
        # For now, we fall back to non-streaming or assume SiliconFlow is used for streaming as per legacy code.
        # We will yield the full response as a single chunk for compatibility.
        content = await self.chat(messages, config)
        yield content

    async def health_check(self) -> bool:
        return True

class AdapterFactory:
    _adapters: Dict[str, LLMAdapter] = {}

    @classmethod
    def get_adapter(cls, provider: str) -> LLMAdapter:
        if provider in cls._adapters:
            return cls._adapters[provider]
        
        # Lazy initialization
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
            cls._adapters[provider] = OpenAIAdapter(api_key)
        elif provider == "deepseek":
            # Using SiliconFlow for DeepSeek models
            api_key = os.getenv("SILICONFLOW_API_KEY")
            if not api_key:
                raise ValueError("SILICONFLOW_API_KEY environment variable is required for deepseek provider")
            base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
            cls._adapters[provider] = OpenAIAdapter(api_key, base_url, provider_name="siliconflow")
        elif provider == "siliconflow":
             # Explicit SiliconFlow provider
            api_key = os.getenv("SILICONFLOW_API_KEY")
            if not api_key:
                raise ValueError("SILICONFLOW_API_KEY environment variable is required for siliconflow provider")
            base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
            cls._adapters[provider] = OpenAIAdapter(api_key, base_url, provider_name="siliconflow")
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY", "dummy-key")
            cls._adapters[provider] = GeminiAdapter(api_key)
        elif provider == "anthropic":
            # Mock for now
            cls._adapters[provider] = GeminiAdapter("dummy") 
            
        return cls._adapters.get(provider)
