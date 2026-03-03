"""
Chat repository for database operations on chat sessions.

This repository provides async methods for creating, retrieving, and updating
chat sessions. It handles all database operations for the Chat model using
async SQLAlchemy sessions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.models.chat import Chat

logger = logging.getLogger(__name__)


class ChatRepository:
    """
    Repository for Chat model database operations.
    
    Provides async methods for CRUD operations on chat sessions,
    including session continuity checks and user chat retrieval.
    
    Attributes:
        session: AsyncSession for database operations
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize ChatRepository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def create(self, chat_data: dict) -> Chat:
        """
        Create a new chat session.
        
        Args:
            chat_data: Dictionary containing chat fields (user_id, owner_id, etc.)
            
        Returns:
            Chat: Created chat instance
            
        Example:
            chat_data = {
                "user_id": user_uuid,
                "owner_id": owner_uuid,
                "status": "active",
                "flow_state": {},
                "bot_memory": {}
            }
            chat = await repo.create(chat_data)
        """
        chat = Chat(**chat_data)
        self.session.add(chat)
        await self.session.flush()
        
        logger.info(
            f"Created chat session: {chat.id} "
            f"(user={chat.user_id}, owner={chat.owner_id})"
        )
        
        return chat
    
    async def get_by_id(self, chat_id: UUID) -> Optional[Chat]:
        """
        Get chat by ID.
        
        Args:
            chat_id: UUID of the chat to retrieve
            
        Returns:
            Chat if found, None otherwise
        """
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            logger.debug(f"Retrieved chat: {chat_id}")
        else:
            logger.debug(f"Chat not found: {chat_id}")
        
        return chat
    
    async def get_latest_by_user_owner(
        self, 
        user_id: UUID, 
        owner_id: UUID
    ) -> Optional[Chat]:
        """
        Get the most recent active chat for a user-owner pair.
        
        This method is used for session continuity to determine if an
        existing conversation should be continued or a new one started.
        
        Args:
            user_id: UUID of the user
            owner_id: UUID of the property owner
            
        Returns:
            Most recent active Chat if found, None otherwise
        """
        result = await self.session.execute(
            select(Chat)
            .where(
                and_(
                    Chat.user_id == user_id,
                    Chat.owner_id == owner_id,
                    Chat.status == "active"
                )
            )
            .order_by(desc(Chat.last_message_at))
            .limit(1)
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            logger.debug(
                f"Found latest chat: {chat.id} "
                f"(user={user_id}, owner={owner_id}, "
                f"last_message={chat.last_message_at})"
            )
        else:
            logger.debug(
                f"No active chat found for user={user_id}, owner={owner_id}"
            )
        
        return chat
    
    async def get_user_chats(
        self, 
        user_id: UUID, 
        limit: int = 50
    ) -> List[Chat]:
        """
        Get all chats for a user, ordered by most recent first.
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of chats to return (default: 50)
            
        Returns:
            List of Chat instances ordered by last_message_at descending
        """
        result = await self.session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(desc(Chat.last_message_at))
            .limit(limit)
        )
        chats = list(result.scalars().all())
        
        logger.debug(f"Retrieved {len(chats)} chats for user {user_id}")
        
        return chats
    
    async def update(self, chat: Chat, update_data: dict) -> Chat:
        """
        Update chat fields.
        
        Args:
            chat: Chat instance to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated Chat instance
            
        Example:
            update_data = {
                "flow_state": {"step": "select_time", "property_id": "..."},
                "last_message_at": datetime.utcnow()
            }
            chat = await repo.update(chat, update_data)
        """
        for key, value in update_data.items():
            if hasattr(chat, key):
                setattr(chat, key, value)
        
        await self.session.flush()
        
        logger.debug(
            f"Updated chat {chat.id} with fields: {list(update_data.keys())}"
        )
        
        return chat
    
    async def is_session_expired(
        self, 
        chat: Chat, 
        threshold_hours: int = 24
    ) -> bool:
        """
        Check if chat session has expired based on time threshold.
        
        Used for session continuity logic to determine if user should
        be asked about continuing previous conversation.
        
        Args:
            chat: Chat instance to check
            threshold_hours: Hours after which session is considered expired (default: 24)
            
        Returns:
            True if session expired, False otherwise
        """
        threshold = datetime.utcnow() - timedelta(hours=threshold_hours)
        is_expired = chat.last_message_at < threshold
        
        if is_expired:
            logger.debug(
                f"Chat {chat.id} session expired "
                f"(last_message: {chat.last_message_at}, threshold: {threshold})"
            )
        
        return is_expired
