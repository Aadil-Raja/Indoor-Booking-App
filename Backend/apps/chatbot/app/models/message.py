"""
Message model for storing individual chat messages.

This model stores all messages in a conversation, including user messages,
bot responses, and system messages. Supports multiple message types
(text, button, list, media) and tracks token usage for cost monitoring.
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from shared.models.base import Base


class Message(Base):
    """
    Message model.
    
    Represents individual messages within a chat session. Stores message
    content, metadata for rich message types, and token usage for LLM calls.
    
    Attributes:
        id: Unique message identifier
        chat_id: Foreign key to chat session
        sender_type: Message sender (user, bot, system)
        message_type: Message format (text, button, list, media)
        content: Message text content
        metadata: JSONB for message-specific data (buttons, lists, media URLs)
        token_usage: LLM token count for cost tracking (nullable)
        created_at: Message creation timestamp
    """
    __tablename__ = "messages"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique message identifier"
    )
    
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey('chats.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Foreign key to chat session"
    )
    
    sender_type = Column(
        String(20),
        nullable=False,
        comment="Message sender: user, bot, system"
    )
    
    message_type = Column(
        String(20),
        nullable=False,
        default="text",
        comment="Message format: text, button, list, media"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="Message text content"
    )
    
    message_metadata = Column(
        "metadata",  # Database column name
        JSONB,
        nullable=False,
        default=dict,
        comment="Message-specific data (buttons, lists, media URLs, etc.)"
    )
    
    token_usage = Column(
        Integer,
        nullable=True,
        comment="LLM token count for cost tracking"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Message creation timestamp"
    )
    
    # Index for efficient chat history retrieval
    __table_args__ = (
        Index(
            'idx_chat_created',
            'chat_id',
            'created_at',
            postgresql_using='btree'
        ),
    )
    
    def __repr__(self):
        return (
            f"<Message(id={self.id}, chat_id={self.chat_id}, "
            f"sender_type={self.sender_type}, message_type={self.message_type})>"
        )
