"""
Pydantic schemas for the chatbot application.

This module exports all schema classes for easy importing throughout the application.
"""

from .chat import (
    # Chat schemas
    ChatBase,
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    # Message schemas
    MessageBase,
    MessageCreate,
    MessageResponse,
    # API endpoint schemas
    ChatMessageRequest,
    ChatMessageResponse,
)

__all__ = [
    # Chat schemas
    "ChatBase",
    "ChatCreate",
    "ChatUpdate",
    "ChatResponse",
    # Message schemas
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    # API endpoint schemas
    "ChatMessageRequest",
    "ChatMessageResponse",
]
