"""
Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement,
along with standardized exception classes for error handling.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator


# Exception Classes

class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMConnectionError(LLMProviderError):
    """Raised when connection to LLM service fails."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with LLM service fails."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""
    pass


class LLMInvalidRequestError(LLMProviderError):
    """Raised when request parameters are invalid."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when request times out."""
    pass


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when LLM provider service is unavailable."""
    pass


# Abstract Base Class

class LLMProvider(ABC):
    """
    Abstract base class for language model providers.
    
    All LLM provider implementations must inherit from this class
    and implement the abstract methods: generate, stream, and count_tokens.
    """
    
    @abstractmethod
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
            temperature: Sampling temperature (0.0 to 2.0)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            LLMProviderError: Base exception for provider errors
            LLMConnectionError: Connection to provider failed
            LLMAuthenticationError: Authentication failed
            LLMRateLimitError: Rate limit exceeded
            LLMInvalidRequestError: Invalid request parameters
            LLMTimeoutError: Request timed out
            LLMProviderUnavailableError: Provider service unavailable
        """
        pass
    
    @abstractmethod
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
            temperature: Sampling temperature (0.0 to 2.0)
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            LLMProviderError: Base exception for provider errors
            LLMConnectionError: Connection to provider failed
            LLMAuthenticationError: Authentication failed
            LLMRateLimitError: Rate limit exceeded
            LLMInvalidRequestError: Invalid request parameters
            LLMTimeoutError: Request timed out
            LLMProviderUnavailableError: Provider service unavailable
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
            
        Raises:
            LLMProviderError: Error counting tokens
        """
        pass
