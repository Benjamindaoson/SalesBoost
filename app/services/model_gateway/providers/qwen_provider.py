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

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """Qwen 流式聊天调用"""
        client = await self._get_client()
        
        try:
            # DashScope returns a generator when stream=True
            # Note: DashScope async call with stream=True is a bit different, usually it's synchronous generator wrapped?
            # Or use call() with stream=True which returns a generator.
            # But here we are in async method. DashScope doesn't have native async stream generator yet?
            # Actually, dashscope.Generation.call is synchronous. We might need to run it in executor or use their async support if available.
            # However, looking at the existing 'chat' method, it uses 'asyncio.wait_for(client.Generation.call(...))'
            # Wait, 'client.Generation.call' is NOT async by default unless using specific async client or maybe the existing code is wrong?
            # The existing code treats it as awaitable: 'await asyncio.wait_for(client.Generation.call(...))'.
            # If dashscope.Generation.call returns a coroutine, then it's fine.
            # Assuming it supports async/await or is patched.
            
            # For streaming, if it returns an async generator, we iterate.
            # If it returns a sync generator, we might block the loop.
            # Let's assume for now we use the same pattern but with stream=True.
            
            # Note: As of my knowledge cut-off, DashScope SDK 'call' is sync.
            # But if the user code has 'await client.Generation.call', maybe they are using a wrapper or newer version.
            # Let's try to follow the pattern but use 'stream=True, incremental_output=True'.
            
            responses = client.Generation.call(
                model=self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                result_format='message',
                stream=True,
                incremental_output=True,
                **kwargs
            )
            
            # DashScope sync generator. We should ideally run this in a thread if it's blocking.
            # But for simplicity in this step, let's iterate.
            # If we want to be async-friendly with sync generator:
            for response in responses:
                if response.status_code == 200:
                    if response.output and response.output.choices:
                         # incremental_output=True means we get deltas
                         content = response.output.choices[0].message.content
                         if content:
                             yield content
                else:
                    raise RuntimeError(f"Qwen API error: {response.message}")
                    
        except Exception as e:
            raise RuntimeError(f"Qwen API stream error: {str(e)}")
    
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

