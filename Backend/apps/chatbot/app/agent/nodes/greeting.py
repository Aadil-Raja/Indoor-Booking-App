"""
Greeting handler node for LangGraph conversation management.

This module implements the greeting_handler node that responds to greeting intents.
It generates contextual greetings based on session history, differentiating between
new users (first message) and returning users (continuing conversation).

Requirements: 6.1, 21.1
"""

from typing import Optional
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.chat_service import ChatService
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)


async def greeting_handler(
    state: ConversationState,
    chat_service: Optional[ChatService] = None,
    message_service: Optional[MessageService] = None
) -> ConversationState:
    """
    Handle greeting intents with contextual responses.
    
    This node generates friendly, contextual greetings based on the user's
    conversation history. It differentiates between:
    - New users: First message in the conversation (no history in bot_memory)
    - Returning users: Continuing an existing conversation (has message history)
    
    The node checks bot_memory to determine if this is a new or returning user
    and generates an appropriate greeting message. It sets response_content,
    response_type, and response_metadata in the state.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with Greeting handler node
    - 21.1: Route greeting messages to Greeting node
    
    Args:
        state: ConversationState containing user message and bot_memory
        chat_service: Optional ChatService for dependency injection (unused in this node)
        message_service: Optional MessageService for dependency injection (unused in this node)
        
    Returns:
        ConversationState: State with response_content, response_type, and response_metadata set
        
    Example:
        # New user
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "Hello",
            "bot_memory": {},
            ...
        }
        result = await greeting_handler(state)
        # result["response_content"] = "Hello! I'm your sports booking assistant..."
        
        # Returning user
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "Hi again",
            "bot_memory": {
                "conversation_history": [
                    {"role": "user", "content": "Hello", "timestamp": "..."},
                    {"role": "assistant", "content": "Hi!", "timestamp": "..."}
                ]
            },
            ...
        }
        result = await greeting_handler(state)
        # result["response_content"] = "Welcome back! How can I help you today?..."
    """
    chat_id = state["chat_id"]
    bot_memory = state.get("bot_memory", {})
    
    logger.info(f"Processing greeting for chat {chat_id}")
    
    # Check if this is a returning user by examining bot_memory
    # A returning user will have conversation history or session metadata
    is_returning = _is_returning_user(bot_memory)
    
    # Generate contextual greeting based on user type
    if is_returning:
        response = _generate_returning_user_greeting(bot_memory)
        logger.debug(f"Generated returning user greeting for chat {chat_id}")
    else:
        response = _generate_new_user_greeting()
        logger.debug(f"Generated new user greeting for chat {chat_id}")
    
    # Set response in state
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(
        f"Greeting handler completed for chat {chat_id} - "
        f"is_returning={is_returning}"
    )
    
    return state


def _is_returning_user(bot_memory: dict) -> bool:
    """
    Determine if the user is returning based on bot_memory.
    
    A user is considered returning if they have:
    - Conversation history with more than just the current greeting
    - Session metadata indicating previous messages
    - User preferences from previous interactions
    - Context from previous searches
    
    Args:
        bot_memory: The bot_memory dict from ConversationState
        
    Returns:
        bool: True if returning user, False if new user
    """
    # Check conversation history
    conversation_history = bot_memory.get("conversation_history", [])
    
    # If there's more than 1 message in history (current greeting was just added),
    # this is a returning user
    if len(conversation_history) > 1:
        return True
    
    # Check session metadata for total messages
    session_metadata = bot_memory.get("session_metadata", {})
    total_messages = session_metadata.get("total_messages", 0)
    
    if total_messages > 0:
        return True
    
    # Check if there are user preferences (indicates previous interaction)
    user_preferences = bot_memory.get("user_preferences", {})
    if user_preferences:
        return True
    
    # Check if there's any context from previous interactions
    context = bot_memory.get("context", {})
    if context.get("last_search_results") or context.get("mentioned_properties"):
        return True
    
    # No indicators of previous interaction - this is a new user
    return False


def _generate_new_user_greeting() -> str:
    """
    Generate a greeting for a new user.
    
    This greeting introduces the bot and explains what it can do,
    helping new users understand the available functionality.
    
    Returns:
        str: Greeting message for new users
    """
    return (
        "Hello! I'm your sports booking assistant. "
        "I can help you find and book indoor sports facilities. "
        "What would you like to do today?"
    )


def _generate_returning_user_greeting(bot_memory: dict) -> str:
    """
    Generate a contextual greeting for a returning user.
    
    This greeting acknowledges the user's return and offers assistance,
    optionally referencing previous context if available.
    
    Args:
        bot_memory: The bot_memory dict containing conversation context
        
    Returns:
        str: Contextual greeting message for returning users
    """
    # Check if there's context about previous searches or preferences
    context = bot_memory.get("context", {})
    user_preferences = bot_memory.get("user_preferences", {})
    
    # Base returning user greeting
    greeting = "Welcome back! How can I help you today?"
    
    # Add contextual information if available
    if user_preferences.get("preferred_sport"):
        sport = user_preferences["preferred_sport"]
        greeting = (
            f"Welcome back! Looking for more {sport} facilities, "
            f"or can I help you with something else?"
        )
    elif context.get("last_search_results"):
        greeting = (
            "Welcome back! Would you like to continue with your previous search, "
            "or start something new?"
        )
    else:
        # Generic returning user greeting with helpful options
        greeting = (
            "Welcome back! How can I help you today? "
            "I can help you search for sports facilities or make a booking."
        )
    
    return greeting
