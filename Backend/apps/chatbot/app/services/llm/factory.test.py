"""
Unit tests for LLM provider factory function.

Tests the factory function's ability to create different provider instances
based on configuration without requiring actual API keys or network access.
"""

import pytest
from unittest.mock import patch, Mock

from . import create_llm_provider
from .base import LLMProvider, LLMProviderError
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider


@pytest.fixture
def mock_openai_init():
    """Mock OpenAIProvider initialization."""
    with patch('Backend.apps.chatbot.app.services.llm.openai_provider.AsyncOpenAI'):
        yield


@pytest.fixture
def mock_tiktoken():
    """Mock tiktoken for token counting."""
    with patch('Backend.apps.chatbot.app.services.llm.openai_provider.tiktoken') as mock:
        mock.encoding_for_model.return_value = Mock()
        mock.get_encoding.return_value = Mock()
        yield mock


def test_create_openai_provider_with_defaults(mock_openai_init, mock_tiktoken):
    """Test creating OpenAI provider with default parameters."""
    provider = create_llm_provider(
        provider_name="openai",
        api_key="test-key"
    )
    
    assert isinstance(provider, OpenAIProvider)
    assert isinstance(provider, LLMProvider)
    assert provider.model == "gpt-4o-mini"
    assert provider.default_max_tokens == 500
    assert provider.default_temperature == 0.7


def test_create_openai_provider_with_custom_params(mock_openai_init, mock_tiktoken):
    """Test creating OpenAI provider with custom parameters."""
    provider = create_llm_provider(
        provider_name="openai",
        api_key="test-key",
        model="gpt-4",
        max_tokens=1000,
        temperature=0.5,
        max_retries=5,
        retry_delay=2.0
    )
    
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4"
    assert provider.default_max_tokens == 1000
    assert provider.default_temperature == 0.5
    assert provider.max_retries == 5
    assert provider.retry_delay == 2.0


def test_create_openai_provider_case_insensitive(mock_openai_init, mock_tiktoken):
    """Test that provider name is case insensitive."""
    providers = [
        create_llm_provider("openai", "test-key"),
        create_llm_provider("OPENAI", "test-key"),
        create_llm_provider("OpenAI", "test-key"),
        create_llm_provider("  openai  ", "test-key"),  # with whitespace
    ]
    
    for provider in providers:
        assert isinstance(provider, OpenAIProvider)


def test_create_gemini_provider_with_defaults():
    """Test creating Gemini provider with default parameters."""
    provider = create_llm_provider(
        provider_name="gemini",
        api_key="test-key"
    )
    
    assert isinstance(provider, GeminiProvider)
    assert isinstance(provider, LLMProvider)
    assert provider.model == "gemini-pro"
    assert provider.default_max_tokens == 500
    assert provider.default_temperature == 0.7


def test_create_gemini_provider_with_custom_params():
    """Test creating Gemini provider with custom parameters."""
    provider = create_llm_provider(
        provider_name="gemini",
        api_key="test-key",
        model="gemini-pro-vision",
        max_tokens=2000,
        temperature=0.9
    )
    
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-pro-vision"
    assert provider.default_max_tokens == 2000
    assert provider.default_temperature == 0.9


def test_create_gemini_provider_case_insensitive():
    """Test that Gemini provider name is case insensitive."""
    providers = [
        create_llm_provider("gemini", "test-key"),
        create_llm_provider("GEMINI", "test-key"),
        create_llm_provider("Gemini", "test-key"),
    ]
    
    for provider in providers:
        assert isinstance(provider, GeminiProvider)


def test_unsupported_provider_raises_value_error():
    """Test that unsupported provider name raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        create_llm_provider("unsupported-provider", "test-key")
    
    assert "Unsupported LLM provider" in str(exc_info.value)
    assert "unsupported-provider" in str(exc_info.value)


def test_empty_provider_name_raises_value_error():
    """Test that empty provider name raises ValueError."""
    with pytest.raises(ValueError):
        create_llm_provider("", "test-key")


def test_provider_initialization_error_wrapped(mock_tiktoken):
    """Test that provider initialization errors are wrapped in LLMProviderError."""
    with patch('Backend.apps.chatbot.app.services.llm.openai_provider.AsyncOpenAI') as mock_client:
        mock_client.side_effect = Exception("Initialization failed")
        
        with pytest.raises(LLMProviderError) as exc_info:
            create_llm_provider("openai", "test-key")
        
        assert "Failed to create LLM provider" in str(exc_info.value)


def test_temperature_zero_is_preserved(mock_openai_init, mock_tiktoken):
    """Test that temperature=0.0 is preserved (not treated as None)."""
    provider = create_llm_provider(
        provider_name="openai",
        api_key="test-key",
        temperature=0.0
    )
    
    assert provider.default_temperature == 0.0


def test_factory_returns_llm_provider_interface(mock_openai_init, mock_tiktoken):
    """Test that factory returns objects implementing LLMProvider interface."""
    openai_provider = create_llm_provider("openai", "test-key")
    gemini_provider = create_llm_provider("gemini", "test-key")
    
    # Both should implement the LLMProvider interface
    assert isinstance(openai_provider, LLMProvider)
    assert isinstance(gemini_provider, LLMProvider)
    
    # Both should have the required methods
    assert hasattr(openai_provider, 'generate')
    assert hasattr(openai_provider, 'stream')
    assert hasattr(openai_provider, 'count_tokens')
    
    assert hasattr(gemini_provider, 'generate')
    assert hasattr(gemini_provider, 'stream')
    assert hasattr(gemini_provider, 'count_tokens')


def test_factory_with_all_optional_params(mock_openai_init, mock_tiktoken):
    """Test factory with all optional parameters specified."""
    provider = create_llm_provider(
        provider_name="openai",
        api_key="test-key",
        model="gpt-4-turbo",
        max_tokens=2048,
        temperature=0.3,
        max_retries=5,
        retry_delay=2.5
    )
    
    assert provider.model == "gpt-4-turbo"
    assert provider.default_max_tokens == 2048
    assert provider.default_temperature == 0.3
    assert provider.max_retries == 5
    assert provider.retry_delay == 2.5
