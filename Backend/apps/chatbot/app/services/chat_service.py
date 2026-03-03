"""
Chat service for business logic related to chat session management.

This service implements the core business logic for chat sessions, including:
- Session continuity determination (24-hour threshold, new topic detection)
- Chat creation and lifecycle management
- State updates with transaction management
- Integration with repositories for data access

The service follows async patterns and uses dependency injection for
repository access, ensuring clean separation of concerns.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple
from datetime import datetime, timezone
import logging
from uuid import UUID
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.models.chat import Chat

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for chat session management business logic.
    
    Handles session continuity, chat lifecycle, and state management.
    All operations are async and use transaction management through
    the provided database session.
    
    Attributes:
        session: AsyncSession for database operations
        chat_repo: ChatRepository for chat data access
        message_repo: MessageRepository for message data access
    """
    
    def __init__(
        self, 
        session: AsyncSession,
        chat_repo: ChatRepository,
        message_repo: MessageRepository
    ):
        """
        Initialize ChatService with session and repositories.
        
        Args:
            session: AsyncSession for database operations
            chat_repo: ChatRepository instance
            message_repo: MessageRepository instance
        """
        self.session = session
        self.chat_repo = chat_repo
        self.message_repo = message_repo
    
    async def determine_session(
        self, 
        user_id: int, 
        owner_profile_id: int,
        user_message: str
    ) -> Tuple[Chat, bool]:
        """
        Determine whether to continue existing session or create new one.
        
        Implements session continuity logic per Requirements 4.1-4.8:
        - Checks for explicit new session intent in user message
        - Queries for latest active chat session
        - Evaluates 24-hour threshold for session expiration
        - Returns existing chat if within threshold
        - Returns existing chat with expired flag if beyond threshold
        
        The caller is responsible for handling expired sessions by
        prompting the user about continuing previous conversation.
        
        Args:
            user_id: UUID of the user
            owner_profile_id: UUID of the owner profile
            user_message: User's message content for intent detection
            
        Returns:
            Tuple of (Chat, is_new_session):
                - Chat: Existing or newly created chat instance
                - is_new_session: True if new chat created, False if existing
                
        Example:
            chat, is_new = await service.determine_session(
                user_id=user_uuid,
                owner_id=owner_uuid,
                user_message="I want to book a tennis court"
            )
            
            if not is_new and await chat_repo.is_session_expired(chat):
                # Prompt user about continuing previous conversation
                pass
        """
        logger.info(
            f"Determining session for user={user_id}, owner_profile={owner_profile_id}"
        )
        
        # Check for explicit new session intent (Requirement 4.7)
        if self._is_new_session_intent(user_message):
            logger.info("New session intent detected in user message")
            new_chat = await self._create_new_session(user_id, owner_profile_id)
            return new_chat, True
        
        # Look for existing session (Requirement 4.1)
        existing_chat = await self.chat_repo.get_latest_by_user_owner(
            user_id, owner_profile_id
        )
        
        # No existing session - create new one (Requirement 4.2)
        if not existing_chat:
            logger.info("No existing session found, creating new chat")
            new_chat = await self._create_new_session(user_id, owner_profile_id)
            return new_chat, True
        
        # Check if session expired (Requirement 4.3, 4.4)
        if await self.chat_repo.is_session_expired(existing_chat):
            logger.info(
                f"Session expired for chat {existing_chat.id}, "
                f"last_message_at={existing_chat.last_message_at}"
            )
            # Return existing chat but flag as expired
            # Caller will handle continuation prompt
            return existing_chat, False
        
        # Continue existing session (Requirement 4.3, 4.8)
        logger.info(
            f"Continuing existing session: {existing_chat.id}"
        )
        return existing_chat, False
    
    async def create_chat(
        self, 
        user_id: int, 
        owner_profile_id: int
    ) -> Chat:
        """
        Create a new chat session.
        
        Creates a new active chat with empty flow_state and bot_memory.
        Used when explicitly starting a new conversation or when user
        denies reference to previous conversation.
        
        Args:
            user_id: UUID of the user
            owner_id: UUID of the property owner
            
        Returns:
            Chat: Newly created chat instance
            
        Example:
            chat = await service.create_chat(
                user_id=user_uuid,
                owner_id=owner_uuid
            )
        """
        logger.info(
            f"Creating new chat for user={user_id}, owner_profile={owner_profile_id}"
        )
        return await self._create_new_session(user_id, owner_profile_id)
    
    async def update_chat_state(
        self, 
        chat: Chat, 
        flow_state: dict = None,
        bot_memory: dict = None
    ) -> Chat:
        """
        Update chat flow state and/or bot memory.
        
        Updates the chat's structured flow_state (booking progress) and/or
        unstructured bot_memory (AI context). Always updates last_message_at
        to current time for session continuity tracking.
        
        Uses transaction management - changes are flushed but not committed.
        The caller is responsible for committing the transaction.
        
        Args:
            chat: Chat instance to update
            flow_state: Optional new flow_state dict (booking progress)
            bot_memory: Optional new bot_memory dict (AI context)
            
        Returns:
            Chat: Updated chat instance
            
        Example:
            updated_chat = await service.update_chat_state(
                chat=chat,
                flow_state={"step": "select_time", "property_id": "..."},
                bot_memory={"context": {"last_search": [...]}}
            )
        """
        update_data = {"last_message_at": datetime.now(timezone.utc)}
        
        if flow_state is not None:
            update_data["flow_state"] = flow_state
            logger.debug(
                f"Updating flow_state for chat {chat.id}: "
                f"step={flow_state.get('step')}"
            )
        
        if bot_memory is not None:
            update_data["bot_memory"] = bot_memory
            logger.debug(f"Updating bot_memory for chat {chat.id}")
        
        updated_chat = await self.chat_repo.update(chat, update_data)
        
        logger.info(
            f"Updated chat state for {chat.id} "
            f"(fields: {list(update_data.keys())})"
        )
        
        return updated_chat
    
    async def close_chat(self, chat_id: UUID) -> Chat:
        """
        Close a chat session.
        
        Sets chat status to 'closed', preventing it from being returned
        in session continuity queries. Closed chats remain in database
        for history and analytics.
        
        Args:
            chat_id: UUID of the chat to close
            
        Returns:
            Chat: Updated chat instance with status='closed'
            
        Example:
            closed_chat = await service.close_chat(chat_id=chat_uuid)
        """
        logger.info(f"Closing chat session: {chat_id}")
        
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            logger.error(f"Cannot close chat {chat_id}: not found")
            raise ValueError(f"Chat {chat_id} not found")
        
        updated_chat = await self.chat_repo.update(
            chat, 
            {"status": "closed"}
        )
        
        logger.info(f"Chat {chat_id} closed successfully")
        return updated_chat
    
    def _is_new_session_intent(self, message: str) -> bool:
        """
        Detect if user wants to start a new conversation.
        
        Implements Requirement 4.7: new topic detection.
        Uses keyword matching to identify explicit new session intent.
        
        Args:
            message: User's message content
            
        Returns:
            True if new session intent detected, False otherwise
        """
        new_session_keywords = [
            "new topic",
            "start over",
            "new conversation",
            "forget previous",
            "reset",
            "begin again",
            "fresh start"
        ]
        
        message_lower = message.lower()
        detected = any(
            keyword in message_lower 
            for keyword in new_session_keywords
        )
        
        if detected:
            logger.debug(
                f"New session keyword detected in: {message[:50]}..."
            )
        
        return detected
    
    async def _create_new_session(
        self, 
        user_id: int, 
        owner_profile_id: int
    ) -> Chat:
        """
        Internal method to create new chat session.
        
        Creates chat with default values:
        - status: 'active'
        - flow_state: empty dict
        - bot_memory: empty dict
        - last_message_at: current time (set by database default)
        
        Args:
            user_id: UUID of the user
            owner_profile_id: UUID of the owner profile
            
        Returns:
            Chat: Newly created chat instance
        """
        chat_data = {
            "user_id": user_id,
            "owner_profile_id": owner_profile_id,
            "status": "active",
            "flow_state": {},
            "bot_memory": {}
        }
        
        chat = await self.chat_repo.create(chat_data)
        
        logger.info(
            f"Created new chat session: {chat.id} "
            f"(user={user_id}, owner_profile={owner_profile_id})"
        )
        
        return chat
