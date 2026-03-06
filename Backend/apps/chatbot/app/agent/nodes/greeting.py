"""
Greeting handler node for LangGraph conversation management.

This module implements the greeting_handler node that initializes conversation state
and responds to greeting intents. It generates contextual greetings based on session
history, differentiating between new users (first message) and returning users
(continuing conversation).

For new users, it fetches and displays property information to introduce the facility,
and caches the fetched properties in flow_state.owner_properties for later use in
the booking flow. This ensures properties are available for both display and booking
without redundant API calls.

The greeting handler initializes flow_state and bot_memory but does NOT make routing
decisions - intent detection handles routing to the appropriate next node.

This node uses rule-based logic and does not require LangChain agents or tools,
as greetings are deterministic based on user state. While the node accepts an
llm_provider parameter for consistency with other nodes, it does not use LangChain
or make any LLM calls.

Requirements: 5.1, 5.2, 5.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

from typing import Optional, Dict, Any
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.tools import TOOL_REGISTRY
from app.agent.state.flow_state_manager import initialize_flow_state, validate_flow_state
from app.agent.state.memory_manager import _initialize_bot_memory, _ensure_bot_memory_structure

logger = logging.getLogger(__name__)


async def greeting_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle greeting intents with contextual responses and state initialization.
    
    This node initializes conversation state (flow_state and bot_memory) and generates
    friendly, contextual greetings based on the user's conversation history.
    
    It differentiates between:
    - New users: First message in the conversation (fetches property info to introduce facility)
    - Returning users: Continuing an existing conversation (has message history)
    
    For new users, it fetches property details, displays them in a rich format
    with property name, address, city, and map link, and caches the fetched properties
    in flow_state.owner_properties for later use in the booking flow. This ensures
    properties are available for both display and booking without redundant API calls.
    
    IMPORTANT: This node does NOT make routing decisions. Intent detection handles
    routing to the appropriate next node based on user intent.
    
    This node follows the standard LangGraph node pattern:
    1. Initialize flow_state and bot_memory if needed
    2. Extract state (user_message, bot_memory, flow_state)
    3. Process (generate contextual greeting)
    4. Return updated state (response_content, response_type, response_metadata)
    
    Note: This node does not use LangChain agents or tools as greeting generation
    is rule-based and deterministic. The llm_provider parameter is accepted for
    consistency with other nodes but is not used.
    
    Implements Requirements:
    - 5.1: Fetch owner_properties in greeting handler
    - 5.2: Display available properties to user in greeting message
    - 5.3: Cache fetched properties in flow_state.owner_properties
    - 10.1: Initialize Flow_State when a conversation begins
    - 10.2: Initialize Bot_Memory when a conversation begins
    - 10.3: Set up conversation context for subsequent nodes
    - 10.4: First node to process message when user starts conversation
    - 10.5: Remain as separate node in conversation flow
    - 10.6: Introduce assistant and present available properties
    
    Args:
        state: ConversationState containing user message and bot_memory
        llm_provider: Optional LLMProvider (not used in this node)
        
    Returns:
        ConversationState: State with initialized flow_state, bot_memory, and greeting response
    """
    # 1. Initialize flow_state if not present or invalid (Requirement 10.1)
    flow_state = state.get("flow_state", {})
    if not flow_state or not validate_flow_state(flow_state):
        logger.info(f"Initializing flow_state for chat {state['chat_id']}")
        state["flow_state"] = initialize_flow_state()
        flow_state = state["flow_state"]
    
    # 2. Initialize bot_memory if not present (Requirement 10.2)
    bot_memory = state.get("bot_memory", {})
    if not bot_memory or not isinstance(bot_memory, dict):
        logger.info(f"Initializing bot_memory for chat {state['chat_id']}")
        state["bot_memory"] = _initialize_bot_memory()
        bot_memory = state["bot_memory"]
    else:
        # Ensure bot_memory has proper structure
        state["bot_memory"] = _ensure_bot_memory_structure(bot_memory)
        bot_memory = state["bot_memory"]
    
    # 3. Set up conversation context (Requirement 10.3)
    chat_id = state["chat_id"]
    owner_profile_id = state["owner_profile_id"]
    
    logger.info(f"Processing greeting for chat {chat_id}")
    
    # 4. Process - Generate contextual greeting
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
        # New user - fetch owner profile and property details (Requirement 10.6)
        owner_profile = await _fetch_owner_profile(owner_profile_id, chat_id)
        properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        
        # Cache fetched properties in flow_state for later use (Requirements 5.1, 5.2, 5.3)
        if properties:
            flow_state["owner_properties"] = properties
            logger.info(f"Cached {len(properties)} properties in flow_state for chat {chat_id}")
        
        if properties:
            # Generate rich greeting with business_name and property information
            response, response_type, metadata = _generate_new_user_greeting_with_properties(
                owner_profile, properties
            )
            state["response_content"] = response
            state["response_type"] = response_type
            state["response_metadata"] = metadata
            logger.debug(f"Generated new user greeting with {len(properties)} properties for chat {chat_id}")
        else:
            # Fallback to simple greeting if no properties found
            response = _generate_new_user_greeting(owner_profile)
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            logger.debug(f"Generated simple new user greeting (no properties) for chat {chat_id}")
    
    # 5. Return updated state
    # NOTE: This node does NOT set next_node - intent detection handles routing
    logger.info(
        f"Greeting handler completed for chat {chat_id} - "
        f"is_returning={is_returning}, flow_state initialized, bot_memory initialized"
    )
    
    return state


def _is_returning_user(bot_memory: dict) -> bool:
    """
    Determine if the user is returning based on bot_memory.
    
    A user is considered returning if they have:
    - Conversation history with more than just the current user message
      (append_user_message runs before greeting, so 1 message = new user)
    
    Args:
        bot_memory: The bot_memory dict from ConversationState
        
    Returns:
        bool: True if returning user, False if new user
    """
    # Check conversation history
    # Note: append_user_message runs before greeting_handler, so the current
    # user message has already been added to conversation_history.
    # - 1 message = new user (just the current "hi")
    # - 2+ messages = returning user (has previous conversation)
    conversation_history = bot_memory.get("conversation_history", [])
    
    if len(conversation_history) > 1:
        logger.debug(f"Returning user detected: {len(conversation_history)} messages in history")
        return True
    
    logger.debug("New user detected: first message")
    return False


def _generate_new_user_greeting(owner_profile: dict) -> str:
    """
    Generate a simple greeting for a new user (fallback).
    
    This greeting introduces the bot and explains what it can do,
    helping new users understand the available functionality.
    Used as fallback when property information is not available.
    
    Args:
        owner_profile: Owner profile dictionary with business_name
    
    Returns:
        str: Greeting message for new users
    """
    business_name = owner_profile.get("business_name") or "our facility"
    
    return (
        f"Hello! I am {business_name}'s assistant. "
        "I can show you indoors and courts where you can play futsal, cricket, etc. "
        "What would you like to do today?"
    )


async def _fetch_owner_profile(owner_profile_id: str, chat_id: str) -> dict:
    """
    Fetch owner profile to get business_name and other details.
    
    Args:
        owner_profile_id: Owner profile ID
        chat_id: Chat ID for logging
        
    Returns:
        Dictionary with owner profile data including business_name
    """
    try:
        # Validate owner_profile_id
        try:
            profile_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return {"business_name": "our facility"}  # Default fallback
        
        from sqlalchemy.orm import Session
        from shared.models import OwnerProfile
        from app.agent.tools.sync_bridge import call_sync_service
        
        def get_owner_profile_sync(db: Session, profile_id: int) -> dict:
            """Sync function to fetch owner profile"""
            profile = db.query(OwnerProfile).filter(OwnerProfile.id == profile_id).first()
            if profile:
                return {
                    "id": profile.id,
                    "business_name": profile.business_name or "our facility",  # Fallback
                    "phone": profile.phone,
                    "address": profile.address,
                    "verified": profile.verified
                }
            return {"business_name": "our facility"}  # Default if not found
        
        # Call sync service using the bridge
        profile_data = await call_sync_service(
            get_owner_profile_sync,
            db=None,  # Auto-managed by sync bridge
            profile_id=profile_id
        )
        
        logger.info(f"Fetched owner profile for owner_profile_id={owner_profile_id} in chat {chat_id}")
        return profile_data
        
    except Exception as e:
        logger.error(f"Error fetching owner profile for greeting in chat {chat_id}: {e}", exc_info=True)
        return {"business_name": "our facility"}  # Fallback on error


async def _fetch_owner_properties(owner_profile_id: str, chat_id: str) -> list:
    """
    Fetch properties for the owner to display in greeting and cache in flow_state.
    
    This function retrieves all properties owned by the owner profile using the
    get_owner_properties tool. The fetched properties are displayed to the user
    in the greeting message and cached in flow_state.owner_properties for later
    use in the booking flow, ensuring no redundant API calls.
    
    Args:
        owner_profile_id: Owner profile ID
        chat_id: Chat ID for logging
        
    Returns:
        List of property dictionaries with details (id, name, address, city, etc.)
        
    Requirements: 5.1, 5.2, 5.3
    """
    try:
        # Validate owner_profile_id
        try:
            owner_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return []
        
        # Get the property tool from registry
        get_owner_properties = TOOL_REGISTRY.get("get_owner_properties")
        
        if not get_owner_properties:
            logger.warning(f"get_owner_properties tool not found for chat {chat_id}")
            return []
        
        # Fetch properties with error handling
        properties = await get_owner_properties(owner_profile_id=owner_id)
        
        if not isinstance(properties, list):
            logger.warning(f"Invalid properties response type: {type(properties)}")
            return []
        
        logger.info(f"Fetched {len(properties)} properties for greeting in chat {chat_id}")
        return properties
        
    except Exception as e:
        logger.error(f"Error fetching properties for greeting in chat {chat_id}: {e}", exc_info=True)
        return []


def _generate_new_user_greeting_with_properties(owner_profile: dict, properties: list) -> tuple:
    """
    Generate a rich greeting with property information for new users.
    
    Creates a personalized welcome message that introduces the facility
    with business_name, property name, address, city, and map link.
    
    Args:
        owner_profile: Owner profile dictionary with business_name
        properties: List of property dictionaries
        
    Returns:
        Tuple of (response_content, response_type, response_metadata)
    """
    if not properties:
        return _generate_new_user_greeting(owner_profile), "text", {}
    
    # Get business_name from owner profile
    business_name = owner_profile.get("business_name") or "our facility"
    
    # Create greeting message with business_name personalization
    greeting_text = f"Hello, I am {business_name}'s assistant. I can show you indoors and courts where you can play futsal, cricket, etc.\n\n"
    
    # Add available properties information
    greeting_text += "Here are our available facilities:\n\n"
    
    for idx, property_info in enumerate(properties, 1):
        property_name = property_info.get("name", "Facility")
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
        
        location = ", ".join(location_parts) if location_parts else "Location not specified"
        
        # Add property information
        greeting_text += f"{idx}. {property_name}\n"
        greeting_text += f"   Location: {location}\n"
        
        # Add map link if available
        if maps_link:
            greeting_text += f"   View on map: {maps_link}\n"
        
        greeting_text += "\n"
    
    greeting_text += "How can I help you today? I can:\n"
    greeting_text += "• Show you available courts and facilities\n"
    greeting_text += "• Help you make a booking\n"
    greeting_text += "• Answer questions about pricing and availability"
    
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
