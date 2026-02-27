"""
Tests for basic flow nodes.

This module tests the foundational LangGraph nodes that handle
basic conversation flow: receive_message, load_chat, and append_user_message.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from .basic_nodes import receive_message, load_chat, append_user_message
from ..state.conversation_state import ConversationState


class TestReceiveMessage:
    """Tests for receive_message node."""
    
    @pytest.mark.asyncio
    async def test_receive_message_validates_required_fields(self):
        """Test that receive_message validates required fields."""
        # Missing user_message
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
        }
        
        with pytest.raises(ValueError, match="missing required fields"):
            await receive_message(state)
    
    @pytest.mark.asyncio
    async def test_receive_message_accepts_valid_state(self):
        """Test that receive_message accepts valid state."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "I want to book a tennis court",
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
        
        result = await receive_message(state)
        
        # State should be unchanged
        assert result == state
        assert result["user_message"] == "I want to book a tennis court"
    
    @pytest.mark.asyncio
    async def test_receive_message_handles_empty_message(self):
        """Test that receive_message handles empty messages gracefully."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "   ",  # Empty/whitespace message
            "flow_state": {},
            "bot_memory": {},
            "messages": [],
        }
        
        # Should not raise error, just log warning
        result = await receive_message(state)
        assert result == state


class TestLoadChat:
    """Tests for load_chat node."""
    
    @pytest.mark.asyncio
    async def test_load_chat_initializes_empty_state(self):
        """Test that load_chat initializes empty flow_state and bot_memory."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Hello",
        }
        
        result = await load_chat(state)
        
        assert result["flow_state"] == {}
        assert result["bot_memory"] == {}
        assert result["messages"] == []
    
    @pytest.mark.asyncio
    async def test_load_chat_preserves_existing_state(self):
        """Test that load_chat preserves existing flow_state and bot_memory."""
        existing_flow_state = {"intent": "booking", "step": "select_property"}
        existing_bot_memory = {"conversation_history": [{"role": "user", "content": "Hi"}]}
        
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Hello",
            "flow_state": existing_flow_state,
            "bot_memory": existing_bot_memory,
        }
        
        result = await load_chat(state)
        
        assert result["flow_state"] == existing_flow_state
        assert result["bot_memory"] == existing_bot_memory
    
    @pytest.mark.asyncio
    async def test_load_chat_loads_message_history(self):
        """Test that load_chat loads message history from MessageService."""
        chat_id = uuid4()
        
        # Mock message objects
        mock_messages = [
            MagicMock(sender_type="user", content="Hello"),
            MagicMock(sender_type="bot", content="Hi! How can I help?"),
            MagicMock(sender_type="user", content="I want to book a court"),
        ]
        
        # Mock MessageService
        mock_message_service = AsyncMock()
        mock_message_service.get_chat_history = AsyncMock(return_value=mock_messages)
        
        state = {
            "chat_id": str(chat_id),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Show me options",
            "flow_state": {},
            "bot_memory": {},
        }
        
        result = await load_chat(state, message_service=mock_message_service)
        
        # Verify message history was loaded
        assert len(result["messages"]) == 3
        assert result["messages"][0] == {"role": "user", "content": "Hello"}
        assert result["messages"][1] == {"role": "assistant", "content": "Hi! How can I help?"}
        assert result["messages"][2] == {"role": "user", "content": "I want to book a court"}
        
        # Verify service was called correctly
        mock_message_service.get_chat_history.assert_called_once_with(
            chat_id=chat_id,
            limit=20
        )
    
    @pytest.mark.asyncio
    async def test_load_chat_handles_service_error(self):
        """Test that load_chat handles MessageService errors gracefully."""
        # Mock MessageService that raises error
        mock_message_service = AsyncMock()
        mock_message_service.get_chat_history = AsyncMock(side_effect=Exception("Database error"))
        
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Hello",
            "flow_state": {},
            "bot_memory": {},
        }
        
        # Should not raise error, just continue with empty messages
        result = await load_chat(state, message_service=mock_message_service)
        
        assert result["messages"] == []


class TestAppendUserMessage:
    """Tests for append_user_message node."""
    
    @pytest.mark.asyncio
    async def test_append_user_message_initializes_conversation_history(self):
        """Test that append_user_message initializes conversation_history."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "I want to book a tennis court",
            "bot_memory": {},
            "messages": [],
        }
        
        result = await append_user_message(state)
        
        assert "conversation_history" in result["bot_memory"]
        assert len(result["bot_memory"]["conversation_history"]) == 1
        assert result["bot_memory"]["conversation_history"][0]["role"] == "user"
        assert result["bot_memory"]["conversation_history"][0]["content"] == "I want to book a tennis court"
        assert "timestamp" in result["bot_memory"]["conversation_history"][0]
    
    @pytest.mark.asyncio
    async def test_append_user_message_appends_to_existing_history(self):
        """Test that append_user_message appends to existing conversation_history."""
        existing_history = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-10T10:00:00"},
            {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-10T10:00:01"},
        ]
        
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "I want to book a court",
            "bot_memory": {"conversation_history": existing_history.copy()},
            "messages": [],
        }
        
        result = await append_user_message(state)
        
        assert len(result["bot_memory"]["conversation_history"]) == 3
        assert result["bot_memory"]["conversation_history"][2]["role"] == "user"
        assert result["bot_memory"]["conversation_history"][2]["content"] == "I want to book a court"
    
    @pytest.mark.asyncio
    async def test_append_user_message_updates_messages_list(self):
        """Test that append_user_message updates ephemeral messages list."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Show me tennis courts",
            "bot_memory": {},
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        }
        
        result = await append_user_message(state)
        
        # Should append to messages list
        assert len(result["messages"]) == 3
        assert result["messages"][2] == {"role": "user", "content": "Show me tennis courts"}
    
    @pytest.mark.asyncio
    async def test_append_user_message_preserves_other_bot_memory(self):
        """Test that append_user_message preserves other bot_memory fields."""
        state = {
            "chat_id": str(uuid4()),
            "user_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "user_message": "Book a court",
            "bot_memory": {
                "user_preferences": {"sport": "tennis"},
                "context": {"last_search": ["prop1", "prop2"]},
            },
            "messages": [],
        }
        
        result = await append_user_message(state)
        
        # Should preserve existing bot_memory fields
        assert result["bot_memory"]["user_preferences"] == {"sport": "tennis"}
        assert result["bot_memory"]["context"] == {"last_search": ["prop1", "prop2"]}
        # And add conversation_history
        assert "conversation_history" in result["bot_memory"]
        assert len(result["bot_memory"]["conversation_history"]) == 1
