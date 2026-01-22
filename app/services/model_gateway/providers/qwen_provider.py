"""
Qwen Provider (阿里云通义千问)
"""
import asyncio
from typing import List, Dict, Any, Optional
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.schemas import ModelConfig


class QwenProvider(BaseProvider):
    """Qwen Provider - 使用 DashScope API"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    async def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                import dashscope
                dashscope.api_key = self.config.api_key
                self._client = dashscope
            except ImportError:
                raise ImportError("dashscope package not installed. Install with: pip install dashscope")
        return self._client
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Qwen 聊天调用"""
        client = await self._get_client()
        
        try:
            response = await asyncio.wait_for(
                client.Generation.call(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    **kwargs
                ),
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Qwen API error: {response.message}")
            
            return {
                "content": response.output.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                "model": self.config.model,
                "finish_reason": "stop",
            }
        except asyncio.TimeoutError:
            raise TimeoutError(f"Qwen API timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"Qwen API error: {str(e)}")
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Qwen 嵌入调用"""
        client = await self._get_client()
        
        try:
            response = await asyncio.wait_for(
                client.embeddings.call(
                    model="text-embedding-v2",
                    input=texts,
                ),
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Qwen Embedding error: {response.message}")
            
            return [item.embedding for item in response.output.embeddings]
        except asyncio.TimeoutError:
            raise TimeoutError(f"Qwen Embedding timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"Qwen Embedding error: {str(e)}")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Qwen 重排序（使用 embedding 相似度）"""
        query_embedding = await self.embed([query])
        doc_embeddings = await self.embed(documents)
        
        # 计算余弦相似度
        import numpy as np
        scores = []
        for i, doc_emb in enumerate(doc_embeddings):
            score = np.dot(query_embedding[0], doc_emb) / (
                np.linalg.norm(query_embedding[0]) * np.linalg.norm(doc_emb)
            )
            scores.append({"index": i, "score": float(score), "text": documents[i]})
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_n]

