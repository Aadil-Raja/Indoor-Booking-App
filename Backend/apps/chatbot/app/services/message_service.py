"""
Message service for business logic related to message management.

This service implements the core business logic for message operations, including:
- Message creation with proper metadata handling
- Chat history retrieval for context building
- Multi-message aggregation for WhatsApp-style sequential inputs
- Integration with repositories for data access

The service follows async patterns and uses dependency injection for
repository access, ensuring clean separation of concerns.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from app.repositories.message_repository import MessageRepository
from app.models.message import Message

logger = logging.getLogger(__name__)


class MessageService:
    """
    Service for message management business logic.
    
    Handles message creation, retrieval, and aggregation.
    All operations are async and use transaction management through
    the provided database session.
    
    Attributes:
        session: AsyncSession for database operations
        message_repo: MessageRepository for message data access
    """
    
    def __init__(
        self, 
        session: AsyncSession,
        message_repo: MessageRepository
    ):
        """
        Initialize MessageService with session and repository.
        
        Args:
            session: AsyncSession for database operations
            message_repo: MessageRepository instance
        """
        self.session = session
        self.message_repo = message_repo
    
    async def create_message(
        self,
        chat_id: UUID,
        sender_type: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[dict] = None,
        token_usage: Optional[int] = None
    ) -> Message:
        """
        Create a new message.
        
        Creates a message with the specified attributes. Validates sender_type
        and message_type against allowed values. Stores metadata for rich
        message types (buttons, lists, media).
        
        Implements Requirements 5.1 (store each message separately),
        3.1-3.8 (message model schema), and 13.1-13.2 (token tracking).
        
        Args:
            chat_id: UUID of the chat session
            sender_type: Message sender ('user', 'bot', 'system')
            content: Message text content
            message_type: Message format ('text', 'button', 'list', 'media')
            metadata: Optional dict for message-specific data
            token_usage: Optional LLM token count for cost tracking
            
        Returns:
            Message: Created message instance
            
        Raises:
            ValueError: If sender_type or message_type is invalid
            
        Example:
            # Create user text message
            message = await service.create_message(
                chat_id=chat_uuid,
                sender_type="user",
                content="I want to book a tennis court"
            )
            
            # Create bot button message
            message = await service.create_message(
                chat_id=chat_uuid,
                sender_type="bot",
                content="Which facility would you like?",
                message_type="button",
                metadata={
                    "buttons": [
                        {"id": "prop1", "text": "Downtown Sports"},
                        {"id": "prop2", "text": "Westside Arena"}
                    ]
                },
                token_usage=150
            )
        """
        # Validate sender_type
        valid_sender_types = ["user", "bot", "system"]
        if sender_type not in valid_sender_types:
            logger.error(
                f"Invalid sender_type: {sender_type}. "
                f"Must be one of {valid_sender_types}"
            )
            raise ValueError(
                f"sender_type must be one of {valid_sender_types}, "
                f"got '{sender_type}'"
            )
        
        # Validate message_type
        valid_message_types = ["text", "button", "list", "media"]
        if message_type not in valid_message_types:
            logger.error(
                f"Invalid message_type: {message_type}. "
                f"Must be one of {valid_message_types}"
            )
            raise ValueError(
                f"message_type must be one of {valid_message_types}, "
                f"got '{message_type}'"
            )
        
        # Prepare message data
        message_data = {
            "chat_id": chat_id,
            "sender_type": sender_type,
            "message_type": message_type,
            "content": content,
            "message_metadata": metadata or {},
            "token_usage": token_usage
        }
        
        # Create message through repository
        message = await self.message_repo.create(message_data)
        
        logger.info(
            f"Created {sender_type} message: {message.id} "
            f"(chat={chat_id}, type={message_type}, "
            f"tokens={token_usage or 0})"
        )
        
        return message
    
    async def get_chat_history(
        self, 
        chat_id: UUID, 
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Retrieve chat message history.
        
        Returns all messages for a chat in chronological order (oldest first).
        Useful for displaying conversation history or building context for
        the LLM.
        
        Implements Requirement 17.4-17.5 (chat history endpoint).
        
        Args:
            chat_id: UUID of the chat session
            limit: Optional maximum number of messages to return
            
        Returns:
            List of Message instances in chronological order
            
        Example:
            # Get all messages
            history = await service.get_chat_history(chat_id=chat_uuid)
            
            # Get last 50 messages
            recent = await service.get_chat_history(
                chat_id=chat_uuid,
                limit=50
            )
        """
        messages = await self.message_repo.get_chat_history(chat_id, limit)
        
        logger.info(
            f"Retrieved {len(messages)} messages for chat {chat_id}"
            + (f" (limited to {limit})" if limit else "")
        )
        
        return messages
    
    async def aggregate_user_messages(
        self, 
        chat_id: UUID, 
        after_timestamp: datetime
    ) -> str:
        """
        Aggregate multiple user messages into single input.
        
        Implements WhatsApp-style multi-message handling (Requirements 5.1-5.6).
        When users send multiple messages in quick succession, this method
        retrieves all unprocessed user messages and combines them into a
        single input string for the LangGraph agent.
        
        The aggregation preserves message order and combines messages with
        newlines to maintain context. Individual messages remain stored
        separately in the database.
        
        Args:
            chat_id: UUID of the chat session
            after_timestamp: Retrieve messages created after this time
            
        Returns:
            Aggregated message content as single string.
            Returns empty string if no messages found.
            Returns single message content if only one message.
            Returns newline-joined content if multiple messages.
            
        Example:
            # User sends three quick messages:
            # 1. "I want to book"
            # 2. "a tennis court"
            # 3. "for tomorrow afternoon"
            
            last_bot_message_time = datetime(2024, 1, 10, 10, 0, 0)
            aggregated = await service.aggregate_user_messages(
                chat_id=chat_uuid,
                after_timestamp=last_bot_message_time
            )
            
            # Result: "I want to book\na tennis court\nfor tomorrow afternoon"
        """
        # Retrieve unprocessed user messages
        messages = await self.message_repo.get_unprocessed_user_messages(
            chat_id, after_timestamp
        )
        
        if not messages:
            logger.debug(
                f"No unprocessed user messages for chat {chat_id} "
                f"after {after_timestamp}"
            )
            return ""
        
        # Single message - return as-is
        if len(messages) == 1:
            logger.info(
                f"Single user message for chat {chat_id}: "
                f"{messages[0].content[:50]}..."
            )
            return messages[0].content
        
        # Multiple messages - aggregate with newlines
        aggregated = "\n".join([msg.content for msg in messages])
        
        logger.info(
            f"Aggregated {len(messages)} user messages for chat {chat_id}: "
            f"{aggregated[:100]}..."
        )
        
        return aggregated
