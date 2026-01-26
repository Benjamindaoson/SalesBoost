"""
Model Gateway Providers
"""
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.providers.mock import MockProvider
from app.services.model_gateway.providers.openai_provider import OpenAIProvider
from app.services.model_gateway.providers.qwen_provider import QwenProvider
from app.services.model_gateway.providers.zhipu_provider import ZhipuProvider
from app.services.model_gateway.providers.deepseek_provider import DeepSeekProvider
from app.services.model_gateway.schemas import ProviderType, ModelConfig


def create_provider(provider_type: ProviderType, config: ModelConfig) -> BaseProvider:
    """创建 Provider 实例"""
    providers = {
        ProviderType.MOCK: MockProvider,
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.QWEN: QwenProvider,
        ProviderType.ZHIPU: ZhipuProvider,
        ProviderType.DEEPSEEK: DeepSeekProvider,
    }
    
    provider_class = providers.get(provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider type: {provider_type}")
    
    return provider_class(config)
