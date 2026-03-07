"""
Greeting handler - welcomes users and displays properties.

New users: Fetches and displays properties
Returning users: Simple welcome back message

Note: flow_state and bot_memory are initialized by agent_service.
"""

from typing import Optional, Dict, Any
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def greeting_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle greetings and display properties.
    
    New users: Fetch properties and show welcome with facility list
    Returning users: Simple welcome back message
    
    Note: flow_state and bot_memory already initialized by agent_service.
    """
    # 1. Get flow_state (already initialized by agent_service)
    flow_state = state.get("flow_state", {})
    
    # 2. Get bot_memory (already initialized by agent_service)
    bot_memory = state.get("bot_memory", {})
    
    # 3. Extract context
    chat_id = state["chat_id"]
    owner_profile_id = state["owner_profile_id"]
    
    logger.info(f"Processing greeting for chat {chat_id}")
    
    # 4. Process - Generate contextual greeting
    # Check if this is a returning user by examining message history
    is_returning = _is_returning_user(state)
    
    # Generate contextual greeting based on user type
    if is_returning:
        response = _generate_returning_user_greeting(bot_memory)
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        logger.debug(f"Generated returning user greeting for chat {chat_id}")
    else:
        # New user - fetch properties to display
        owner_profile = await _fetch_owner_profile(owner_profile_id, chat_id)
        properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        
        # Cache properties for booking flow
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
    
    # 5. Track last node and return
    state["flow_state"]["last_node"] = "greeting"
    
    logger.info(f"Greeting completed for chat {chat_id} - is_returning={is_returning}")
    
    return state


def _is_returning_user(state: dict) -> bool:
    """
    Check if user is returning based on message history.
    
    Returns True if more than 1 message in history.
    Uses state["messages"] loaded from database by load_chat node.
    """
    messages = state.get("messages", [])
    return len(messages) > 1


def _generate_new_user_greeting(owner_profile: dict) -> str:
    """
    Generate simple greeting for new user (fallback when no properties).
    """
    business_name = owner_profile.get("business_name") or "our facility"
    
    return (
        f"Hello! I am {business_name}'s assistant. "
        "I can show you indoors and courts where you can play futsal, cricket, etc. "
        "What would you like to do today?"
    )


async def _fetch_owner_profile(owner_profile_id: str, chat_id: str) -> dict:
    """
    Fetch owner profile for business_name.
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
    Fetch owner's properties to display in greeting.
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
    Generate rich greeting with property list for new users.
    
    Returns: (response_content, response_type, response_metadata)
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
    Generate contextual greeting for returning user.
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
