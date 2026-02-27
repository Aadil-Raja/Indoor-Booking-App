"""
LangGraph nodes for conversation flow management.

This package contains all node implementations for the LangGraph agent.
Nodes are async functions that take ConversationState and return updated state.

Basic Flow Nodes:
- receive_message: Entry point that receives and validates user messages
- load_chat: Loads chat history and context from database
- append_user_message: Adds user message to conversation history

Intent Detection:
- intent_detection: Classifies user intent (greeting, search, booking, faq)

Handler Nodes:
- greeting_handler: Responds to greeting intents with contextual messages

Future nodes will include:
- Additional handler nodes (search, FAQ)
- Booking subgraph nodes
"""

from .basic_nodes import (
    receive_message,
    load_chat,
    append_user_message
)
from .intent_detection import intent_detection
from .greeting import greeting_handler

__all__ = [
    "receive_message",
    "load_chat",
    "append_user_message",
    "intent_detection",
    "greeting_handler",
]
