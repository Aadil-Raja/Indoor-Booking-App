"""
Unit tests for greeting handler node.

This module tests the greeting_handler node to ensure it correctly:
- Initializes flow_state when conversation begins (Requirement 10.1)
- Initializes bot_memory when conversation begins (Requirement 10.2)
- Sets up conversation context for subsequent nodes (Requirement 10.3)
- Differentiates between new and returning users
- Generates appropriate contextual greetings
- Sets response fields correctly in the state
- Does NOT make routing decisions (intent detection handles that)
"""

import pytest
from datetime import datetime

from .greeting import greeting_handler, _is_returning_user
from ..state.conversation_state import ConversationState


@pytest.mark.asyncio
async def test_greeting_handler_new_user():
    """Test greeting handler for a new user with no conversation history."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert - Verify state initialization (Requirements 10.1, 10.2)
    assert result["flow_state"] is not None
    assert isinstance(result["flow_state"], dict)
    assert "current_intent" in result["flow_state"]
    assert "context" in result["flow_state"]
    
    assert result["bot_memory"] is not None
    assert isinstance(result["bot_memory"], dict)
    assert "conversation_history" in result["bot_memory"]
    assert "user_preferences" in result["bot_memory"]
    assert "inferred_information" in result["bot_memory"]
    
    # Assert - Verify greeting response
    assert result["response_content"] is not None
    assert len(result["response_content"]) > 0
    assert result["response_type"] == "text"
    assert result["response_metadata"] == {}
    
    # Verify new user greeting content
    assert "Hello" in result["response_content"] or "Hi" in result["response_content"]
    assert "sports booking assistant" in result["response_content"] or "booking assistant" in result["response_content"]
    assert "help you find" in result["response_content"] or "help you" in result["response_content"]


@pytest.mark.asyncio
async def test_greeting_handler_returning_user_with_history():
    """Test greeting handler for a returning user with conversation history."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hi again",
        "flow_state": {},
        "bot_memory": {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-10T10:00:00Z"
                },
                {
                    "role": "assistant",
                    "content": "Hi! How can I help?",
                    "timestamp": "2024-01-10T10:00:02Z"
                },
                {
                    "role": "user",
                    "content": "Hi again",
                    "timestamp": "2024-01-10T11:00:00Z"
                }
            ]
        },
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert - Verify state initialization even for returning users
    assert result["flow_state"] is not None
    assert isinstance(result["flow_state"], dict)
    
    assert result["bot_memory"] is not None
    assert isinstance(result["bot_memory"], dict)
    assert "conversation_history" in result["bot_memory"]
    
    # Assert - Verify greeting response
    assert result["response_content"] is not None
    assert len(result["response_content"]) > 0
    assert result["response_type"] == "text"
    assert result["response_metadata"] == {}
    
    # Verify returning user greeting content
    assert "Welcome back" in result["response_content"]


@pytest.mark.asyncio
async def test_greeting_handler_returning_user_with_preferences():
    """Test greeting handler for a returning user with sport preferences."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "I want to book a tennis court",
                    "timestamp": "2024-01-10T10:00:00Z"
                }
            ],
            "user_preferences": {
                "preferred_sport": "tennis",
                "preferred_time_of_day": "afternoon"
            }
        },
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert
    assert result["response_content"] is not None
    assert "Welcome back" in result["response_content"]
    assert "tennis" in result["response_content"]


@pytest.mark.asyncio
async def test_greeting_handler_returning_user_with_search_context():
    """Test greeting handler for a returning user with previous search results."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hi",
        "flow_state": {},
        "bot_memory": {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Show me tennis courts",
                    "timestamp": "2024-01-10T10:00:00Z"
                }
            ],
            "context": {
                "last_search_results": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "223e4567-e89b-12d3-a456-426614174001"
                ]
            }
        },
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert
    assert result["response_content"] is not None
    assert "Welcome back" in result["response_content"]
    assert "previous search" in result["response_content"] or "continue" in result["response_content"]


@pytest.mark.asyncio
async def test_greeting_handler_preserves_other_state_fields():
    """Test that greeting handler doesn't modify unrelated state fields."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hello",
        "flow_state": {"some_key": "some_value"},
        "bot_memory": {"some_data": "preserved"},
        "messages": [{"role": "user", "content": "test"}],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert - verify other fields are preserved
    assert result["chat_id"] == state["chat_id"]
    assert result["user_id"] == state["user_id"]
    assert result["owner_profile_id"] == state["owner_profile_id"]
    assert result["user_message"] == state["user_message"]
    # Note: flow_state and bot_memory may be initialized/updated
    assert result["messages"] == state["messages"]
    assert result["intent"] == state["intent"]


@pytest.mark.asyncio
async def test_greeting_handler_initializes_empty_flow_state():
    """Test that greeting handler initializes flow_state when empty (Requirement 10.1)."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hello",
        "flow_state": {},  # Empty flow_state
        "bot_memory": {},
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert - Verify flow_state is initialized with proper structure
    assert result["flow_state"] is not None
    assert isinstance(result["flow_state"], dict)
    assert "current_intent" in result["flow_state"]
    assert "property_id" in result["flow_state"]
    assert "court_id" in result["flow_state"]
    assert "date" in result["flow_state"]
    assert "time_slot" in result["flow_state"]
    assert "booking_step" in result["flow_state"]
    assert "owner_properties" in result["flow_state"]
    assert "context" in result["flow_state"]


@pytest.mark.asyncio
async def test_greeting_handler_initializes_empty_bot_memory():
    """Test that greeting handler initializes bot_memory when empty (Requirement 10.2)."""
    # Arrange
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {},  # Empty bot_memory
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Act
    result = await greeting_handler(state)
    
    # Assert - Verify bot_memory is initialized with proper structure
    assert result["bot_memory"] is not None
    assert isinstance(result["bot_memory"], dict)
    assert "conversation_history" in result["bot_memory"]
    assert "user_preferences" in result["bot_memory"]
    assert "inferred_information" in result["bot_memory"]
    assert "context" in result["bot_memory"]
    assert isinstance(result["bot_memory"]["conversation_history"], list)
    assert isinstance(result["bot_memory"]["user_preferences"], dict)
    assert isinstance(result["bot_memory"]["inferred_information"], dict)
    assert isinstance(result["bot_memory"]["context"], dict)


def test_is_returning_user_with_conversation_history():
    """Test _is_returning_user returns True when conversation history exists."""
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-10T10:00:00Z"},
            {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-10T10:00:02Z"}
        ]
    }
    
    assert _is_returning_user(bot_memory) is True


def test_is_returning_user_with_session_metadata():
    """Test _is_returning_user returns True when session metadata indicates previous messages."""
    bot_memory = {
        "conversation_history": [],
        "session_metadata": {
            "total_messages": 5
        }
    }
    
    assert _is_returning_user(bot_memory) is True


def test_is_returning_user_with_search_context():
    """Test _is_returning_user returns True when previous search results exist."""
    bot_memory = {
        "conversation_history": [],
        "context": {
            "last_search_results": ["123e4567-e89b-12d3-a456-426614174000"]
        }
    }
    
    assert _is_returning_user(bot_memory) is True


def test_is_returning_user_with_user_preferences():
    """Test _is_returning_user returns True when user preferences exist."""
    bot_memory = {
        "conversation_history": [],
        "user_preferences": {
            "preferred_sport": "tennis"
        }
    }
    
    assert _is_returning_user(bot_memory) is True


def test_is_returning_user_new_user():
    """Test _is_returning_user returns False for a new user with empty bot_memory."""
    bot_memory = {}
    
    assert _is_returning_user(bot_memory) is False


def test_is_returning_user_single_message():
    """Test _is_returning_user returns False when only current greeting exists."""
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-10T10:00:00Z"}
        ]
    }
    
    assert _is_returning_user(bot_memory) is False
