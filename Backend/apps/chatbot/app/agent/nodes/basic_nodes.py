"""
Basic flow nodes for LangGraph.

One node that runs first:
1. load_chat - Loads chat history from database
"""

from typing import Dict, Any
import logging
from datetime import datetime

from app.agent.state.conversation_state import ConversationState
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


async def load_chat(
    state: ConversationState,
    chat_service: ChatService = None,
    message_service: MessageService = None
) -> ConversationState:
    """
    Load chat history from database.
    
    Loads last 20 messages (including current one) and formats for LLM.
    """
    chat_id = state["chat_id"]
    logger.info(f"Loading chat history for {chat_id}")
    
    if message_service:
        try:
            from uuid import UUID
            chat_uuid = UUID(chat_id)
            
            # Get last 20 messages (includes current message saved before graph)
            messages = await message_service.get_chat_history(chat_id=chat_uuid, limit=20)
            
            # Format for LLM (role + content)
            formatted_messages = []
            for msg in messages:
                role = "user" if msg.sender_type == "user" else "assistant"
                if msg.sender_type == "system":
                    role = "system"
                
                formatted_messages.append({"role": role, "content": msg.content})
            
            state["messages"] = formatted_messages
            logger.info(f"Loaded {len(formatted_messages)} messages")
            
        except Exception as e:
            logger.error(f"Error loading history: {e}", exc_info=True)
            state["messages"] = []
    
    return state
