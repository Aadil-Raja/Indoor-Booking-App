"""
Unit tests for MessageService.

Tests cover:
- Message creation with validation
- Chat history retrieval
- Multi-message aggregation for WhatsApp-style inputs
- Token usage tracking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from message_service import MessageService
from ..models.message import Message


class TestMessageService:
    """Test suite for MessageService business logic."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_message_repo(self):
        """Create mock MessageRepository."""
        return AsyncMock()
    
    @pytest.fixture
    def message_service(self, mock_session, mock_message_repo):
        """Create MessageService instance with mocked dependencies."""
        return MessageService(
            session=mock_session,
            message_repo=mock_message_repo
        )
    
    @pytest.fixture
    def sample_message(self):
        """Create sample message instance."""
        message = MagicMock(spec=Message)
        message.id = uuid4()
        message.chat_id = uuid4()
        message.sender_type = "user"
        message.message_type = "text"
        message.content = "I want to book a tennis court"
        message.message_metadata = {}
        message.token_usage = None
        message.created_at = datetime.utcnow()
        return message
    
    @pytest.mark.asyncio
    async def test_create_message_user_text(
        self, message_service, mock_message_repo, sample_message
    ):
        """Test creating a simple user text message."""
        chat_id = uuid4()
        content = "I want to book a tennis court"
        
        mock_message_repo.create.return_value = sample_message
        
        result = await message_service.create_message(
            chat_id=chat_id,
            sender_type="user",
            content=content
        )
        
        assert result == sample_message
        mock_message_repo.create.assert_called_once()
        call_args = mock_message_repo.create.call_args[0][0]
        assert call_args["chat_id"] == chat_id
        assert call_args["sender_type"] == "user"
        assert call_args["content"] == content
        assert call_args["message_type"] == "text"
        assert call_args["message_metadata"] == {}
        assert call_args["token_usage"] is None
    
    @pytest.mark.asyncio
    async def test_create_message_bot_with_buttons(
        self, message_service, mock_message_repo
    ):
        """Test creating a bot message with button metadata."""
        chat_id = uuid4()
        content = "Which facility would you like?"
        metadata = {
            "buttons": [
                {"id": "prop1", "text": "Downtown Sports"},
                {"id": "prop2", "text": "Westside Arena"}
            ]
        }
        token_usage = 150
        
        bot_message = MagicMock(spec=Message)
        bot_message.id = uuid4()
        mock_message_repo.create.return_value = bot_message
        
        result = await message_service.create_message(
            chat_id=chat_id,
            sender_type="bot",
            content=content,
            message_type="button",
            metadata=metadata,
            token_usage=token_usage
        )
        
        assert result == bot_message
        call_args = mock_message_repo.create.call_args[0][0]
        assert call_args["sender_type"] == "bot"
        assert call_args["message_type"] == "button"
        assert call_args["message_metadata"] == metadata
        assert call_args["token_usage"] == token_usage
    
    @pytest.mark.asyncio
    async def test_create_message_bot_with_list(
        self, message_service, mock_message_repo
    ):
        """Test creating a bot message with list metadata."""
        chat_id = uuid4()
        content = "Available time slots:"
        metadata = {
            "list_items": [
                {"id": "time1", "title": "2:00 PM", "description": "$50/hour"},
                {"id": "time2", "title": "3:00 PM", "description": "$50/hour"}
            ]
        }
        
        list_message = MagicMock(spec=Message)
        mock_message_repo.create.return_value = list_message
        
        result = await message_service.create_message(
            chat_id=chat_id,
            sender_type="bot",
            content=content,
            message_type="list",
            metadata=metadata,
            token_usage=200
        )
        
        assert result == list_message
        call_args = mock_message_repo.create.call_args[0][0]
        assert call_args["message_type"] == "list"
        assert call_args["message_metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_create_message_system(
        self, message_service, mock_message_repo
    ):
        """Test creating a system message."""
        chat_id = uuid4()
        content = "Session expired. Starting new conversation."
        
        system_message = MagicMock(spec=Message)
        mock_message_repo.create.return_value = system_message
        
        result = await message_service.create_message(
            chat_id=chat_id,
            sender_type="system",
            content=content
        )
        
        assert result == system_message
        call_args = mock_message_repo.create.call_args[0][0]
        assert call_args["sender_type"] == "system"
    
    @pytest.mark.asyncio
    async def test_create_message_invalid_sender_type(
        self, message_service
    ):
        """Test that invalid sender_type raises ValueError."""
        with pytest.raises(ValueError, match="sender_type must be one of"):
            await message_service.create_message(
                chat_id=uuid4(),
                sender_type="invalid",
                content="test"
            )
    
    @pytest.mark.asyncio
    async def test_create_message_invalid_message_type(
        self, message_service
    ):
        """Test that invalid message_type raises ValueError."""
        with pytest.raises(ValueError, match="message_type must be one of"):
            await message_service.create_message(
                chat_id=uuid4(),
                sender_type="user",
                content="test",
                message_type="invalid"
            )
    
    @pytest.mark.asyncio
    async def test_get_chat_history_all_messages(
        self, message_service, mock_message_repo
    ):
        """Test retrieving all messages for a chat."""
        chat_id = uuid4()
        
        messages = [
            MagicMock(spec=Message, id=uuid4(), content=f"Message {i}")
            for i in range(5)
        ]
        mock_message_repo.get_chat_history.return_value = messages
        
        result = await message_service.get_chat_history(chat_id)
        
        assert result == messages
        mock_message_repo.get_chat_history.assert_called_once_with(
            chat_id, None
        )
    
    @pytest.mark.asyncio
    async def test_get_chat_history_with_limit(
        self, message_service, mock_message_repo
    ):
        """Test retrieving limited number of messages."""
        chat_id = uuid4()
        limit = 50
        
        messages = [
            MagicMock(spec=Message, id=uuid4())
            for i in range(limit)
        ]
        mock_message_repo.get_chat_history.return_value = messages
        
        result = await message_service.get_chat_history(chat_id, limit=limit)
        
        assert len(result) == limit
        mock_message_repo.get_chat_history.assert_called_once_with(
            chat_id, limit
        )
    
    @pytest.mark.asyncio
    async def test_aggregate_user_messages_no_messages(
        self, message_service, mock_message_repo
    ):
        """Test aggregation with no unprocessed messages."""
        chat_id = uuid4()
        after_timestamp = datetime.utcnow()
        
        mock_message_repo.get_unprocessed_user_messages.return_value = []
        
        result = await message_service.aggregate_user_messages(
            chat_id, after_timestamp
        )
        
        assert result == ""
        mock_message_repo.get_unprocessed_user_messages.assert_called_once_with(
            chat_id, after_timestamp
        )
    
    @pytest.mark.asyncio
    async def test_aggregate_user_messages_single_message(
        self, message_service, mock_message_repo
    ):
        """Test aggregation with single message returns content as-is."""
        chat_id = uuid4()
        after_timestamp = datetime.utcnow()
        content = "I want to book a tennis court"
        
        message = MagicMock(spec=Message)
        message.content = content
        mock_message_repo.get_unprocessed_user_messages.return_value = [message]
        
        result = await message_service.aggregate_user_messages(
            chat_id, after_timestamp
        )
        
        assert result == content
    
    @pytest.mark.asyncio
    async def test_aggregate_user_messages_multiple_messages(
        self, message_service, mock_message_repo
    ):
        """Test aggregation of multiple sequential messages."""
        chat_id = uuid4()
        after_timestamp = datetime.utcnow()
        
        # Simulate user sending three quick messages
        messages = [
            MagicMock(spec=Message, content="I want to book"),
            MagicMock(spec=Message, content="a tennis court"),
            MagicMock(spec=Message, content="for tomorrow afternoon")
        ]
        mock_message_repo.get_unprocessed_user_messages.return_value = messages
        
        result = await message_service.aggregate_user_messages(
            chat_id, after_timestamp
        )
        
        expected = "I want to book\na tennis court\nfor tomorrow afternoon"
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_aggregate_user_messages_preserves_order(
        self, message_service, mock_message_repo
    ):
        """Test that aggregation preserves chronological order."""
        chat_id = uuid4()
        after_timestamp = datetime.utcnow()
        
        # Messages should be in chronological order
        messages = [
            MagicMock(
                spec=Message,
                content="First",
                created_at=datetime.utcnow()
            ),
            MagicMock(
                spec=Message,
                content="Second",
                created_at=datetime.utcnow() + timedelta(seconds=1)
            ),
            MagicMock(
                spec=Message,
                content="Third",
                created_at=datetime.utcnow() + timedelta(seconds=2)
            )
        ]
        mock_message_repo.get_unprocessed_user_messages.return_value = messages
        
        result = await message_service.aggregate_user_messages(
            chat_id, after_timestamp
        )
        
        assert result == "First\nSecond\nThird"
    
    @pytest.mark.asyncio
    async def test_create_message_with_media_metadata(
        self, message_service, mock_message_repo
    ):
        """Test creating a media message with URL metadata."""
        chat_id = uuid4()
        content = "Tennis Court A"
        metadata = {
            "media_type": "image",
            "media_url": "https://example.com/court.jpg",
            "caption": "Tennis Court A"
        }
        
        media_message = MagicMock(spec=Message)
        mock_message_repo.create.return_value = media_message
        
        result = await message_service.create_message(
            chat_id=chat_id,
            sender_type="bot",
            content=content,
            message_type="media",
            metadata=metadata
        )
        
        assert result == media_message
        call_args = mock_message_repo.create.call_args[0][0]
        assert call_args["message_type"] == "media"
        assert call_args["message_metadata"] == metadata
