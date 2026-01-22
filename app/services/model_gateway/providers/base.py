"""
Base Provider Interface
所有 Provider 必须实现此接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from app.services.model_gateway.schemas import ModelConfig, ProviderType


class BaseProvider(ABC):
    """Provider 基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.provider_type = config.provider
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天调用
        
        Returns:
            {
                "content": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
                "model": str,
                "finish_reason": str
            }
        """
        pass
    
    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """
        文本嵌入
        
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        重排序（如果 Provider 不支持，返回原顺序）
        
        Returns:
            [{"index": int, "score": float, "text": str}, ...]
        """
        pass
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """
        估算成本（美元）
        
        默认实现：基于模型名称估算
        子类可覆盖以提供精确计算
        """
        model = model or self.config.model
        # 默认定价（每 1K tokens）
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "qwen-plus": {"prompt": 0.002, "completion": 0.002},
            "qwen-turbo": {"prompt": 0.001, "completion": 0.001},
            "deepseek-chat": {"prompt": 0.0007, "completion": 0.0007},
            "text-embedding-ada-002": {"prompt": 0.0001, "completion": 0},
        }
        
        # 查找模型定价
        for model_key, prices in pricing.items():
            if model_key in model.lower():
                cost = (prompt_tokens / 1000 * prices["prompt"] + 
                       completion_tokens / 1000 * prices["completion"])
                return cost
        
        # 默认：使用 GPT-3.5 定价
        return (prompt_tokens / 1000 * 0.0015 + completion_tokens / 1000 * 0.002)
