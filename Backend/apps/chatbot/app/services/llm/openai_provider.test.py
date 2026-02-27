"""
Unit tests for OpenAIProvider.

Tests the OpenAI LLM provider implementation including:
- Text generation
- Streaming
- Token counting
- Retry logic
- Error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from openai import RateLimitError, APIConnectionError, AuthenticationError, APITimeoutError, APIError

from .openai_provider import OpenAIProvider
from .base import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMProviderUnavailableError,
    LLMInvalidRequestError,
    LLMProviderError
)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    with patch('Backend.apps.chatbot.app.services.llm.openai_provider.AsyncOpenAI') as mock:
        yield mock


@pytest.fixture
def provider(mock_openai_client):
    """Create an OpenAIProvider instance with mocked client."""
    return OpenAIProvider(
        api_key="test-key",
        model="gpt-4o-mini",
        max_tokens=100,
        temperature=0.7,
        max_retries=3,
        retry_delay=0.1  # Short delay for tests
    )


@pytest.mark.asyncio
async def test_generate_success(provider, mock_openai_client):
    """Test successful text generation."""
    # Mock response
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Generated response"))]
    mock_response.usage = Mock(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15
    )
    
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Test
    result = await provider.generate("Test prompt")
    
    assert result == "Generated response"
    provider.client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_with_custom_params(provider, mock_openai_client):
    """Test generation with custom parameters."""
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await provider.generate(
        "Test prompt",
        max_tokens=200,
        temperature=0.5
    )
    
    assert result == "Response"
    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs['max_tokens'] == 200
    assert call_args.kwargs['temperature'] == 0.5


@pytest.mark.asyncio
async def test_generate_authentication_error(provider):
    """Test authentication error handling."""
    provider.client.chat.completions.create = AsyncMock(
        side_effect=AuthenticationError("Invalid API key", response=Mock(), body=None)
    )
    
    with pytest.raises(LLMAuthenticationError):
        await provider.generate("Test prompt")


@pytest.mark.asyncio
async def test_generate_rate_limit_retry(provider):
    """Test retry logic on rate limit error."""
    # Fail twice, then succeed
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Success after retry"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    provider.client.chat.completions.create = AsyncMock(
        side_effect=[
            RateLimitError("Rate limit", response=Mock(), body=None),
            RateLimitError("Rate limit", response=Mock(), body=None),
            mock_response
        ]
    )
    
    result = await provider.generate("Test prompt")
    
    assert result == "Success after retry"
    assert provider.client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_generate_rate_limit_exhausted(provider):
    """Test rate limit error after max retries."""
    provider.client.chat.completions.create = AsyncMock(
        side_effect=RateLimitError("Rate limit", response=Mock(), body=None)
    )
    
    with pytest.raises(LLMRateLimitError):
        await provider.generate("Test prompt")
    
    assert provider.client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_generate_connection_error_retry(provider):
    """Test retry logic on connection error."""
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Success"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    provider.client.chat.completions.create = AsyncMock(
        side_effect=[
            APIConnectionError(request=Mock()),
            mock_response
        ]
    )
    
    result = await provider.generate("Test prompt")
    
    assert result == "Success"
    assert provider.client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_timeout_error(provider):
    """Test timeout error handling."""
    provider.client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=Mock())
    )
    
    with pytest.raises(LLMTimeoutError):
        await provider.generate("Test prompt")


@pytest.mark.asyncio
async def test_generate_server_error_retry(provider):
    """Test retry on server error (5xx)."""
    mock_error = APIError("Server error", response=Mock(), body=None)
    mock_error.status_code = 503
    
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Success"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    provider.client.chat.completions.create = AsyncMock(
        side_effect=[mock_error, mock_response]
    )
    
    result = await provider.generate("Test prompt")
    assert result == "Success"


@pytest.mark.asyncio
async def test_generate_client_error_no_retry(provider):
    """Test no retry on client error (4xx)."""
    mock_error = APIError("Bad request", response=Mock(), body=None)
    mock_error.status_code = 400
    
    provider.client.chat.completions.create = AsyncMock(side_effect=mock_error)
    
    with pytest.raises(LLMInvalidRequestError):
        await provider.generate("Test prompt")
    
    # Should not retry on client errors
    assert provider.client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_stream_success(provider):
    """Test successful streaming."""
    # Mock streaming response
    async def mock_stream():
        chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))]),
        ]
        for chunk in chunks:
            yield chunk
    
    provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())
    
    result = []
    async for chunk in provider.stream("Test prompt"):
        result.append(chunk)
    
    assert result == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_stream_error(provider):
    """Test streaming error handling."""
    provider.client.chat.completions.create = AsyncMock(
        side_effect=RateLimitError("Rate limit", response=Mock(), body=None)
    )
    
    with pytest.raises(LLMRateLimitError):
        async for _ in provider.stream("Test prompt"):
            pass


def test_count_tokens(provider):
    """Test token counting."""
    text = "Hello, world! This is a test."
    token_count = provider.count_tokens(text)
    
    # Should return a positive integer
    assert isinstance(token_count, int)
    assert token_count > 0


def test_count_tokens_empty(provider):
    """Test token counting with empty string."""
    token_count = provider.count_tokens("")
    assert token_count == 0


def test_backoff_delay_calculation(provider):
    """Test exponential backoff calculation."""
    assert provider._calculate_backoff_delay(0) == 0.1  # 0.1 * 2^0
    assert provider._calculate_backoff_delay(1) == 0.2  # 0.1 * 2^1
    assert provider._calculate_backoff_delay(2) == 0.4  # 0.1 * 2^2


@pytest.mark.asyncio
async def test_generate_uses_default_params(provider):
    """Test that default parameters are used when not specified."""
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    await provider.generate("Test prompt")
    
    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs['max_tokens'] == 100  # default
    assert call_args.kwargs['temperature'] == 0.7  # default
