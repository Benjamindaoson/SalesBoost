"""
OpenAI Provider
"""
import asyncio
from typing import List, Dict, Any, Optional
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.schemas import ModelConfig, ProviderType


class OpenAIProvider(BaseProvider):
    """OpenAI Provider"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    async def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
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
        """OpenAI 聊天调用"""
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
            raise TimeoutError(f"OpenAI API timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """OpenAI 流式聊天调用"""
        client = await self._get_client()
        
        try:
            stream = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenAI API timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """OpenAI 嵌入调用"""
        client = await self._get_client()
        
        try:
            response = await asyncio.wait_for(
                client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=texts,
                ),
                timeout=self.config.timeout
            )
            
            return [item.embedding for item in response.data]
        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenAI Embedding timeout after {self.config.timeout}s")
        except Exception as e:
            raise RuntimeError(f"OpenAI Embedding error: {str(e)}")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """OpenAI 重排序（使用 text-embedding-3-large，如果可用）"""
        # OpenAI 没有专门的 rerank API，使用 embedding 相似度
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
        
        # 排序并返回 top_n
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_n]

