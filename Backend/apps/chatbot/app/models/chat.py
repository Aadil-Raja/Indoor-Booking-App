"""
Chat model for storing conversation sessions.

This model tracks chat sessions between users and property owners,
maintaining conversation state and bot memory for context persistence.
"""

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from shared.models.base import Base


class Chat(Base):
    """
    Chat session model.
    
    Represents a conversation thread between a user and a property owner.
    Stores structured flow state for booking progress and unstructured
    bot memory for AI context.
    
    Attributes:
        id: Unique chat identifier
        user_id: Reference to user (no FK constraint - separate database)
        owner_id: Reference to owner (no FK constraint - separate database)
        status: Chat status (active, closed)
        last_message_at: Timestamp of last message for session continuity
        flow_state: Structured JSONB for booking progress tracking
        bot_memory: Unstructured JSONB for AI conversation context
        created_at: Chat creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "chats"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique chat identifier"
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User ID (reference only, no FK)"
    )
    
    owner_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Owner ID (reference only, no FK)"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="Chat status: active, closed"
    )
    
    last_message_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of last message for session continuity"
    )
    
    flow_state = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Structured booking state (property_id, service_id, date, time, etc.)"
    )
    
    bot_memory = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Unstructured AI context and conversation history"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Chat creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )
    
    # Indexes for efficient queries
    __table_args__ = (
        Index(
            'idx_user_owner_last_message',
            'user_id',
            'owner_id',
            'last_message_at',
            postgresql_using='btree'
        ),
        Index(
            'idx_status',
            'status',
            postgresql_using='btree'
        ),
    )
    
    def __repr__(self):
        return (
            f"<Chat(id={self.id}, user_id={self.user_id}, "
            f"owner_id={self.owner_id}, status={self.status})>"
        )
