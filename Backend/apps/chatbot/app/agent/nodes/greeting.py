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
from app.agent.utils.llm_logger import get_llm_logger

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
    # Check if properties already initialized (returning user)
    owner_properties_initialized = flow_state.get("owner_properties_initialized", False)
    
    # Generate contextual greeting based on user type
    if owner_properties_initialized:
        # Returning user - properties already fetched
        response = _generate_returning_user_greeting(bot_memory, flow_state)
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        logger.debug(f"Generated returning user greeting for chat {chat_id}")
    else:
        # New user - fetch properties to display
        owner_profile = await _fetch_owner_profile(owner_profile_id, chat_id)
        properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        
        # Cache properties for booking flow (always cache, even if empty list)
        flow_state["available_properties"] = properties
        flow_state["owner_properties_initialized"] = True
        
        logger.info(f"Cached {len(properties)} properties in flow_state for chat {chat_id}")
        
        # Fetch and cache court details for all properties
        all_courts = []
        for prop in properties:
            prop_id = prop.get("id")
            if prop_id:
                prop_details = await _fetch_property_details(prop_id, chat_id)
                if prop_details and "courts" in prop_details:
                    courts = prop_details.get("courts", [])
                    # Extract only essential court details
                    for court in courts:
                        essential_court = _extract_essential_court_details(court, prop_id)
                        all_courts.append(essential_court)
        
        # Save all courts in available_courts
        flow_state["available_courts"] = all_courts
        logger.info(f"Cached {len(all_courts)} courts (essential details only) in flow_state for chat {chat_id}")
        
        if properties:
            # Generate greeting based on property count
            response, response_type, metadata = await _generate_new_user_greeting_with_properties(
                owner_profile, properties, flow_state, chat_id
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
    
    # 5. Update state with modified flow_state
    state["flow_state"] = flow_state
    
    # 6. Track last node
    state["flow_state"]["last_node"] = "greeting"
    
    # 7. Log greeting output (no LLM call, but log the generated response)
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        node_name="greeting",
        prompt="[No LLM call - greeting generated from templates]",
        response=state["response_content"],
        parameters=None
    )
    
    logger.info(
        f"Greeting completed for chat {chat_id} - "
        f"returning_user={owner_properties_initialized}"
    )
    
    return state


def _extract_essential_court_details(court: dict, property_id: int) -> dict:
    """
    Extract only essential court details to save in flow_state.
    
    Reduces memory usage by storing only necessary fields:
    - id: Court ID
    - name: Court name
    - property_id: Associated property ID
    - sport_types: Array of sport types (e.g., ["Futsal", "Cricket"])
    - description: Court description
    
    Args:
        court: Full court dictionary from API
        property_id: Property ID to associate with this court
        
    Returns:
        Dictionary with only essential court fields
    """
    return {
        "id": court.get("id"),
        "name": court.get("name"),
        "property_id": property_id,
        "sport_types": court.get("sport_types", []),
        "description": court.get("description")
    }


def _generate_new_user_greeting(owner_profile: dict) -> str:
    """
    Generate simple greeting for new user (fallback when no properties).
    
    Used when no properties are found - provides helpful message.
    """
    business_name = owner_profile.get("business_name") or "our facility"
    
    return (
        f"Hello! I am {business_name}'s assistant.\n\n"
        "⚠️ No facilities are currently available in our system. "
        "This might be because:\n"
        "• Facilities haven't been added yet\n"
        "• There's a temporary issue\n\n"
        "Please contact support or try again later."
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
        
        # Get the owner profile tool from registry
        get_owner_profile = TOOL_REGISTRY.get("get_owner_profile")
        
        if not get_owner_profile:
            logger.warning(f"get_owner_profile tool not found for chat {chat_id}")
            return {"business_name": "our facility"}
        
        # Fetch profile using tool
        profile_data = await get_owner_profile(owner_profile_id=profile_id)
        
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




async def _generate_new_user_greeting_with_properties(
    owner_profile: dict,
    properties: list,
    flow_state: dict,
    chat_id: str
) -> tuple:
    """
    Generate rich greeting with property list for new users.
    
    Handles three cases:
    - Multiple properties: Simple list
    - Single property: Full details + court types + auto-set property_id
    - Single property + single court: Auto-set both IDs
    
    Returns: (response_content, response_type, response_metadata)
    """
    if not properties:
        return _generate_new_user_greeting(owner_profile), "text", {}
    
    business_name = owner_profile.get("business_name") or "our facility"
    
    # Case 1: Multiple properties - show simple list
    if len(properties) > 1:
        return _generate_multi_property_greeting(business_name, properties), "text", {}
    
    # Case 2 & 3: Single property - fetch full details with courts
    property_info = properties[0]
    property_id = property_info.get("id")
    property_name = property_info.get("name", "Facility")
    
    # Auto-set property_id
    flow_state["property_id"] = property_id
    flow_state["property_name"] = property_name
    logger.info(f"Auto-set property_id={property_id} for single property in chat {chat_id}")
    
    # Fetch full property details (includes courts) in one call
    property_details = await _fetch_property_details(property_id, chat_id)
    
    if not property_details:
        # Failed to fetch details - show basic info
        return _generate_single_property_greeting(business_name, property_info, []), "text", {}
    
    # Extract courts from property details
    courts = property_details.get("courts", [])
    
    if not courts:
        # No courts found - show property details only
        return _generate_single_property_greeting(business_name, property_details, []), "text", {}
    
    # Case 3: Single property + single court - auto-set both
    if len(courts) == 1:
        court_info = courts[0]
        flow_state["court_id"] = court_info.get("id")
        # Use court name as court_type since a court can have multiple sport types
        flow_state["court_type"] = court_info.get("name", "Court")
        logger.info(
            f"Auto-set court_id={court_info.get('id')} for single court "
            f"in chat {chat_id}"
        )
        return _generate_single_property_single_court_greeting(
            business_name, property_details, court_info
        ), "text", {}
    
    # Case 2: Single property + multiple courts
    return _generate_single_property_greeting(
        business_name, property_details, courts
    ), "text", {}


def _generate_returning_user_greeting(bot_memory: dict, flow_state: dict) -> str:
    """
    Generate contextual greeting for returning user.
    
    Shows relevant info based on flow_state:
    - Case A: No property selected → show property list
    - Case B: Property selected → show that property details
    - Case C: Property + court selected → reference them by name
    
    Handles edge cases:
    - Data inconsistency (court without property)
    - Missing cached data
    """
    property_id = flow_state.get("property_id")
    court_id = flow_state.get("court_id")
    property_name = flow_state.get("property_name")
    court_type = flow_state.get("court_type")
    available_properties = flow_state.get("available_properties", [])
    
    # Edge case: Court selected but no property (data inconsistency)
    if court_id and not property_id:
        logger.warning("Data inconsistency: court_id set but property_id is None, clearing court")
        flow_state["court_id"] = None
        flow_state["court_type"] = None
        court_id = None
        court_type = None
    
    # Case C: Both property and court selected
    if property_id and court_id and property_name and court_type:
        return (
            f"Welcome back! I see you were looking at {property_name} - {court_type}. "
            f"Ready to continue with your booking?"
        )
    
    # Case B: Only property selected
    if property_id and available_properties:
        # Find property in cached list
        property_info = _find_property_by_id(available_properties, property_id)
        if property_info:
            return _generate_selected_property_greeting(property_info)
        elif property_name:
            # Edge case: Property not in cache but we have the name
            logger.warning(f"Property {property_id} not found in cache, using name fallback")
            return (
                f"Welcome back! Continuing with {property_name}. "
                f"How can I help you today?"
            )
    
    # Case A: No property selected - show property list if available
    if available_properties and len(available_properties) > 0:
        return _generate_property_selection_greeting(available_properties)
    
    # Fallback: Generic returning user greeting
    context = bot_memory.get("context", {})
    user_preferences = bot_memory.get("user_preferences", {})
    
    if user_preferences.get("preferred_sport"):
        sport = user_preferences["preferred_sport"]
        return (
            f"Welcome back! Looking for more {sport} facilities, "
            f"or can I help you with something else?"
        )
    elif context.get("last_search_results"):
        return (
            "Welcome back! Would you like to continue with your previous search, "
            "or start something new?"
        )
    else:
        return (
            "Welcome back! How can I help you today? "
            "I can help you search for sports facilities or make a booking."
        )
    return greeting



async def _fetch_property_details(property_id: int, chat_id: str) -> dict:
    """
    Fetch full property details including courts using tool.
    """
    try:
        # Get the tool from registry
        get_property_details_public = TOOL_REGISTRY.get("get_property_details_public")
        
        if not get_property_details_public:
            logger.warning(f"get_property_details_public tool not found for chat {chat_id}")
            return None
        
        # Fetch property details (includes courts)
        property_details = await get_property_details_public(property_id=property_id)
        
        if property_details:
            logger.info(f"Fetched property details for property_id={property_id} in chat {chat_id}")
        
        return property_details
        
    except Exception as e:
        logger.error(f"Error fetching property details for {property_id} in chat {chat_id}: {e}", exc_info=True)
        return None


def _generate_multi_property_greeting(business_name: str, properties: list) -> str:
    """
    Generate greeting for multiple properties - simple list.
    """
    greeting_text = f"Hello, I am {business_name}'s assistant. I can show you indoors and courts where you can play futsal, cricket, etc.\n\n"
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
    
    return greeting_text


def _generate_single_property_greeting(business_name: str, property_info: dict, courts: list) -> str:
    """
    Generate greeting for single property with court types.
    """
    property_name = property_info.get("name", "Facility")
    address = property_info.get("address", "")
    city = property_info.get("city", "")
    state_name = property_info.get("state", "")
    maps_link = property_info.get("maps_link", "")
    
    # Build location
    location_parts = []
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if state_name:
        location_parts.append(state_name)
    location = ", ".join(location_parts) if location_parts else "Location not specified"
    
    greeting_text = f"Hello, I am {business_name}'s assistant!\n\n"
    greeting_text += f"📍 {property_name}\n"
    greeting_text += f"Location: {location}\n"
    
    if maps_link:
        greeting_text += f"View on map: {maps_link}\n"
    
    # Add court types if available
    if courts:
        greeting_text += f"\n🏟️ Available Courts ({len(courts)}):\n"
        
        # List court names with their sport types
        for court in courts:
            court_name = court.get("name", "Unknown Court")
            sport_types = court.get("sport_types", [])
            sport_types_str = ", ".join(sport_types) if sport_types else ""
            
            if sport_types_str:
                greeting_text += f"• {court_name} ({sport_types_str})\n"
            else:
                greeting_text += f"• {court_name}\n"
    
    greeting_text += "\nHow can I help you today? I can:\n"
    greeting_text += "• Show you available courts\n"
    greeting_text += "• Help you make a booking\n"
    greeting_text += "• Answer questions about pricing and availability"
    
    return greeting_text


def _generate_single_property_single_court_greeting(business_name: str, property_info: dict, court_info: dict) -> str:
    """
    Generate greeting for single property with single court.
    """
    property_name = property_info.get("name", "Facility")
    court_name = court_info.get("name", "Court")
    sport_types = court_info.get("sport_types", [])
    sport_types_str = ", ".join(sport_types) if sport_types else ""
    address = property_info.get("address", "")
    city = property_info.get("city", "")
    state_name = property_info.get("state", "")
    maps_link = property_info.get("maps_link", "")
    
    # Build location
    location_parts = []
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if state_name:
        location_parts.append(state_name)
    location = ", ".join(location_parts) if location_parts else "Location not specified"
    
    greeting_text = f"Hello, I am {business_name}'s assistant!\n\n"
    greeting_text += f"📍 {property_name}\n"
    greeting_text += f"Location: {location}\n"
    
    if maps_link:
        greeting_text += f"View on map: {maps_link}\n"
    
    greeting_text += f"\n🏟️ Court: {court_name}"
    if sport_types_str:
        greeting_text += f" ({sport_types_str})"
    greeting_text += "\n"
    
    greeting_text += "\nHow can I help you today? I can:\n"
    greeting_text += "• Show you available time slots\n"
    greeting_text += "• Help you make a booking\n"
    greeting_text += "• Answer questions about pricing"
    
    return greeting_text



def _find_property_by_id(properties: list, property_id: int) -> dict:
    """
    Find property in list by ID.
    """
    for prop in properties:
        if prop.get("id") == property_id:
            return prop
    return None


def _generate_selected_property_greeting(property_info: dict) -> str:
    """
    Generate greeting showing details of selected property.
    """
    property_name = property_info.get("name", "your selected property")
    address = property_info.get("address", "")
    city = property_info.get("city", "")
    state_name = property_info.get("state", "")
    
    # Build location
    location_parts = []
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if state_name:
        location_parts.append(state_name)
    location = ", ".join(location_parts) if location_parts else ""
    
    greeting = f"Welcome back! Continuing with {property_name}"
    if location:
        greeting += f" ({location})"
    greeting += ". How can I help you today?"
    
    return greeting


def _generate_property_selection_greeting(properties: list) -> str:
    """
    Generate greeting with property list for selection.
    """
    if len(properties) == 1:
        # Single property - show details
        prop = properties[0]
        property_name = prop.get("name", "Facility")
        return f"Welcome back! Ready to book at {property_name}?"
    
    # Multiple properties - show simple list
    greeting = "Welcome back! Which facility would you like to book?\n\n"
    
    for idx, prop in enumerate(properties[:5], 1):  # Show max 5
        property_name = prop.get("name", "Facility")
        city = prop.get("city", "")
        greeting += f"{idx}. {property_name}"
        if city:
            greeting += f" ({city})"
        greeting += "\n"
    
    if len(properties) > 5:
        greeting += f"\n...and {len(properties) - 5} more facilities"
    
    return greeting
