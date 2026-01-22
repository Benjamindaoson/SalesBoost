"""
DeepSeek Provider
"""
import asyncio
from typing import List, Dict, Any, Optional
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.schemas import ModelConfig


class DeepSeekProvider(BaseProvider):
    """DeepSeek Provider"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    async def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                # DeepSeek 兼容 OpenAI API
                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url or "https://api.deepseek.com",
                )
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """DeepSeek 聊天调用"""
        client = await self._get_client()
        
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    **kwargs
                ),
                timeout=self.config.timeout
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
            }
        except asyncio.TimeoutError:
            raise TimeoutError(f"DeepSeek API timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"DeepSeek API error: {str(e)}")
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """DeepSeek 嵌入调用（如果支持）"""
        # DeepSeek 可能不支持 embedding，使用 OpenAI 兼容接口或降级
        # 这里先 stub，实际使用时需要确认
        raise NotImplementedError("DeepSeek embedding not yet implemented")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """DeepSeek 重排序（stub）"""
        # 返回原顺序
        return [
            {"index": i, "score": 0.8, "text": doc}
            for i, doc in enumerate(documents[:top_n])
        ]

