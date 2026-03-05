"""
Unit tests for intent detection node.

This module tests the intent_detection node's ability to make LLM-driven routing
decisions by returning next_node, message, and state_updates.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
import json

from .intent_detection import intent_detection
from ..state.conversation_state import ConversationState
from ...services.llm.base import LLMProvider, LLMProviderError


# Test Fixtures

@pytest.fixture
def base_state() -> ConversationState:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
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


def create_llm_response(next_node: str, message: str, current_intent: str = None) -> str:
    """Helper to create a JSON LLM response."""
    response = {
        "next_node": next_node,
        "message": message,
        "state_updates": {
            "flow_state": {
                "current_intent": current_intent or next_node
            }
        }
    }
    return json.dumps(response)


# Intent Detection Node Tests (LLM-Based Routing)

class TestIntentDetectionNode:
    """Test the intent_detection node function with LLM-based routing decisions."""
    
    @pytest.mark.asyncio
    async def test_greeting_routing(self, base_state, mock_llm_provider):
        """Test greeting routing decision updates state correctly."""
        base_state["user_message"] = "Hello!"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("greeting", "Hello! How can I help you?")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "greeting"
            assert result["flow_state"]["current_intent"] == "greeting"
            # LLM should be called for all routing decisions
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_information_routing(self, base_state, mock_llm_provider):
        """Test information routing decision updates state correctly."""
        base_state["user_message"] = "Show me tennis courts"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("information", "Let me search for tennis courts.")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "information"
            assert result["flow_state"]["current_intent"] == "information"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_booking_routing(self, base_state, mock_llm_provider):
        """Test booking routing decision updates state correctly."""
        base_state["user_message"] = "I want to book a court"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Let's get you booked!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "booking"
            assert result["flow_state"]["current_intent"] == "booking"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_routing_success(self, base_state, mock_llm_provider):
        """Test LLM routing for ambiguous messages."""
        base_state["user_message"] = "I need something for tomorrow"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "I'll help you book for tomorrow.")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "booking"
            assert result["flow_state"]["current_intent"] == "booking"
            # LLM should be called
            mock_create_llm.assert_called_once()
            mock_llm.ainvoke.assert_called_once()
            # Verify temperature and max_tokens were set correctly
            call_args = mock_create_llm.call_args
            assert call_args.kwargs["temperature"] == 0.0
            assert call_args.kwargs["max_tokens"] == 200
    
    @pytest.mark.asyncio
    async def test_llm_invalid_json_response(self, base_state, mock_llm_provider):
        """Test LLM with invalid JSON response defaults to greeting."""
        base_state["user_message"] = "ambiguous message"
        
        # Mock the ChatOpenAI response with invalid JSON
        mock_response = Mock()
        mock_response.content = "not valid json"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "greeting"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_invalid_next_node(self, base_state, mock_llm_provider):
        """Test LLM with invalid next_node defaults to greeting."""
        base_state["user_message"] = "ambiguous message"
        
        # Mock the ChatOpenAI response with invalid next_node
        mock_response = Mock()
        mock_response.content = json.dumps({
            "next_node": "invalid_node",
            "message": "Test message",
            "state_updates": {}
        })
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Parser should default to greeting for invalid next_node
            assert result["next_node"] == "greeting"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_error(self, base_state, mock_llm_provider):
        """Test LLM error handling defaults to greeting."""
        base_state["user_message"] = "ambiguous message"
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "greeting"
            mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preserves_existing_flow_state(self, base_state, mock_llm_provider):
        """Test that routing decision preserves existing flow_state fields."""
        base_state["user_message"] = "Hello"
        base_state["flow_state"] = {
            "property_id": 123,
            "court_id": 456
        }
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("greeting", "Hello!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "greeting"
            assert result["flow_state"]["current_intent"] == "greeting"
            # Existing fields should be preserved
            assert result["flow_state"]["property_id"] == 123
            assert result["flow_state"]["court_id"] == 456
    
    @pytest.mark.asyncio
    async def test_handles_empty_flow_state(self, base_state, mock_llm_provider):
        """Test that routing decision handles empty flow_state."""
        base_state["user_message"] = "book a court"
        base_state["flow_state"] = {}
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Let's book a court!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "booking"
            assert result["flow_state"]["current_intent"] == "booking"
    
    @pytest.mark.asyncio
    async def test_typos_and_informal_language(self, base_state, mock_llm_provider):
        """Test handling of typos and informal language."""
        # Test with informal greeting
        base_state["user_message"] = "heyyy"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("greeting", "Hey there!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            assert result["next_node"] == "greeting"
        
        # Test with informal booking
        base_state["user_message"] = "wanna book a court"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Sure, let's book!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            assert result["next_node"] == "booking"


# Edge Cases

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_no_llm_provider(self, base_state):
        """Test behavior when no LLM provider is available."""
        base_state["user_message"] = "ambiguous message"
        
        result = await intent_detection(base_state, llm_provider=None)
        
        # Should default to greeting when no LLM provider
        assert result["next_node"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_empty_message(self, base_state, mock_llm_provider):
        """Test handling of empty message."""
        base_state["user_message"] = ""
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("greeting", "Hello!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Empty message should be routed by LLM
            assert result["next_node"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_whitespace_only_message(self, base_state, mock_llm_provider):
        """Test handling of whitespace-only message."""
        base_state["user_message"] = "   \n\t  "
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("greeting", "Hello!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "greeting"
    
    @pytest.mark.asyncio
    async def test_very_long_message(self, base_state, mock_llm_provider):
        """Test handling of very long message."""
        long_message = "I want to book " + "a tennis court " * 100
        base_state["user_message"] = long_message
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Let's book!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Should still detect booking routing
            assert result["next_node"] == "booking"
    
    @pytest.mark.asyncio
    async def test_mixed_intents(self, base_state, mock_llm_provider):
        """Test message with multiple intent signals."""
        base_state["user_message"] = "Hello! I want to search for courts and book one"
        
        # Mock the ChatOpenAI response - LLM should determine primary routing
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Let's book a court!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # LLM determines the primary routing
            assert result["next_node"] == "booking"
    
    @pytest.mark.asyncio
    async def test_special_characters(self, base_state, mock_llm_provider):
        """Test handling of special characters."""
        base_state["user_message"] = "book a court!!! 🎾"
        
        # Mock the ChatOpenAI response with JSON
        mock_response = Mock()
        mock_response.content = create_llm_response("booking", "Let's book!")
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            assert result["next_node"] == "booking"
    
    @pytest.mark.asyncio
    async def test_missing_next_node_in_response(self, base_state, mock_llm_provider):
        """Test LLM response missing next_node defaults to greeting."""
        base_state["user_message"] = "ambiguous"
        
        # Mock the ChatOpenAI response with missing next_node
        mock_response = Mock()
        mock_response.content = json.dumps({
            "message": "Hello",
            "state_updates": {}
            # next_node is missing
        })
        
        with patch('app.agent.nodes.intent_detection.create_langchain_llm') as mock_create_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create_llm.return_value = mock_llm
            
            result = await intent_detection(base_state, mock_llm_provider)
            
            # Should default to greeting (current_node default)
            assert result["next_node"] == "greeting"
