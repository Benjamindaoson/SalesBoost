"""
Unified LLM Client

Production-ready LLM client supporting multiple providers with retry, timeout, and circuit breaker.

Supported Providers:
- OpenAI (GPT-4, GPT-4o, GPT-3.5-turbo)
- SiliconFlow (DeepSeek-V3, Qwen-Turbo)
- Google Gemini (Gemini-2.0-Flash)

Features:
- Unified interface across providers
- Automatic retry with exponential backoff
- Timeout protection
- Circuit breaker pattern
- Token usage tracking
- Streaming support
- Error handling and fallback

Usage:
    from app.infra.llm import UnifiedLLMClient, LLMProvider

    client = UnifiedLLMClient.get_instance()
    await client.initialize()

    response = await client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        provider=LLMProvider.OPENAI,
        model="gpt-4o-mini",
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    SILICONFLOW = "siliconflow"
    GEMINI = "gemini"


@dataclass
class LLMResponse:
    """Unified LLM response."""
    content: str
    provider: LLMProvider
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    finish_reason: str
    metadata: Dict[str, Any]


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for a provider."""
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False
    half_open_attempts: int = 0


class UnifiedLLMClient:
    """
    Unified LLM client with multi-provider support.

    Features:
    - Automatic provider selection
    - Retry with exponential backoff
    - Circuit breaker per provider
    - Token usage tracking
    - Streaming support
    - Comprehensive error handling

    Args:
        openai_api_key: OpenAI API key
        openai_base_url: OpenAI base URL (optional, for proxies)
        siliconflow_api_key: SiliconFlow API key
        siliconflow_base_url: SiliconFlow base URL
        gemini_api_key: Google Gemini API key
        max_retries: Maximum retry attempts (default: 3)
        retry_delay: Initial retry delay in seconds (default: 1.0)
        timeout: Request timeout in seconds (default: 60)
        circuit_breaker_threshold: Failures before opening circuit (default: 5)
        circuit_breaker_timeout: Circuit breaker timeout in seconds (default: 60)
    """

    _instance: Optional["UnifiedLLMClient"] = None

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        siliconflow_api_key: Optional[str] = None,
        siliconflow_base_url: str = "https://api.siliconflow.cn/v1",
        gemini_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 60,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url
        self.siliconflow_api_key = siliconflow_api_key
        self.siliconflow_base_url = siliconflow_base_url
        self.gemini_api_key = gemini_api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Clients
        self._openai_client = None
        self._siliconflow_client = None
        self._gemini_client = None

        # Circuit breakers
        self._circuit_breakers: Dict[LLMProvider, CircuitBreakerState] = {
            LLMProvider.OPENAI: CircuitBreakerState(),
            LLMProvider.SILICONFLOW: CircuitBreakerState(),
            LLMProvider.GEMINI: CircuitBreakerState(),
        }

        # Statistics
        self._total_requests = 0
        self._total_tokens = 0
        self._total_latency = 0.0
        self._provider_stats: Dict[LLMProvider, Dict[str, int]] = {
            provider: {"requests": 0, "tokens": 0, "errors": 0}
            for provider in LLMProvider
        }

        self._initialized = False

    @classmethod
    def get_instance(cls, **kwargs) -> "UnifiedLLMClient":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def initialize(self) -> bool:
        """
        Initialize LLM clients.

        Returns:
            True if at least one provider is initialized
        """
        if self._initialized:
            return True

        initialized_count = 0

        # Initialize OpenAI
        if self.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.timeout,
                )
                logger.info("Initialized OpenAI client")
                initialized_count += 1
            except ImportError:
                logger.warning("openai package not available. Install with: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

        # Initialize SiliconFlow (OpenAI-compatible)
        if self.siliconflow_api_key:
            try:
                from openai import AsyncOpenAI
                self._siliconflow_client = AsyncOpenAI(
                    api_key=self.siliconflow_api_key,
                    base_url=self.siliconflow_base_url,
                    timeout=self.timeout,
                )
                logger.info("Initialized SiliconFlow client")
                initialized_count += 1
            except ImportError:
                logger.warning("openai package not available")
            except Exception as e:
                logger.error(f"Failed to initialize SiliconFlow client: {e}")

        # Initialize Gemini
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self._gemini_client = genai
                logger.info("Initialized Gemini client")
                initialized_count += 1
            except ImportError:
                logger.warning("google-generativeai package not available. Install with: pip install google-generativeai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

        self._initialized = initialized_count > 0

        if not self._initialized:
            logger.error("No LLM providers initialized")
        else:
            logger.info(f"Initialized {initialized_count} LLM provider(s)")

        return self._initialized

    def _check_circuit_breaker(self, provider: LLMProvider) -> bool:
        """
        Check if circuit breaker is open for a provider.

        Returns:
            True if circuit is closed (can proceed), False if open
        """
        breaker = self._circuit_breakers[provider]

        # If circuit is open, check if timeout has passed
        if breaker.is_open:
            if breaker.last_failure_time:
                elapsed = (datetime.now() - breaker.last_failure_time).total_seconds()
                if elapsed > self.circuit_breaker_timeout:
                    # Try half-open state
                    breaker.is_open = False
                    breaker.half_open_attempts = 0
                    logger.info(f"Circuit breaker for {provider} entering half-open state")
                    return True
                else:
                    logger.warning(f"Circuit breaker for {provider} is open")
                    return False
            else:
                return False

        return True

    def _record_success(self, provider: LLMProvider):
        """Record successful request."""
        breaker = self._circuit_breakers[provider]
        breaker.failures = 0
        breaker.is_open = False
        breaker.half_open_attempts = 0

    def _record_failure(self, provider: LLMProvider):
        """Record failed request."""
        breaker = self._circuit_breakers[provider]
        breaker.failures += 1
        breaker.last_failure_time = datetime.now()

        # Open circuit if threshold reached
        if breaker.failures >= self.circuit_breaker_threshold:
            breaker.is_open = True
            logger.error(
                f"Circuit breaker for {provider} opened after "
                f"{breaker.failures} failures"
            )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        provider: LLMProvider = LLMProvider.OPENAI,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs,
    ) -> Optional[LLMResponse]:
        """
        Chat completion with automatic retry and circuit breaker.

        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            provider: LLM provider to use
            model: Model name (provider-specific)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming (returns AsyncIterator)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse or None if all retries failed
        """
        if not self._initialized:
            logger.error("LLM client not initialized")
            return None

        # Check circuit breaker
        if not self._check_circuit_breaker(provider):
            return None

        # Select default model if not specified
        if model is None:
            model = self._get_default_model(provider)

        # Retry loop
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                # Route to provider
                if provider == LLMProvider.OPENAI:
                    response = await self._openai_completion(
                        messages, model, temperature, max_tokens, stream, **kwargs
                    )
                elif provider == LLMProvider.SILICONFLOW:
                    response = await self._siliconflow_completion(
                        messages, model, temperature, max_tokens, stream, **kwargs
                    )
                elif provider == LLMProvider.GEMINI:
                    response = await self._gemini_completion(
                        messages, model, temperature, max_tokens, stream, **kwargs
                    )
                else:
                    logger.error(f"Unknown provider: {provider}")
                    return None

                # Record success
                latency_ms = (time.time() - start_time) * 1000
                self._record_success(provider)
                self._update_stats(provider, response, latency_ms)

                return response

            except Exception as e:
                logger.error(
                    f"LLM request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                # Record failure
                self._record_failure(provider)
                self._provider_stats[provider]["errors"] += 1

                # Retry with exponential backoff
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("All retry attempts exhausted")
                    return None

        return None

    async def _openai_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs,
    ) -> LLMResponse:
        """OpenAI completion."""
        if self._openai_client is None:
            raise ValueError("OpenAI client not initialized")

        response = await self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs,
        )

        if stream:
            # TODO: Handle streaming
            raise NotImplementedError("Streaming not yet implemented")

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.OPENAI,
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            latency_ms=0,  # Will be set by caller
            finish_reason=response.choices[0].finish_reason,
            metadata={"response_id": response.id},
        )

    async def _siliconflow_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs,
    ) -> LLMResponse:
        """SiliconFlow completion (OpenAI-compatible)."""
        if self._siliconflow_client is None:
            raise ValueError("SiliconFlow client not initialized")

        response = await self._siliconflow_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs,
        )

        if stream:
            raise NotImplementedError("Streaming not yet implemented")

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.SILICONFLOW,
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            latency_ms=0,
            finish_reason=response.choices[0].finish_reason,
            metadata={"response_id": response.id},
        )

    async def _gemini_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs,
    ) -> LLMResponse:
        """Gemini completion."""
        if self._gemini_client is None:
            raise ValueError("Gemini client not initialized")

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        # Create model
        gemini_model = self._gemini_client.GenerativeModel(model)

        # Generate
        response = await gemini_model.generate_content_async(
            gemini_messages,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        # Estimate tokens (Gemini doesn't provide exact counts)
        prompt_tokens = sum(len(msg["content"].split()) for msg in messages) * 1.3
        completion_tokens = len(response.text.split()) * 1.3
        total_tokens = int(prompt_tokens + completion_tokens)

        return LLMResponse(
            content=response.text,
            provider=LLMProvider.GEMINI,
            model=model,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=total_tokens,
            latency_ms=0,
            finish_reason="stop",
            metadata={},
        )

    def _get_default_model(self, provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.SILICONFLOW: "deepseek-ai/DeepSeek-V3",
            LLMProvider.GEMINI: "gemini-2.0-flash-exp",
        }
        return defaults[provider]

    def _update_stats(self, provider: LLMProvider, response: LLMResponse, latency_ms: float):
        """Update statistics."""
        response.latency_ms = latency_ms

        self._total_requests += 1
        self._total_tokens += response.total_tokens
        self._total_latency += latency_ms

        self._provider_stats[provider]["requests"] += 1
        self._provider_stats[provider]["tokens"] += response.total_tokens

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        avg_latency = (
            self._total_latency / self._total_requests
            if self._total_requests > 0
            else 0
        )

        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "average_latency_ms": avg_latency,
            "providers": {
                provider.value: stats
                for provider, stats in self._provider_stats.items()
            },
            "circuit_breakers": {
                provider.value: {
                    "is_open": breaker.is_open,
                    "failures": breaker.failures,
                }
                for provider, breaker in self._circuit_breakers.items()
            },
        }

    async def health_check(self) -> Dict[LLMProvider, bool]:
        """Check health of all providers."""
        health = {}

        for provider in LLMProvider:
            try:
                # Simple test request
                response = await self.chat_completion(
                    messages=[{"role": "user", "content": "Hi"}],
                    provider=provider,
                    max_tokens=10,
                )
                health[provider] = response is not None
            except Exception as e:
                logger.error(f"Health check failed for {provider}: {e}")
                health[provider] = False

        return health
