from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.infra.gateway.schemas import ModelConfig, RoutingContext

class LLMAdapter(ABC):
    """
    Abstract Base Class for LLM Providers.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> str:
        """
        Execute a chat completion request.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: ModelConfig,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ): # -> AsyncGenerator[str, None]
        """
        Execute a streaming chat completion request.
        Yields text chunks.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available.
        """
        pass

class RoutingStrategy(ABC):
    """
    Abstract Base Class for Routing Strategies.
    """
    
    @abstractmethod
    def select_model(self, context: RoutingContext, candidates: List[ModelConfig]) -> ModelConfig:
        """
        Select the best model based on context and candidates.
        """
        pass
