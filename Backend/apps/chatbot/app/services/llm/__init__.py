"""
LLM Provider abstraction layer.

This package provides an abstract interface for language model providers,
allowing the chatbot to switch between different LLM services without
changing business logic.
"""

import logging
from typing import Optional

from .base import (
    LLMProvider,
    LLMProviderError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMInvalidRequestError,
    LLMTimeoutError,
    LLMProviderUnavailableError,
)
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "LLMConnectionError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMInvalidRequestError",
    "LLMTimeoutError",
    "LLMProviderUnavailableError",
    "OpenAIProvider",
    "GeminiProvider",
    "create_llm_provider",
    "get_llm_provider",
]


def create_llm_provider(
    provider_name: str,
    api_key: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> LLMProvider:
    """
    Factory function to create an LLM provider instance based on configuration.
    
    This function allows easy switching between different LLM providers
    (OpenAI, Gemini, etc.) without code changes, using only environment
    variable configuration.
    
    Args:
        provider_name: Name of the provider ("openai" or "gemini")
        api_key: API key for the provider
        model: Model name (provider-specific, uses defaults if None)
        max_tokens: Default max tokens for generation (uses provider defaults if None)
        temperature: Default temperature for generation (uses provider defaults if None)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        
    Returns:
        LLMProvider instance configured for the specified provider
        
    Raises:
        ValueError: If provider_name is not supported
        LLMProviderError: If provider initialization fails
        
    Example:
        >>> from app.core.config import settings
        >>> provider = create_llm_provider(
        ...     provider_name=settings.LLM_PROVIDER,
        ...     api_key=settings.OPENAI_API_KEY,
        ...     model=settings.OPENAI_MODEL,
        ...     max_tokens=settings.OPENAI_MAX_TOKENS,
        ...     temperature=settings.OPENAI_TEMPERATURE
        ... )
    """
    provider_name_lower = provider_name.lower().strip()
    
    logger.info(f"Creating LLM provider: {provider_name_lower}")
    
    try:
        if provider_name_lower == "openai":
            # Set defaults for OpenAI if not provided
            model = model or "gpt-4o-mini"
            max_tokens = max_tokens or 500
            temperature = temperature if temperature is not None else 0.7
            
            provider = OpenAIProvider(
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            logger.info(f"OpenAI provider created successfully with model: {model}")
            return provider
            
        elif provider_name_lower == "gemini":
            # Set defaults for Gemini if not provided
            model = model or "gemini-pro"
            max_tokens = max_tokens or 500
            temperature = temperature if temperature is not None else 0.7
            
            provider = GeminiProvider(
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            logger.warning(
                f"Gemini provider created (placeholder only - not yet implemented). "
                f"Model: {model}"
            )
            return provider
            
        else:
            error_msg = (
                f"Unsupported LLM provider: '{provider_name}'. "
                f"Supported providers: 'openai', 'gemini'"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
            
    except ValueError:
        # Re-raise ValueError for unsupported providers
        raise
    except Exception as e:
        error_msg = f"Failed to create LLM provider '{provider_name}': {e}"
        logger.error(error_msg, exc_info=True)
        raise LLMProviderError(error_msg) from e


def get_llm_provider() -> LLMProvider:
    """
    Get an LLM provider instance configured from application settings.
    
    This is a convenience function that reads configuration from the
    settings object and creates the appropriate LLM provider.
    
    Returns:
        LLMProvider instance configured from settings
        
    Raises:
        ValueError: If provider configuration is invalid
        LLMProviderError: If provider initialization fails
        
    Example:
        >>> provider = get_llm_provider()
        >>> response = await provider.generate("Hello, how are you?")
    """
    from ...core.config import settings
    
    # Validate that API key is configured
    if not settings.OPENAI_API_KEY and settings.LLM_PROVIDER.lower() == "openai":
        error_msg = "OPENAI_API_KEY not configured in settings"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Create provider from settings
    return create_llm_provider(
        provider_name=settings.LLM_PROVIDER,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE
    )
