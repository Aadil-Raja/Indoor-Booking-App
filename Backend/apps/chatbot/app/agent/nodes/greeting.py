"""
Greeting handler node for LangGraph conversation management.

This module implements the greeting_handler node that responds to greeting intents.
It generates contextual greetings based on session history, differentiating between
new users (first message) and returning users (continuing conversation).

For new users, it fetches and displays property information to introduce the facility.

Requirements: 6.1, 21.1
"""

from typing import Optional, Dict, Any
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.agent.tools import TOOL_REGISTRY

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
    - New users: First message in the conversation (fetches property info to introduce facility)
    - Returning users: Continuing an existing conversation (has message history)
    
    For new users, it fetches property details and displays them in a rich format
    with property name, address, city, and map link.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with Greeting handler node
    - 21.1: Route greeting messages to Greeting node
    
    Args:
        state: ConversationState containing user message and bot_memory
        chat_service: Optional ChatService for dependency injection (unused in this node)
        message_service: Optional MessageService for dependency injection (unused in this node)
        
    Returns:
        ConversationState: State with response_content, response_type, and response_metadata set
    """
    chat_id = state["chat_id"]
    owner_profile_id = state["owner_profile_id"]
    bot_memory = state.get("bot_memory", {})
    
    logger.info(f"Processing greeting for chat {chat_id}")
    
    # Check if this is a returning user by examining bot_memory
    is_returning = _is_returning_user(bot_memory)
    
    # Generate contextual greeting based on user type
    if is_returning:
        response = _generate_returning_user_greeting(bot_memory)
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        logger.debug(f"Generated returning user greeting for chat {chat_id}")
    else:
        # New user - fetch property details and create rich greeting
        properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        
        if properties:
            # Generate rich greeting with property information
            response, response_type, metadata = _generate_new_user_greeting_with_properties(properties)
            state["response_content"] = response
            state["response_type"] = response_type
            state["response_metadata"] = metadata
            logger.debug(f"Generated new user greeting with {len(properties)} properties for chat {chat_id}")
        else:
            # Fallback to simple greeting if no properties found
            response = _generate_new_user_greeting()
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            logger.debug(f"Generated simple new user greeting (no properties) for chat {chat_id}")
    
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
    Generate a simple greeting for a new user (fallback).
    
    This greeting introduces the bot and explains what it can do,
    helping new users understand the available functionality.
    Used as fallback when property information is not available.
    
    Returns:
        str: Greeting message for new users
    """
    return (
        "Hello! I'm your sports booking assistant. "
        "I can help you find and book indoor sports facilities. "
        "What would you like to do today?"
    )


async def _fetch_owner_properties(owner_profile_id: str, chat_id: str) -> list:
    """
    Fetch properties for the owner to display in greeting.
    
    Args:
        owner_profile_id: Owner profile ID
        chat_id: Chat ID for logging
        
    Returns:
        List of property dictionaries with details
    """
    try:
        # Get the property tool from registry
        get_owner_properties = TOOL_REGISTRY.get("get_owner_properties")
        
        if not get_owner_properties:
            logger.warning(f"get_owner_properties tool not found for chat {chat_id}")
            return []
        
        # Fetch properties
        properties = await get_owner_properties(owner_profile_id=int(owner_profile_id))
        
        logger.info(f"Fetched {len(properties)} properties for greeting in chat {chat_id}")
        return properties
        
    except Exception as e:
        logger.error(f"Error fetching properties for greeting in chat {chat_id}: {e}", exc_info=True)
        return []


def _generate_new_user_greeting_with_properties(properties: list) -> tuple:
    """
    Generate a rich greeting with property information for new users.
    
    Creates a personalized welcome message that introduces the facility
    with property name, address, city, and map link.
    
    Args:
        properties: List of property dictionaries
        
    Returns:
        Tuple of (response_content, response_type, response_metadata)
    """
    if not properties:
        return _generate_new_user_greeting(), "text", {}
    
    # Get the first property (or primary property)
    property_info = properties[0]
    
    property_name = property_info.get("name", "our facility")
    address = property_info.get("address", "")
    city = property_info.get("city", "")
    state_name = property_info.get("state", "")
    maps_link = property_info.get("maps_link", "")
    
    # Build location string
    location_parts = []
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if state_name:
        location_parts.append(state_name)
    
    location = ", ".join(location_parts) if location_parts else "our location"
    
    # Create greeting message with proper formatting
    greeting_text = f"Welcome to {property_name}!\n\n"
    greeting_text += "I'm your booking assistant, here to help you find and reserve sports facilities.\n\n"
    
    # Add location information
    greeting_text += f"Location: {location}\n"
    
    # Add map link if available
    if maps_link:
        greeting_text += f"View on map: {maps_link}\n"
    
    greeting_text += "\nHow can I help you today? I can:\n"
    greeting_text += "• Show you available courts and facilities\n"
    greeting_text += "• Help you make a booking\n"
    greeting_text += "• Answer questions about pricing and availability"
    
    # If multiple properties, mention them
    if len(properties) > 1:
        greeting_text += f"\n\nWe have {len(properties)} facilities available for you to explore!"
    
    return greeting_text, "text", {}


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
