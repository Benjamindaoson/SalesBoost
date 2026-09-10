"""
DeepSeek LLM Provider
集成 DeepSeek API 作为备用 LLM 提供商
"""

import httpx
import json
from typing import AsyncIterator, Dict, Any, List, Optional
from pydantic import BaseModel, Field

from salesagent.core.settings import settings
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class DeepSeekMessage(BaseModel):
    """DeepSeek 消息格式"""
    role: str = Field(..., description="角色: system/user/assistant")
    content: str = Field(..., description="消息内容")


class DeepSeekRequest(BaseModel):
    """DeepSeek API 请求"""
    model: str = Field(default="deepseek-v3.2", description="模型名称")
    messages: List[DeepSeekMessage] = Field(..., description="对话消息列表")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2000, ge=1, le=8000, description="最大生成 token 数")
    stream: bool = Field(default=False, description="是否流式返回")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="核采样参数")


class DeepSeekProvider:
    """DeepSeek API 提供商"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-v3.2",
        timeout: float = 60.0
    ):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.model = model
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("DeepSeek API key is required")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        logger.info(f"DeepSeek provider initialized with model: {self.model}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        非流式对话补全

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Returns:
            API 响应结果
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"DeepSeek completion successful. "
                    f"Tokens: {result.get('usage', {}).get('total_tokens', 0)}"
                )

                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"DeepSeek request failed: {str(e)}")
                raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式对话补全

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue

                logger.info("DeepSeek streaming completion finished")

            except httpx.HTTPStatusError as e:
                logger.error(f"DeepSeek streaming error: {e.response.status_code}")
                raise
            except Exception as e:
                logger.error(f"DeepSeek streaming failed: {str(e)}")
                raise

    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入（DeepSeek 可能不支持，使用 OpenAI 作为后备）

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        logger.warning("DeepSeek does not support embeddings, falling back to OpenAI")
        raise NotImplementedError("DeepSeek does not provide embedding API")

    def format_messages(
        self,
        system_prompt: Optional[str] = None,
        user_message: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        格式化消息列表

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            conversation_history: 对话历史

        Returns:
            格式化后的消息列表
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        if user_message:
            messages.append({"role": "user", "content": user_message})

        return messages


# 全局实例
_deepseek_provider: Optional[DeepSeekProvider] = None


def get_deepseek_provider() -> DeepSeekProvider:
    """获取 DeepSeek 提供商单例"""
    global _deepseek_provider

    if _deepseek_provider is None:
        _deepseek_provider = DeepSeekProvider()

    return _deepseek_provider


async def test_deepseek_connection() -> bool:
    """测试 DeepSeek API 连接"""
    try:
        provider = get_deepseek_provider()
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        return result.get("choices", [{}])[0].get("message", {}).get("content") is not None
    except Exception as e:
        logger.error(f"DeepSeek connection test failed: {str(e)}")
        return False
