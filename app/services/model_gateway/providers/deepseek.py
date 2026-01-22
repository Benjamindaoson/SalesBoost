"""
DeepSeek Provider Implementation (Mock/Stub)
"""
import time
import logging
from typing import List, Dict, Any, Optional
from app.services.model_gateway.schemas import CallResult, ModelConfig, ProviderType
from app.services.model_gateway.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseProvider):
    """DeepSeek Provider (Stub - 需要真实 API key 时再实现)"""
    
    def __init__(self, config: ModelConfig, api_key: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key
        # TODO: 初始化真实 DeepSeek 客户端
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CallResult:
        """DeepSeek 聊天调用（Mock）"""
        start_time = time.time()
        
        # Mock 实现
        content = f"[DeepSeek Mock] Response to: {messages[-1]['content'][:50]}..."
        tokens_used = len(content.split()) * 1.3
        latency_ms = (time.time() - start_time) * 1000
        
        return CallResult(
            content=content,
            tokens_used=int(tokens_used),
            cost=self.estimate_cost(int(tokens_used)),
            provider=ProviderType.DEEPSEEK,
            model_name=self.config.model_name,
            latency_ms=latency_ms,
            success=True,
        )
    
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """DeepSeek 嵌入（Mock）"""
        return [[0.1] * 1024 for _ in texts]
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """DeepSeek 重排序（Mock）"""
        return [{"index": i, "score": 0.5, "text": doc} for i, doc in enumerate(documents[:top_n])]

