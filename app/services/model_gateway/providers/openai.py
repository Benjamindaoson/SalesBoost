"""
OpenAI Provider Implementation
"""
import time
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.services.model_gateway.schemas import CallResult, ModelConfig, ProviderType
from app.services.model_gateway.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI Provider"""
    
    def __init__(self, config: ModelConfig, api_key: Optional[str] = None):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CallResult:
        """OpenAI 聊天调用"""
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            latency_ms = (time.time() - start_time) * 1000
            
            return CallResult(
                content=content,
                tokens_used=tokens_used,
                cost=self.estimate_cost(tokens_used),
                provider=ProviderType.OPENAI,
                model_name=self.config.model_name,
                latency_ms=latency_ms,
                success=True,
            )
        except Exception as e:
            logger.error(f"OpenAI chat failed: {e}")
            return CallResult(
                content="",
                tokens_used=0,
                cost=0.0,
                provider=ProviderType.OPENAI,
                model_name=self.config.model_name,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e),
            )
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """OpenAI 嵌入"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",  # 默认使用小模型
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embed failed: {e}")
            # 返回零向量作为降级
            return [[0.0] * 1536 for _ in texts]
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """OpenAI 重排序（使用 text-embedding-3-small + 余弦相似度）"""
        # 简化实现：使用嵌入 + 余弦相似度
        try:
            query_embedding = (await self.embed([query]))[0]
            doc_embeddings = await self.embed(documents)
            
            # 计算余弦相似度
            import numpy as np
            scores = []
            for i, doc_emb in enumerate(doc_embeddings):
                similarity = np.dot(query_embedding, doc_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
                )
                scores.append({
                    "index": i,
                    "score": float(similarity),
                    "text": documents[i],
                })
            
            # 排序并返回 top_n
            scores.sort(key=lambda x: x["score"], reverse=True)
            return scores[:top_n]
        except Exception as e:
            logger.error(f"OpenAI rerank failed: {e}")
            # 降级：返回原顺序
            return [{"index": i, "score": 0.5, "text": doc} for i, doc in enumerate(documents[:top_n])]

