"""
Mock Provider - 用于测试
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.schemas import ModelConfig


class MockProvider(BaseProvider):
    """Mock Provider - 模拟 API 调用"""
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """模拟聊天调用"""
        # 模拟延迟
        await asyncio.sleep(0.1)
        
        # 生成模拟回复
        last_message = messages[-1]["content"] if messages else ""
        mock_content = f"[Mock Response] You said: {last_message[:50]}..."
        
        # 模拟 token 使用
        prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        completion_tokens = len(mock_content) // 4
        
        return {
            "content": mock_content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "model": self.config.model,
            "finish_reason": "stop",
        }
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """模拟嵌入"""
        await asyncio.sleep(0.05)
        # 返回固定维度（1536，类似 OpenAI ada-002）
        return [[0.1] * 1536 for _ in texts]
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """模拟重排序（返回原顺序）"""
        await asyncio.sleep(0.05)
        return [
            {"index": i, "score": 0.8 - i * 0.1, "text": doc}
            for i, doc in enumerate(documents[:top_n])
        ]

