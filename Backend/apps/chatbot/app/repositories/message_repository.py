"""
Message repository for database operations on chat messages.

This repository provides async methods for creating and retrieving messages,
aggregating user messages, and tracking token usage for cost monitoring.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import logging

from app.models.message import Message

logger = logging.getLogger(__name__)


class MessageRepository:
    """
    Repository for Message model database operations.
    
    Provides async methods for CRUD operations on messages,
    including chat history retrieval, message aggregation,
    and token usage tracking.
    
    Attributes:
        session: AsyncSession for database operations
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize MessageRepository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def create(self, message_data: dict) -> Message:
        """
        Create a new message.
        
        Args:
            message_data: Dictionary containing message fields
            
        Returns:
            Message: Created message instance
            
        Example:
            message_data = {
                "chat_id": chat_uuid,
                "sender_type": "user",
                "message_type": "text",
                "content": "I want to book a tennis court",
                "message_metadata": {},
                "token_usage": None
            }
            message = await repo.create(message_data)
        """
        message = Message(**message_data)
        self.session.add(message)
        await self.session.flush()
        
        logger.info(
            f"Created message: {message.id} "
            f"(chat={message.chat_id}, sender={message.sender_type}, "
            f"type={message.message_type})"
        )
        
        return message
    
    async def get_chat_history(
        self, 
        chat_id: UUID, 
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get all messages for a chat in chronological order.
        
        Retrieves message history for display or context building.
        Messages are ordered by creation time (oldest first).
        
        Args:
            chat_id: UUID of the chat
            limit: Optional maximum number of messages to return
            
        Returns:
            List of Message instances in chronological order
        """
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        
        logger.debug(
            f"Retrieved {len(messages)} messages for chat {chat_id}"
            + (f" (limited to {limit})" if limit else "")
        )
        
        return messages
    
    async def get_unprocessed_user_messages(
        self, 
        chat_id: UUID, 
        after_timestamp: datetime
    ) -> List[Message]:
        """
        Get user messages after a specific timestamp.
        
        Used for multi-message aggregation when users send multiple
        messages in quick succession (WhatsApp-style behavior).
        
        Args:
            chat_id: UUID of the chat
            after_timestamp: Retrieve messages created after this time
            
        Returns:
            List of user Message instances in chronological order
        """
        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_type == "user",
                    Message.created_at > after_timestamp
                )
            )
            .order_by(Message.created_at)
        )
        messages = list(result.scalars().all())
        
        logger.debug(
            f"Retrieved {len(messages)} unprocessed user messages "
            f"for chat {chat_id} after {after_timestamp}"
        )
        
        return messages
    
    async def get_total_token_usage(
        self, 
        chat_id: UUID
    ) -> int:
        """
        Calculate total token usage for a chat.
        
        Sums all token_usage values for cost monitoring and analytics.
        Used to track LLM costs per conversation.
        
        Args:
            chat_id: UUID of the chat
            
        Returns:
            Total token count (0 if no tokens used)
        """
        result = await self.session.execute(
            select(func.sum(Message.token_usage))
            .where(Message.chat_id == chat_id)
        )
        total = result.scalar() or 0
        
        logger.debug(f"Total token usage for chat {chat_id}: {total}")
        
        return total
    
    async def get_last_message(
        self, 
        chat_id: UUID
    ) -> Optional[Message]:
        """
        Get the last message for a chat.
        
        Retrieves the most recent message in a chat session,
        used for displaying message previews in chat lists.
        
        Args:
            chat_id: UUID of the chat
            
        Returns:
            Last Message instance or None if no messages exist
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        message = result.scalar_one_or_none()
        
        if message:
            logger.debug(f"Retrieved last message for chat {chat_id}: {message.id}")
        else:
            logger.debug(f"No messages found for chat {chat_id}")
        
        return message
