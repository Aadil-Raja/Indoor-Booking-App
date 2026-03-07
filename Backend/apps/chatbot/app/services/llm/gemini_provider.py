"""
Gemini LLM Provider placeholder implementation.

This module provides a placeholder implementation of the LLMProvider interface
for Google's Gemini API. This is a stub implementation that raises
NotImplementedError for all methods, allowing the codebase to reference
GeminiProvider without breaking while clearly indicating it's not yet implemented.

Future Implementation Notes:
- Use the google-generativeai SDK for API integration
- Implement retry logic with exponential backoff (similar to OpenAIProvider)
- Add token counting using Gemini's token counting API
- Map Gemini-specific exceptions to standardized LLMProviderError subclasses
- Support both text generation and streaming responses
- Configure model selection (e.g., gemini-pro, gemini-pro-vision)
- Handle Gemini-specific parameters (safety_settings, generation_config, etc.)

Requirements: 7.6
"""

import logging
from typing import Optional, Dict, Any, AsyncIterator

from .base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Placeholder implementation of the LLMProvider interface for Google Gemini.
    
    This class provides stub methods that raise NotImplementedError to clearly
    indicate that Gemini integration is not yet available. The placeholder
    allows the codebase to reference GeminiProvider in configuration and
    dependency injection without causing import errors.
    
    Future implementation will include:
    - Async API calls using google-generativeai SDK
    - Retry logic with exponential backoff
    - Token counting using Gemini's API
    - Comprehensive error handling and mapping
    - Support for streaming responses
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-pro",
        max_tokens: int = 500,
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Gemini provider placeholder.
        
        Args:
            api_key: Google API key for Gemini
            model: Model name (e.g., "gemini-pro", "gemini-pro-vision")
            max_tokens: Default max tokens for generation
            temperature: Default temperature for generation
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            
        Note:
            This is a placeholder implementation. Initialization succeeds but
            all methods will raise NotImplementedError when called.
        """
        self.api_key = api_key
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.warning(
            f"GeminiProvider initialized as placeholder - not yet implemented. "
            f"Model: {model}"
        )
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a text completion for the given prompt.
        
        Args:
            prompt: The input prompt text
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Gemini-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            NotImplementedError: This method is not yet implemented
        """
        logger.error("GeminiProvider.generate() called but not implemented")
        raise NotImplementedError(
            "GeminiProvider is a placeholder and not yet implemented. "
            "Please use OpenAIProvider or implement Gemini integration."
        )
    
    async def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Generate a streaming text completion for the given prompt.
        
        Args:
            prompt: The input prompt text
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Gemini-specific parameters
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            NotImplementedError: This method is not yet implemented
        """
        logger.error("GeminiProvider.stream() called but not implemented")
        raise NotImplementedError(
            "GeminiProvider is a placeholder and not yet implemented. "
            "Please use OpenAIProvider or implement Gemini integration."
        )
        # Make this an async generator to satisfy the type signature
        yield  # This line will never be reached due to the raise above
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
            
        Raises:
            NotImplementedError: This method is not yet implemented
        """
        logger.error("GeminiProvider.count_tokens() called but not implemented")
        raise NotImplementedError(
            "GeminiProvider is a placeholder and not yet implemented. "
            "Please use OpenAIProvider or implement Gemini integration."
        )
