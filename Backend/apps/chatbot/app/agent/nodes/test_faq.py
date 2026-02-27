"""
Unit tests for FAQ handler node.

This module tests the faq_handler node to ensure it correctly:
- Generates LLM responses for general questions
- Handles pricing and policy questions
- Handles unknown intents gracefully
- Falls back to generic responses when LLM is unavailable
- Tracks token usage correctly
"""

import pytest
from unittest.mock import AsyncMock, Mock

from .faq import faq_handler, _generate_fallback_response
from ..state.conversation_state import ConversationState
from ...services.llm.base import LLMProvider, LLMProviderError


@pytest.mark.asyncio
async def test_faq_handler_with_llm_provider():
    """Test FAQ handler generates LLM response when provider is available."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "Pricing varies by facility and time slot. You can see prices when searching."
    mock_llm.count_tokens.side_effect = lambda text: len(text.split())
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "How much does it cost?",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert
    assert result["response_content"] is not None
    assert len(result["response_content"]) > 0
    assert result["response_type"] == "text"
    assert result["response_metadata"] == {}
    assert result["token_usage"] is not None
    assert result["token_usage"] > 0
    
    # Verify LLM was called
    mock_llm.generate.assert_called_once()
    call_kwargs = mock_llm.generate.call_args[1]
    assert "How much does it cost?" in call_kwargs["prompt"]
    assert call_kwargs["max_tokens"] == 150
    assert call_kwargs["temperature"] == 0.7


@pytest.mark.asyncio
async def test_faq_handler_without_llm_provider():
    """Test FAQ handler uses fallback response when no LLM provider."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "How much does it cost?",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=None)
    
    # Assert
    assert result["response_content"] is not None
    assert len(result["response_content"]) > 0
    assert result["response_type"] == "text"
    assert result["response_metadata"] == {}
    
    # Verify fallback response contains helpful information
    assert "pricing" in result["response_content"].lower() or "price" in result["response_content"].lower()


@pytest.mark.asyncio
async def test_faq_handler_llm_error_fallback():
    """Test FAQ handler falls back to generic response when LLM fails."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.side_effect = LLMProviderError("API error")
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "What's the weather?",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert
    assert result["response_content"] is not None
    assert len(result["response_content"]) > 0
    assert result["response_type"] == "text"
    
    # Verify fallback response is helpful
    assert "help" in result["response_content"].lower() or "search" in result["response_content"].lower()


@pytest.mark.asyncio
async def test_faq_handler_pricing_question():
    """Test FAQ handler with pricing-related question."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "Pricing varies by facility. You can see specific prices when you search."
    mock_llm.count_tokens.side_effect = lambda text: len(text.split())
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "What are your prices for tennis courts?",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert
    assert result["response_content"] is not None
    assert "pricing" in result["response_content"].lower() or "price" in result["response_content"].lower()
    mock_llm.generate.assert_called_once()


@pytest.mark.asyncio
async def test_faq_handler_policy_question():
    """Test FAQ handler with policy-related question."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "For cancellation policies, please contact the facility directly."
    mock_llm.count_tokens.side_effect = lambda text: len(text.split())
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "What's your cancellation policy?",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert
    assert result["response_content"] is not None
    mock_llm.generate.assert_called_once()


@pytest.mark.asyncio
async def test_faq_handler_unknown_intent():
    """Test FAQ handler with completely unknown intent."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "I'm here to help you find and book sports facilities. What would you like to do?"
    mock_llm.count_tokens.side_effect = lambda text: len(text.split())
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Tell me a joke",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert
    assert result["response_content"] is not None
    mock_llm.generate.assert_called_once()


@pytest.mark.asyncio
async def test_faq_handler_preserves_other_state_fields():
    """Test that FAQ handler doesn't modify unrelated state fields."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "I can help you search for facilities."
    mock_llm.count_tokens.side_effect = lambda text: len(text.split())
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Help me",
        "flow_state": {"some_key": "some_value"},
        "bot_memory": {"some_data": "preserved"},
        "messages": [{"role": "user", "content": "test"}],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert - verify other fields are preserved
    assert result["chat_id"] == state["chat_id"]
    assert result["user_id"] == state["user_id"]
    assert result["owner_id"] == state["owner_id"]
    assert result["user_message"] == state["user_message"]
    assert result["flow_state"] == state["flow_state"]
    assert result["bot_memory"] == state["bot_memory"]
    assert result["messages"] == state["messages"]
    assert result["intent"] == state["intent"]


def test_generate_fallback_response_pricing():
    """Test fallback response for pricing questions."""
    # Act
    result = _generate_fallback_response("How much does it cost?")
    
    # Assert
    assert result["content"] is not None
    assert "pricing" in result["content"].lower() or "price" in result["content"].lower()
    assert result["token_usage"] is None


def test_generate_fallback_response_policy():
    """Test fallback response for policy questions."""
    # Act
    result = _generate_fallback_response("What's your refund policy?")
    
    # Assert
    assert result["content"] is not None
    assert "cancel" in result["content"].lower() or "refund" in result["content"].lower() or "policy" in result["content"].lower()
    assert result["token_usage"] is None


def test_generate_fallback_response_help():
    """Test fallback response for help requests."""
    # Act
    result = _generate_fallback_response("How do I use this?")
    
    # Assert
    assert result["content"] is not None
    assert "help" in result["content"].lower() or "search" in result["content"].lower()
    assert result["token_usage"] is None


def test_generate_fallback_response_unknown():
    """Test fallback response for completely unknown messages."""
    # Act
    result = _generate_fallback_response("Random message")
    
    # Assert
    assert result["content"] is not None
    assert "help" in result["content"].lower() or "search" in result["content"].lower()
    assert "sports" in result["content"].lower() or "facilities" in result["content"].lower()
    assert result["token_usage"] is None


@pytest.mark.asyncio
async def test_faq_handler_token_counting_error():
    """Test FAQ handler handles token counting errors gracefully."""
    # Arrange
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "Here's a helpful response."
    mock_llm.count_tokens.side_effect = Exception("Token counting failed")
    
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Help me",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "faq",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await faq_handler(state, llm_provider=mock_llm)
    
    # Assert - should still generate response even if token counting fails
    assert result["response_content"] == "Here's a helpful response."
    assert result["response_type"] == "text"
    # Token usage should be None when counting fails
    assert result["token_usage"] is None
