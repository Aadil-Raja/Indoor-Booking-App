"""
Chat and Message Pydantic schemas for request/response validation.

This module defines schemas for:
- Chat session CRUD operations
- Message CRUD operations
- API endpoint request/response models

These schemas are used by FastAPI endpoints to validate incoming data
and serialize responses, ensuring type safety and data consistency.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatBase(BaseModel):
    """Base schema for chat with common fields."""
    user_id: UUID = Field(..., description="User ID participating in the chat")
    owner_id: UUID = Field(..., description="Owner ID whose properties are being discussed")


class ChatCreate(ChatBase):
    """Schema for creating a new chat session."""
    pass


class ChatUpdate(BaseModel):
    """Schema for updating an existing chat session."""
    status: Optional[str] = Field(None, description="Chat status: active, closed")
    last_message_at: Optional[datetime] = Field(None, description="Timestamp of last message")
    flow_state: Optional[Dict[str, Any]] = Field(None, description="Structured booking state")
    bot_memory: Optional[Dict[str, Any]] = Field(None, description="Unstructured AI context")


class ChatResponse(ChatBase):
    """Schema for chat session response."""
    id: UUID = Field(..., description="Unique chat identifier")
    status: str = Field(..., description="Chat status: active, closed")
    last_message_at: datetime = Field(..., description="Timestamp of last message")
    flow_state: Dict[str, Any] = Field(..., description="Structured booking state")
    created_at: datetime = Field(..., description="Chat creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Message Schemas
# ============================================================================

class MessageBase(BaseModel):
    """Base schema for message with common fields."""
    chat_id: UUID = Field(..., description="Chat session ID")
    sender_type: str = Field(..., description="Message sender: user, bot, system")
    message_type: str = Field(default="text", description="Message format: text, button, list, media")
    content: str = Field(..., description="Message text content")
    message_metadata: Dict[str, Any] = Field(default_factory=dict, description="Message-specific data")
    token_usage: Optional[int] = Field(None, description="LLM token count for cost tracking")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: UUID = Field(..., description="Unique message identifier")
    created_at: datetime = Field(..., description="Message creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# API Endpoint Schemas
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Schema for incoming chat message API request."""
    user_id: UUID = Field(..., description="User ID sending the message")
    owner_id: UUID = Field(..., description="Owner ID whose properties are being discussed")
    content: str = Field(..., description="Message content from user", min_length=1)


class ChatMessageResponse(BaseModel):
    """Schema for chat message API response."""
    chat_id: UUID = Field(..., description="Chat session ID")
    message_id: UUID = Field(..., description="Bot message ID")
    content: str = Field(..., description="Bot response content")
    message_type: str = Field(..., description="Message format: text, button, list, media")
    message_metadata: Dict[str, Any] = Field(..., description="Message-specific data (buttons, lists, etc.)")


class ChatHistoryResponse(BaseModel):
    """Schema for chat history API response."""
    chat_id: UUID = Field(..., description="Chat session ID")
    messages: list[MessageResponse] = Field(..., description="List of messages in chronological order")


class ChatSummary(BaseModel):
    """Schema for chat summary in list view."""
    chat_id: UUID = Field(..., description="Chat session ID")
    owner_id: UUID = Field(..., description="Owner ID whose properties are being discussed")
    status: str = Field(..., description="Chat status: active, closed")
    last_message_at: datetime = Field(..., description="Timestamp of last message")
    last_message_preview: Optional[str] = Field(None, description="Preview of last message content")
    last_message_sender: Optional[str] = Field(None, description="Sender of last message: user, bot, system")


class ChatListResponse(BaseModel):
    """Schema for chat list API response."""
    chats: list[ChatSummary] = Field(..., description="List of chat summaries ordered by last_message_at descending")
