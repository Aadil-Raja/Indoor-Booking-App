"""
Chat service for chat session management.

Handles:
- Session determination (reuse or create new)
- Chat creation and updates
- State management (flow_state, bot_memory)
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
    """Chat session management service."""
    
    def __init__(
        self,
        session: AsyncSession,
        chat_repo: ChatRepository,
        message_repo: MessageRepository
    ):
        self.session = session
        self.chat_repo = chat_repo
        self.message_repo = message_repo
    
    async def determine_session(
        self, 
        user_id: int, 
        owner_profile_id: int
    ) -> Tuple[Chat, bool]:
        """
        Get or create chat session (simplified for MVP).
        
        Simple logic: Reuse existing active chat if found, otherwise create new.
        No expiry checks, no keyword detection - keeps it simple.
        
        Args:
            user_id: User ID
            owner_profile_id: Owner profile ID
            
        Returns:
            Tuple of (Chat, is_new_session):
                - Chat: Existing or newly created chat instance
                - is_new_session: True if new chat created, False if reusing existing
        """
        logger.info(f"Getting session for user={user_id}, owner_profile={owner_profile_id}")
        
        # Look for existing active chat
        existing_chat = await self.chat_repo.get_latest_by_user_owner(
            user_id, owner_profile_id
        )
        
        # Reuse if found
        if existing_chat:
            logger.info(f"Reusing existing session: {existing_chat.id}")
            return existing_chat, False
        
        # Create new if not found
        logger.info("Creating new session")
        new_chat = await self._create_new_session(user_id, owner_profile_id)
        return new_chat, True
    
    async def create_chat(self, user_id: int, owner_profile_id: int) -> Chat:
        """Create a new chat session."""
        logger.info(f"Creating new chat for user={user_id}, owner={owner_profile_id}")
        return await self._create_new_session(user_id, owner_profile_id)
    
    async def update_chat_state(
        self,
        chat: Chat,
        flow_state: dict = None,
        bot_memory: dict = None
    ) -> Chat:
        """
        Update chat state (flow_state and/or bot_memory).
        
        Always updates last_message_at to current time.
        """
        update_data = {"last_message_at": datetime.now(timezone.utc)}
        
        if flow_state is not None:
            update_data["flow_state"] = flow_state
        
        if bot_memory is not None:
            update_data["bot_memory"] = bot_memory
        
        updated_chat = await self.chat_repo.update(chat, update_data)
        logger.info(f"Updated chat {chat.id}")
        
        return updated_chat
    
    async def close_chat(self, chat_id: UUID) -> Chat:
        """Close a chat session (sets status to 'closed')."""
        logger.info(f"Closing chat: {chat_id}")
        
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        updated_chat = await self.chat_repo.update(chat, {"status": "closed"})
        logger.info(f"Chat {chat_id} closed")
        
        return updated_chat
    

    async def _create_new_session(self, user_id: int, owner_profile_id: int) -> Chat:
        """Create new chat with default values."""
        chat_data = {
            "user_id": user_id,
            "owner_profile_id": owner_profile_id,
            "status": "active",
            "flow_state": {},
            "bot_memory": {}
        }
        
        chat = await self.chat_repo.create(chat_data)
        logger.info(f"Created chat: {chat.id}")
        
        return chat
