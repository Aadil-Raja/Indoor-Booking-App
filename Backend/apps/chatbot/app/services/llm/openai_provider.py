"""
OpenAI LLM Provider implementation.

This module implements the LLMProvider interface using the OpenAI API.
It includes retry logic with exponential backoff and token counting.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncIterator
from openai import AsyncOpenAI, OpenAIError, APIError, RateLimitError, APIConnectionError, AuthenticationError, APITimeoutError
import tiktoken

from app.services.llm.base import (
    LLMProvider,
    LLMProviderError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMInvalidRequestError,
    LLMTimeoutError,
    LLMProviderUnavailableError
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider interface.
    
    Features:
    - Async API calls using OpenAI SDK
    - Retry logic with exponential backoff (3 retries)
    - Token counting using tiktoken
    - Comprehensive error handling and mapping
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model name (e.g., "gpt-4o-mini", "gpt-4")
            max_tokens: Default max tokens for generation
            temperature: Default temperature for generation
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        # Initialize AsyncOpenAI client with only supported parameters
        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=0  # We handle retries ourselves
        )
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            logger.warning(f"Model {model} not found in tiktoken, using cl100k_base encoding")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        logger.info(f"OpenAIProvider initialized with model: {model}")
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a text completion for the given prompt.
        
        Implements retry logic with exponential backoff for resilience.
        
        Args:
            prompt: The input prompt text
            max_tokens: Maximum number of tokens to generate (uses default if None)
            temperature: Sampling temperature (uses default if None)
            **kwargs: Additional OpenAI-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            LLMProviderError subclasses for various error conditions
        """
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"OpenAI generate attempt {attempt + 1}/{self.max_retries}",
                    extra={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "prompt_length": len(prompt)
                    }
                )
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                content = response.choices[0].message.content
                
                # Log token usage
                if response.usage:
                    logger.info(
                        "OpenAI generate completed",
                        extra={
                            "model": self.model,
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    )
                
                return content
                
            except AuthenticationError as e:
                logger.error(f"OpenAI authentication failed: {e}")
                raise LLMAuthenticationError(f"Authentication failed: {e}") from e
                
            except RateLimitError as e:
                logger.warning(f"OpenAI rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                raise LLMRateLimitError(f"Rate limit exceeded after {self.max_retries} retries: {e}") from e
                
            except APIConnectionError as e:
                logger.warning(f"OpenAI connection error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                raise LLMConnectionError(f"Connection failed after {self.max_retries} retries: {e}") from e
                
            except APITimeoutError as e:
                logger.warning(f"OpenAI timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                raise LLMTimeoutError(f"Request timed out after {self.max_retries} retries: {e}") from e
                
            except APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if e.status_code and 500 <= e.status_code < 600:
                    # Server error - retry
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff_delay(attempt)
                        logger.info(f"Retrying after {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    raise LLMProviderUnavailableError(f"Service unavailable after {self.max_retries} retries: {e}") from e
                else:
                    # Client error - don't retry
                    raise LLMInvalidRequestError(f"Invalid request: {e}") from e
                    
            except OpenAIError as e:
                logger.error(f"Unexpected OpenAI error: {e}")
                raise LLMProviderError(f"OpenAI error: {e}") from e
                
            except Exception as e:
                logger.error(f"Unexpected error in OpenAI generate: {e}")
                raise LLMProviderError(f"Unexpected error: {e}") from e
    
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
            max_tokens: Maximum number of tokens to generate (uses default if None)
            temperature: Sampling temperature (uses default if None)
            **kwargs: Additional OpenAI-specific parameters
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            LLMProviderError subclasses for various error conditions
        """
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        
        try:
            logger.debug(
                "OpenAI stream started",
                extra={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "prompt_length": len(prompt)
                }
            )
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("OpenAI stream completed", extra={"model": self.model})
            
        except AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}") from e
            
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit hit: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}") from e
            
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise LLMConnectionError(f"Connection failed: {e}") from e
            
        except APITimeoutError as e:
            logger.error(f"OpenAI timeout: {e}")
            raise LLMTimeoutError(f"Request timed out: {e}") from e
            
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            if e.status_code and 500 <= e.status_code < 600:
                raise LLMProviderUnavailableError(f"Service unavailable: {e}") from e
            else:
                raise LLMInvalidRequestError(f"Invalid request: {e}") from e
                
        except OpenAIError as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            raise LLMProviderError(f"OpenAI error: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI stream: {e}")
            raise LLMProviderError(f"Unexpected error: {e}") from e
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Uses tiktoken for accurate token counting based on the model's tokenizer.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
            
        Raises:
            LLMProviderError: Error counting tokens
        """
        try:
            tokens = self.tokenizer.encode(text)
            token_count = len(tokens)
            
            logger.debug(
                f"Token count: {token_count}",
                extra={"text_length": len(text), "token_count": token_count}
            )
            
            return token_count
            
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            raise LLMProviderError(f"Token counting failed: {e}") from e
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: retry_delay * (2 ^ attempt)
        # attempt 0: 1s, attempt 1: 2s, attempt 2: 4s
        delay = self.retry_delay * (2 ** attempt)
        logger.debug(f"Calculated backoff delay: {delay}s for attempt {attempt}")
        return delay
