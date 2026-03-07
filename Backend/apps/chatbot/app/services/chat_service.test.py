"""
Unit tests for ChatService.

Tests cover:
- Session continuity logic (24-hour threshold)
- New topic detection
- Chat creation and state updates
- Transaction management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from chat_service import ChatService
from ..models.chat import Chat


class TestChatService:
    """Test suite for ChatService business logic."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_chat_repo(self):
        """Create mock ChatRepository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_message_repo(self):
        """Create mock MessageRepository."""
        return AsyncMock()
    
    @pytest.fixture
    def chat_service(self, mock_session, mock_chat_repo, mock_message_repo):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(
            session=mock_session,
            chat_repo=mock_chat_repo,
            message_repo=mock_message_repo
        )
    
    @pytest.fixture
    def sample_chat(self):
        """Create sample chat instance."""
        chat = MagicMock(spec=Chat)
        chat.id = uuid4()
        chat.user_id = uuid4()
        chat.owner_id = uuid4()
        chat.status = "active"
        chat.last_message_at = datetime.utcnow()
        chat.flow_state = {}
        chat.bot_memory = {}
        return chat
    
    @pytest.mark.asyncio
    async def test_determine_session_new_topic_intent(
        self, chat_service, mock_chat_repo
    ):
        """Test that 'new topic' message creates new session."""
        user_id = uuid4()
        owner_id = uuid4()
        
        # Mock repository to return None (no existing chat)
        mock_chat_repo.get_latest_by_user_owner.return_value = None
        mock_chat_repo.create.return_value = MagicMock(
            id=uuid4(),
            user_id=user_id,
            owner_id=owner_id
        )
        
        chat, is_new = await chat_service.determine_session(
            user_id=user_id,
            owner_id=owner_id,
            user_message="new topic - I want to book a court"
        )
        
        assert is_new is True
        mock_chat_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_determine_session_no_existing_chat(
        self, chat_service, mock_chat_repo
    ):
        """Test that no existing chat creates new session."""
        user_id = uuid4()
        owner_id = uuid4()
        
        mock_chat_repo.get_latest_by_user_owner.return_value = None
        mock_chat_repo.create.return_value = MagicMock(
            id=uuid4(),
            user_id=user_id,
            owner_id=owner_id
        )
        
        chat, is_new = await chat_service.determine_session(
            user_id=user_id,
            owner_id=owner_id,
            user_message="I want to book a tennis court"
        )
        
        assert is_new is True
        mock_chat_repo.get_latest_by_user_owner.assert_called_once_with(
            user_id, owner_id
        )
        mock_chat_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_determine_session_continue_recent_chat(
        self, chat_service, mock_chat_repo, sample_chat
    ):
        """Test that recent chat (within 24 hours) is continued."""
        user_id = uuid4()
        owner_id = uuid4()
        
        # Set last message to 1 hour ago (within threshold)
        sample_chat.last_message_at = datetime.utcnow() - timedelta(hours=1)
        
        mock_chat_repo.get_latest_by_user_owner.return_value = sample_chat
        mock_chat_repo.is_session_expired.return_value = False
        
        chat, is_new = await chat_service.determine_session(
            user_id=user_id,
            owner_id=owner_id,
            user_message="What about tomorrow?"
        )
        
        assert is_new is False
        assert chat == sample_chat
        mock_chat_repo.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_determine_session_expired_chat(
        self, chat_service, mock_chat_repo, sample_chat
    ):
        """Test that expired chat (beyond 24 hours) is flagged."""
        user_id = uuid4()
        owner_id = uuid4()
        
        # Set last message to 25 hours ago (beyond threshold)
        sample_chat.last_message_at = datetime.utcnow() - timedelta(hours=25)
        
        mock_chat_repo.get_latest_by_user_owner.return_value = sample_chat
        mock_chat_repo.is_session_expired.return_value = True
        
        chat, is_new = await chat_service.determine_session(
            user_id=user_id,
            owner_id=owner_id,
            user_message="I want to book a court"
        )
        
        assert is_new is False
        assert chat == sample_chat
        # Should not create new chat - caller handles continuation prompt
        mock_chat_repo.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_chat(self, chat_service, mock_chat_repo):
        """Test explicit chat creation."""
        user_id = uuid4()
        owner_id = uuid4()
        
        expected_chat = MagicMock(id=uuid4())
        mock_chat_repo.create.return_value = expected_chat
        
        chat = await chat_service.create_chat(user_id, owner_id)
        
        assert chat == expected_chat
        mock_chat_repo.create.assert_called_once()
        call_args = mock_chat_repo.create.call_args[0][0]
        assert call_args["user_id"] == user_id
        assert call_args["owner_id"] == owner_id
        assert call_args["status"] == "active"
        assert call_args["flow_state"] == {}
        assert call_args["bot_memory"] == {}
    
    @pytest.mark.asyncio
    async def test_update_chat_state_flow_state_only(
        self, chat_service, mock_chat_repo, sample_chat
    ):
        """Test updating only flow_state."""
        new_flow_state = {
            "step": "select_time",
            "property_id": str(uuid4())
        }
        
        mock_chat_repo.update.return_value = sample_chat
        
        result = await chat_service.update_chat_state(
            chat=sample_chat,
            flow_state=new_flow_state
        )
        
        assert result == sample_chat
        mock_chat_repo.update.assert_called_once()
        call_args = mock_chat_repo.update.call_args[0]
        assert call_args[0] == sample_chat
        update_data = call_args[1]
        assert update_data["flow_state"] == new_flow_state
        assert "last_message_at" in update_data
        assert "bot_memory" not in update_data
    
    @pytest.mark.asyncio
    async def test_update_chat_state_bot_memory_only(
        self, chat_service, mock_chat_repo, sample_chat
    ):
        """Test updating only bot_memory."""
        new_bot_memory = {
            "context": {"last_search": ["prop1", "prop2"]}
        }
        
        mock_chat_repo.update.return_value = sample_chat
        
        result = await chat_service.update_chat_state(
            chat=sample_chat,
            bot_memory=new_bot_memory
        )
        
        assert result == sample_chat
        call_args = mock_chat_repo.update.call_args[0]
        update_data = call_args[1]
        assert update_data["bot_memory"] == new_bot_memory
        assert "last_message_at" in update_data
        assert "flow_state" not in update_data
    
    @pytest.mark.asyncio
    async def test_update_chat_state_both(
        self, chat_service, mock_chat_repo, sample_chat
    ):
        """Test updating both flow_state and bot_memory."""
        new_flow_state = {"step": "confirm"}
        new_bot_memory = {"total_messages": 10}
        
        mock_chat_repo.update.return_value = sample_chat
        
        result = await chat_service.update_chat_state(
            chat=sample_chat,
            flow_state=new_flow_state,
            bot_memory=new_bot_memory
        )
        
        call_args = mock_chat_repo.update.call_args[0]
        update_data = call_args[1]
        assert update_data["flow_state"] == new_flow_state
        assert update_data["bot_memory"] == new_bot_memory
        assert "last_message_at" in update_data
    
    @pytest.mark.asyncio
    async def test_close_chat(self, chat_service, mock_chat_repo, sample_chat):
        """Test closing a chat session."""
        chat_id = sample_chat.id
        
        mock_chat_repo.get_by_id.return_value = sample_chat
        mock_chat_repo.update.return_value = sample_chat
        
        result = await chat_service.close_chat(chat_id)
        
        assert result == sample_chat
        mock_chat_repo.get_by_id.assert_called_once_with(chat_id)
        mock_chat_repo.update.assert_called_once()
        call_args = mock_chat_repo.update.call_args[0]
        assert call_args[1] == {"status": "closed"}
    
    @pytest.mark.asyncio
    async def test_close_chat_not_found(
        self, chat_service, mock_chat_repo
    ):
        """Test closing non-existent chat raises error."""
        chat_id = uuid4()
        mock_chat_repo.get_by_id.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            await chat_service.close_chat(chat_id)
    
    def test_is_new_session_intent_detected(self, chat_service):
        """Test new session intent detection with various keywords."""
        test_cases = [
            "new topic - I want to book",
            "Let's start over",
            "I want a new conversation",
            "Please forget previous chat",
            "Can we reset?",
            "Begin again with a new search"
        ]
        
        for message in test_cases:
            assert chat_service._is_new_session_intent(message) is True
    
    def test_is_new_session_intent_not_detected(self, chat_service):
        """Test that normal messages don't trigger new session."""
        test_cases = [
            "I want to book a tennis court",
            "What about tomorrow?",
            "Show me available properties",
            "Can I see the pricing?"
        ]
        
        for message in test_cases:
            assert chat_service._is_new_session_intent(message) is False
