"""
Unit tests for intent detection node.

This module tests the intent_detection node's ability to classify user messages
into the correct intents using both rule-based patterns and LLM fallback.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from .intent_detection import intent_detection, _rule_based_classification
from ..state.conversation_state import ConversationState
from ...services.llm.base import LLMProvider, LLMProviderError


# Test Fixtures

@pytest.fixture
def base_state() -> ConversationState:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": None,
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }


@pytest.fixture
def mock_llm_provider() -> Mock:
    """Create a mock LLM provider."""
    provider = Mock(spec=LLMProvider)
    provider.api_key = "test-api-key"
    provider.model = "gpt-4o-mini"
    provider.temperature = 0.7
    provider.max_tokens = 500
    return provider


# Rule-Based Classification Tests

class TestRuleBasedClassification:
    """Test rule-based intent classification."""
    
    def test_greeting_intent_simple(self):
        """Test simple greeting detection."""
        assert _rule_based_classification("hello") == "greeting"
        assert _rule_based_classification("hi") == "greeting"
        assert _rule_based_classification("hey") == "greeting"
    
    def test_greeting_intent_formal(self):
        """Test formal greeting detection."""
        assert _rule_based_classification("good morning") == "greeting"
        assert _rule_based_classification("good afternoon") == "greeting"
        assert _rule_based_classification("good evening") == "greeting"
    
    def test_greeting_intent_informal(self):
        """Test informal greeting detection."""
        assert _rule_based_classification("howdy") == "greeting"
        assert _rule_based_classification("hiya") == "greeting"
        assert _rule_based_classification("sup") == "greeting"
    
    def test_search_intent_explicit(self):
        """Test explicit search intent detection."""
        assert _rule_based_classification("search for tennis courts") == "search"
        assert _rule_based_classification("find basketball facilities") == "search"
        assert _rule_based_classification("show me available courts") == "search"
        assert _rule_based_classification("looking for badminton courts") == "search"
    
    def test_search_intent_questions(self):
        """Test search intent in question form."""
        assert _rule_based_classification("what facilities do you have?") == "search"
        assert _rule_based_classification("which courts are available?") == "search"
        assert _rule_based_classification("where can i find tennis courts?") == "search"
    
    def test_search_intent_sport_specific(self):
        """Test sport-specific search detection."""
        assert _rule_based_classification("tennis court near me") == "search"
        assert _rule_based_classification("basketball facility downtown") == "search"
        assert _rule_based_classification("volleyball court available") == "search"
    
    def test_booking_intent_explicit(self):
        """Test explicit booking intent detection."""
        assert _rule_based_classification("book a tennis court") == "booking"
        assert _rule_based_classification("reserve a court") == "booking"
        assert _rule_based_classification("schedule a booking") == "booking"
        assert _rule_based_classification("make a booking") == "booking"
    
    def test_booking_intent_natural(self):
        """Test natural language booking intent."""
        assert _rule_based_classification("i want to book a court") == "booking"
        assert _rule_based_classification("i'd like to reserve a facility") == "booking"
        assert _rule_based_classification("can i book a tennis court?") == "booking"
    
    def test_booking_intent_keywords(self):
        """Test booking-related keywords."""
        assert _rule_based_classification("make an appointment") == "booking"
        assert _rule_based_classification("i need a reservation") == "booking"
    
    def test_faq_intent_help(self):
        """Test FAQ intent for help requests."""
        assert _rule_based_classification("help me") == "faq"
        assert _rule_based_classification("what is the process?") == "faq"
        assert _rule_based_classification("explain the booking process") == "faq"
    
    def test_faq_intent_information(self):
        """Test FAQ intent for information requests."""
        assert _rule_based_classification("tell me about pricing") == "faq"
        assert _rule_based_classification("i have a question") == "faq"
        assert _rule_based_classification("need more information") == "faq"
    
    def test_faq_intent_pricing(self):
        """Test FAQ intent for pricing questions."""
        assert _rule_based_classification("how much does it cost?") == "faq"
        assert _rule_based_classification("what are the prices?") == "faq"
        assert _rule_based_classification("tell me about payment options") == "faq"
        assert _rule_based_classification("refund policy") == "faq"
    
    def test_unknown_intent(self):
        """Test unknown intent for ambiguous messages."""
        assert _rule_based_classification("xyz123") == "unknown"
        assert _rule_based_classification("...") == "unknown"
        assert _rule_based_classification("random text") == "unknown"
    
    def test_case_insensitive(self):
        """Test that classification is case-insensitive."""
        assert _rule_based_classification("HELLO") == "greeting"
        assert _rule_based_classification("BOOK A COURT") == "booking"
        assert _rule_based_classification("SEARCH TENNIS") == "search"
        assert _rule_based_classification("HELP") == "faq"
    
    def test_priority_booking_over_search(self):
        """Test that booking intent takes priority over search."""
        # Message contains both booking and search keywords
        message = "i want to book a tennis court, show me available ones"
        assert _rule_based_classification(message) == "booking"


# Intent Detection Node Tests

class TestIntentDetectionNode:
    """Test the intent_detection node function."""
    
    @pytest.mark.asyncio
    async def test_greeting_detection(self, base_state, mock_llm_provider):
        """Test greeting intent detection updates state correctly."""
        base_state["user_message"] = "Hello!"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "greeting"
        assert result["flow_state"]["intent"] == "greeting"
        # LLM should not be called for clear greeting
        mock_llm_provider.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_detection(self, base_state, mock_llm_provider):
        """Test search intent detection updates state correctly."""
        base_state["user_message"] = "Show me tennis courts"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "search"
        assert result["flow_state"]["intent"] == "search"
        mock_llm_provider.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_booking_detection(self, base_state, mock_llm_provider):
        """Test booking intent detection updates state correctly."""
        base_state["user_message"] = "I want to book a court"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "booking"
        assert result["flow_state"]["intent"] == "booking"
        mock_llm_provider.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_faq_detection(self, base_state, mock_llm_provider):
        """Test FAQ intent detection updates state correctly."""
        base_state["user_message"] = "How much does it cost?"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "faq"
        assert result["flow_state"]["intent"] == "faq"
        mock_llm_provider.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_llm_fallback_success(self, base_state, mock_llm_provider):
        """Test LLM fallback for ambiguous messages."""
        base_state["user_message"] = "I need something for tomorrow"
        
        # Mock the ChatOpenAI response
        mock_response = Mock()
        mock_response.content = "booking"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["intent"] == "booking"
            assert result["flow_state"]["intent"] == "booking"
            # LLM should be called for ambiguous message
            mock_create_llm.assert_called_once()
            mock_llm.ainvoke.assert_called_once()
            # Verify temperature and max_tokens were set correctly
            call_args = mock_create_llm.call_args
            assert call_args.kwargs["temperature"] == 0.0
            assert call_args.kwargs["max_tokens"] == 10
    
    @pytest.mark.asyncio
    async def test_llm_fallback_invalid_response(self, base_state, mock_llm_provider):
        """Test LLM fallback with invalid response defaults to FAQ."""
        base_state["user_message"] = "ambiguous message"
        
        # Mock the ChatOpenAI response with invalid intent
        mock_response = Mock()
        mock_response.content = "invalid_intent"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["intent"] == "faq"
            assert result["flow_state"]["intent"] == "faq"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_fallback_error(self, base_state, mock_llm_provider):
        """Test LLM fallback error handling defaults to FAQ."""
        base_state["user_message"] = "ambiguous message"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["intent"] == "faq"
            assert result["flow_state"]["intent"] == "faq"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_llm_provider(self, base_state):
        """Test behavior when no LLM provider is available."""
        base_state["user_message"] = "ambiguous message"
        
        result = await intent_detection(base_state, llm_provider=None)
        
        # Should default to FAQ when no LLM provider and no rule match
        assert result["intent"] == "faq"
        assert result["flow_state"]["intent"] == "faq"
    
    @pytest.mark.asyncio
    async def test_preserves_existing_flow_state(self, base_state, mock_llm_provider):
        """Test that intent detection preserves existing flow_state fields."""
        base_state["user_message"] = "Hello"
        base_state["flow_state"] = {
            "step": "select_property",
            "property_id": "some-uuid"
        }
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "greeting"
        assert result["flow_state"]["intent"] == "greeting"
        # Existing fields should be preserved
        assert result["flow_state"]["step"] == "select_property"
        assert result["flow_state"]["property_id"] == "some-uuid"
    
    @pytest.mark.asyncio
    async def test_handles_empty_flow_state(self, base_state, mock_llm_provider):
        """Test that intent detection handles empty flow_state."""
        base_state["user_message"] = "book a court"
        base_state["flow_state"] = {}
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "booking"
        assert result["flow_state"]["intent"] == "booking"
    
    @pytest.mark.asyncio
    async def test_typos_and_informal_language(self, base_state, mock_llm_provider):
        """Test handling of typos and informal language."""
        # Test with informal greeting
        base_state["user_message"] = "heyyy"
        result = await intent_detection(base_state, mock_llm_provider)
        assert result["intent"] == "greeting"
        
        # Test with informal booking - needs LLM fallback
        base_state["user_message"] = "wanna book a court"
        
        # Mock the ChatOpenAI response
        mock_response = Mock()
        mock_response.content = "booking"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            # Should use LLM fallback for "wanna"
            assert result["intent"] == "booking"


# Edge Cases

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_message(self, base_state, mock_llm_provider):
        """Test handling of empty message."""
        base_state["user_message"] = ""
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        # Empty message should default to FAQ
        assert result["intent"] == "faq"
    
    @pytest.mark.asyncio
    async def test_whitespace_only_message(self, base_state, mock_llm_provider):
        """Test handling of whitespace-only message."""
        base_state["user_message"] = "   \n\t  "
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "faq"
    
    @pytest.mark.asyncio
    async def test_very_long_message(self, base_state, mock_llm_provider):
        """Test handling of very long message."""
        long_message = "I want to book " + "a tennis court " * 100
        base_state["user_message"] = long_message
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        # Should still detect booking intent
        assert result["intent"] == "booking"
    
    @pytest.mark.asyncio
    async def test_mixed_intents(self, base_state, mock_llm_provider):
        """Test message with multiple intent signals."""
        # Greeting comes first in the message, so it will be detected first
        base_state["user_message"] = "Hello! I want to search for courts and book one"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        # Greeting is detected first due to pattern matching order
        # This is acceptable behavior - user can clarify intent in next message
        assert result["intent"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_booking_priority_over_search(self, base_state, mock_llm_provider):
        """Test that booking intent is prioritized over search when both present."""
        # No greeting, just booking and search keywords
        base_state["user_message"] = "I want to book and search for tennis courts"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        # Booking should be detected before search
        assert result["intent"] == "booking"
    
    @pytest.mark.asyncio
    async def test_special_characters(self, base_state, mock_llm_provider):
        """Test handling of special characters."""
        base_state["user_message"] = "book a court!!! 🎾"
        
        result = await intent_detection(base_state, mock_llm_provider)
        
        assert result["intent"] == "booking"
    
    @pytest.mark.asyncio
    async def test_llm_returns_whitespace(self, base_state, mock_llm_provider):
        """Test LLM returning whitespace is handled correctly."""
        base_state["user_message"] = "ambiguous"
        
        # Mock the ChatOpenAI response with whitespace
        mock_response = Mock()
        mock_response.content = "  search  \n"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Should strip whitespace and recognize valid intent
            assert result["intent"] == "search"
    
    @pytest.mark.asyncio
    async def test_llm_returns_uppercase(self, base_state, mock_llm_provider):
        """Test LLM returning uppercase is handled correctly."""
        base_state["user_message"] = "ambiguous"
        
        # Mock the ChatOpenAI response with uppercase
        mock_response = Mock()
        mock_response.content = "BOOKING"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Should convert to lowercase and recognize valid intent
            assert result["intent"] == "booking"
