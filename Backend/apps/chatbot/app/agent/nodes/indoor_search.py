"""
DEPRECATED: Indoor search handler node - REPLACED by information_handler

This node has been REPLACED by the information_handler (app/agent/nodes/information.py)
which uses LangChain agents with automatic tool calling to handle all information-related
queries including search, availability, pricing, and media.

This file is kept for backward compatibility and reference only.
DO NOT USE THIS NODE IN NEW CODE - Use information_handler instead.

MIGRATION GUIDE:
- Old: from app.agent.nodes.indoor_search import indoor_search_handler
- New: from app.agent.nodes.information import information_handler

- Old: graph.add_node("indoor_search", indoor_search_handler)
- New: graph.add_node("information", information_handler)

- Old routing: "search": "indoor_search"
- New routing: "information": "information"

---

Legacy Documentation:

This module implements the indoor_search_handler node that processes facility
search requests. It extracts search parameters from user messages, calls property
and court search tools, formats results as list messages, and stores results in
bot_memory for later reference.

Requirements: 9.1-9.7, 21.2, 23.1-23.6
"""

from typing import Optional, Dict, Any, List
import logging
import re

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def indoor_search_handler(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle facility search requests with parameter extraction and result formatting.
    
    This node processes user requests to search for indoor sports facilities. It:
    1. Extracts search parameters (sport type, location) from the user message
    2. Calls property and court search tools to find matching facilities
    3. Formats results as a list message type for display
    4. Stores search results in bot_memory for later reference
    5. Handles cases where no results are found
    
    Implements Requirements:
    - 9.1: Integrate property_service.search_properties() as a tool
    - 9.2: Integrate court_service.search_courts_by_sport_type() as a tool
    - 9.4: Call property search tools when user requests facility search
    - 9.5: Filter courts by sport type when user specifies sport type
    - 9.6: Present search results in conversational format
    - 9.7: Use list or button message types when presenting multiple options
    - 21.2: Route facility/sports questions to Indoor_Search node
    - 23.1-23.6: Support text and list message types
    
    Args:
        state: ConversationState containing user message and context
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated bot_memory containing search results
        
    Example:
        # User searches for tennis courts
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "user-uuid",
            "owner_profile_id": "owner-uuid",
            "user_message": "I'm looking for tennis courts in downtown",
            "bot_memory": {},
            ...
        }
        
        result = await indoor_search_handler(state, tools)
        # result["response_type"] = "list"
        # result["response_metadata"]["list_items"] = [...]
        # result["bot_memory"]["context"]["last_search_results"] = [...]
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    owner_profile_id = state["owner_profile_id"]
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing indoor search for chat {chat_id} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Extract search parameters from user message
    search_params = _extract_search_params(user_message)
    
    # Check if user is asking for details about a specific property
    property_name = _extract_property_name(user_message)
    if property_name and ("detail" in user_message.lower() or "more" in user_message.lower()):
        logger.info(f"User requesting details for property: {property_name}")
        # Try to find the property by name and show details
        result = await _show_property_details(
            tools=tools,
            owner_profile_id=owner_profile_id,
            property_name=property_name,
            chat_id=chat_id
        )
        if result:
            state.update(result)
            return state
        # If property not found, fall through to regular search
    
    logger.debug(
        f"Extracted search parameters for chat {chat_id}: {search_params}"
    )
    
    # Search for properties and courts
    properties = await _search_facilities(
        tools=tools,
        owner_profile_id=owner_profile_id,
        search_params=search_params,
        chat_id=chat_id
    )
    
    # Handle no results case
    if not properties:
        logger.info(f"No facilities found for chat {chat_id}")
        response = _generate_no_results_response(search_params)
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        return state
    
    # Format results as list message
    list_items = _format_search_results(properties)
    
    # Generate response message
    response = _generate_results_response(search_params, len(properties))
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    # Store search results in bot_memory
    bot_memory = state.get("bot_memory", {})
    bot_memory = _update_bot_memory_with_results(
        bot_memory=bot_memory,
        properties=properties,
        search_params=search_params
    )
    state["bot_memory"] = bot_memory
    
    logger.info(
        f"Indoor search completed for chat {chat_id} - "
        f"found {len(properties)} facilities"
    )
    
    return state


def _extract_search_params(message: str) -> Dict[str, Any]:
    """
    Extract search parameters from user message.
    
    This function analyzes the user's message to identify:
    - Sport type (tennis, basketball, badminton, squash, volleyball)
    - Location keywords (downtown, westside, etc.)
    
    The extraction uses keyword matching and pattern recognition to handle
    natural language variations and typos.
    
    Implements Requirement 21.6: Handle typos and informal language
    
    Args:
        message: User's search message
        
    Returns:
        Dictionary containing extracted parameters (sport_type, location)
        
    Example:
        params = _extract_search_params("looking for tennis courts downtown")
        # Returns: {"sport_type": "tennis", "location": "downtown"}
    """
    params = {}
    message_lower = message.lower()
    
    # Sport type detection with variations and typos
    sport_keywords = {
        "tennis": [
            r'\btennis\b',
            r'\btennis\s+court',
        ],
        "basketball": [
            r'\bbasketball\b',
            r'\bbasket\s+ball\b',
            r'\bbasket\b',
            r'\bhoops\b',
        ],
        "badminton": [
            r'\bbadminton\b',
            r'\bbad\s+minton\b',
        ],
        "squash": [
            r'\bsquash\b',
        ],
        "volleyball": [
            r'\bvolleyball\b',
            r'\bvolley\s+ball\b',
            r'\bvolley\b',
        ],
    }
    
    # Check each sport type
    for sport, patterns in sport_keywords.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                params["sport_type"] = sport
                logger.debug(f"Detected sport type: {sport}")
                break
        if "sport_type" in params:
            break
    
    # Location detection (simple keyword matching)
    location_keywords = {
        "downtown": [r'\bdowntown\b', r'\bdown\s+town\b', r'\bcity\s+center\b'],
        "westside": [r'\bwestside\b', r'\bwest\s+side\b', r'\bwest\b'],
        "eastside": [r'\beastside\b', r'\beast\s+side\b', r'\beast\b'],
        "northside": [r'\bnorthside\b', r'\bnorth\s+side\b', r'\bnorth\b'],
        "southside": [r'\bsouthside\b', r'\bsouth\s+side\b', r'\bsouth\b'],
    }
    
    for location, patterns in location_keywords.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                params["location"] = location
                logger.debug(f"Detected location: {location}")
                break
        if "location" in params:
            break
    
    return params


async def _search_facilities(
    tools: Dict[str, Any],
    owner_profile_id: str,
    search_params: Dict[str, Any],
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Search for facilities using property and court search tools.
    
    This function calls the appropriate search tools based on the extracted
    parameters. It prioritizes property search and enriches results with
    court information when sport_type is specified.
    
    Implements Requirements:
    - 9.1: Integrate property_service.search_properties() as a tool
    - 9.2: Integrate court_service.search_courts_by_sport_type() as a tool
    - 9.4: Call property search tools when user requests facility search
    - 9.5: Filter courts by sport type when user specifies sport type
    
    Args:
        tools: Tool registry containing search functions
        owner_profile_id: Owner profile ID to filter properties
        search_params: Extracted search parameters
        chat_id: Chat ID for logging
        
    Returns:
        List of property dictionaries with court information
    """
    try:
        sport_type = search_params.get("sport_type")
        location = search_params.get("location")
        
        # Search for properties
        search_properties = tools.get("search_properties")
        if not search_properties:
            logger.error(f"search_properties tool not found in registry")
            return []
        
        logger.debug(
            f"Calling search_properties for chat {chat_id}: "
            f"owner_profile_id={owner_profile_id}, city={location}, sport_type={sport_type}"
        )
        
        properties = await search_properties(
            owner_profile_id=owner_profile_id,
            city=location,
            sport_type=sport_type,
            limit=10
        )
        
        if not properties:
            logger.info(
                f"No properties found for chat {chat_id} with "
                f"sport_type={sport_type}, city={location}"
            )
            return []
        
        logger.info(
            f"Found {len(properties)} properties for chat {chat_id}"
        )
        
        # If sport_type is specified, enrich with court details
        if sport_type:
            enriched = await _enrich_with_court_details(
                tools=tools,
                properties=properties,
                sport_type=sport_type,
                chat_id=chat_id
            )
            # Only use enriched results if we got some back
            if enriched:
                properties = enriched
        
        return properties
        
    except Exception as e:
        logger.error(
            f"Error searching facilities for chat {chat_id}: {e}",
            exc_info=True
        )
        return []


async def _enrich_with_court_details(
    tools: Dict[str, Any],
    properties: List[Dict[str, Any]],
    sport_type: str,
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Enrich property results with court details for the specified sport type.
    
    This function retrieves detailed court information for each property
    and filters courts by sport type to provide more relevant results.
    
    Args:
        tools: Tool registry
        properties: List of property dictionaries
        sport_type: Sport type to filter courts by
        chat_id: Chat ID for logging
        
    Returns:
        List of properties enriched with court details
    """
    get_property_courts = tools.get("get_property_courts")
    if not get_property_courts:
        logger.warning("get_property_courts tool not found, skipping enrichment")
        return properties
    
    enriched_properties = []
    
    for prop in properties:
        try:
            property_id = prop.get("id")
            if not property_id:
                enriched_properties.append(prop)
                continue
            
            # Get courts for this property
            courts = await get_property_courts(property_id=property_id)
            
            # Filter courts by sport type
            matching_courts = [
                court for court in courts
                if court.get("sport_type", "").lower() == sport_type.lower()
            ]
            
            # Add court information to property
            if matching_courts:
                prop["matching_courts_count"] = len(matching_courts)
                prop["matching_courts"] = matching_courts
            
            # Include property regardless of whether it has matching courts
            # (the search already filtered by sport_type)
            enriched_properties.append(prop)
                
        except Exception as e:
            logger.warning(
                f"Error enriching property {prop.get('id')} for chat {chat_id}: {e}"
            )
            # Include property even if enrichment fails
            enriched_properties.append(prop)
    
    return enriched_properties


def _format_search_results(properties: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format search results as list items for display.
    
    This function converts property dictionaries into the list message format
    with id, title, and description fields suitable for display to the user.
    
    Implements Requirements:
    - 9.6: Present search results in conversational format
    - 9.7: Use list or button message types when presenting multiple options
    - 23.3: Support list message type for multiple choice selections
    
    Args:
        properties: List of property dictionaries
        
    Returns:
        List of formatted list items with id, title, description
        
    Example:
        items = _format_search_results([
            {"id": 1, "name": "Sports Center", "city": "NYC", "matching_courts_count": 3}
        ])
        # Returns: [{"id": "1", "title": "Sports Center", "description": "NYC - 3 courts"}]
    """
    list_items = []
    
    for prop in properties[:5]:  # Limit to 5 results for better UX
        property_id = prop.get("id")
        name = prop.get("name", "Unknown Property")
        city = prop.get("city", "")
        address = prop.get("address", "")
        
        # Build description with available information
        description_parts = []
        
        if city:
            description_parts.append(city)
        elif address:
            description_parts.append(address)
        
        # Add court count if available
        matching_courts = prop.get("matching_courts_count")
        if matching_courts:
            court_text = "court" if matching_courts == 1 else "courts"
            description_parts.append(f"{matching_courts} {court_text} available")
        else:
            # Fallback to total courts if available
            total_courts = prop.get("courts_count") or len(prop.get("courts", []))
            if total_courts:
                court_text = "court" if total_courts == 1 else "courts"
                description_parts.append(f"{total_courts} {court_text}")
        
        description = " - ".join(description_parts) if description_parts else "Available"
        
        list_items.append({
            "id": str(property_id),
            "title": name,
            "description": description
        })
    
    return list_items


def _generate_no_results_response(search_params: Dict[str, Any]) -> str:
    """
    Generate a helpful response when no facilities are found.
    
    This function creates a contextual message that acknowledges the search
    criteria and suggests alternative actions.
    
    Args:
        search_params: The search parameters that yielded no results
        
    Returns:
        Helpful no-results message
    """
    sport_type = search_params.get("sport_type")
    location = search_params.get("location")
    
    # Build contextual message
    criteria_parts = []
    if sport_type:
        criteria_parts.append(f"{sport_type} facilities")
    else:
        criteria_parts.append("facilities")
    
    if location:
        criteria_parts.append(f"in {location}")
    
    criteria = " ".join(criteria_parts)
    
    response = (
        f"I couldn't find any {criteria} matching your search. "
        f"Would you like to try a different search or browse all available facilities?"
    )
    
    return response


def _generate_results_response(
    search_params: Dict[str, Any],
    result_count: int
) -> str:
    """
    Generate a contextual response message for search results.
    
    This function creates a friendly message that introduces the search
    results and provides context about what was found.
    
    Args:
        search_params: The search parameters used
        result_count: Number of results found
        
    Returns:
        Contextual results message
    """
    sport_type = search_params.get("sport_type")
    location = search_params.get("location")
    
    # Build contextual message
    criteria_parts = []
    if sport_type:
        criteria_parts.append(f"{sport_type}")
    
    if location:
        criteria_parts.append(f"in {location}")
    
    if criteria_parts:
        criteria = " ".join(criteria_parts)
        response = f"Here are the available {criteria} facilities:"
    else:
        response = "Here are the available facilities:"
    
    # Add count if showing subset
    if result_count > 5:
        response += f" (showing top 5 of {result_count})"
    
    return response


def _update_bot_memory_with_results(
    bot_memory: Dict[str, Any],
    properties: List[Dict[str, Any]],
    search_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update bot_memory with search results and parameters.
    
    This function stores search results in bot_memory for later reference
    in the conversation flow (e.g., for booking).
    
    Args:
        bot_memory: Current bot_memory dictionary
        properties: List of property results
        search_params: Search parameters used
        
    Returns:
        Updated bot_memory dictionary
    """
    # Ensure context exists
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Store search results (property IDs)
    property_ids = [str(prop.get("id")) for prop in properties if prop.get("id")]
    bot_memory["context"]["last_search_results"] = property_ids
    
    # Store search parameters for context
    bot_memory["context"]["last_search_params"] = search_params
    
    # Update user preferences if sport type was specified
    if search_params.get("sport_type"):
        if "user_preferences" not in bot_memory:
            bot_memory["user_preferences"] = {}
        bot_memory["user_preferences"]["preferred_sport"] = search_params["sport_type"]
    
    return bot_memory



def _extract_property_name(message: str) -> Optional[str]:
    """
    Extract property name from user message.
    
    This function looks for property names mentioned in the message,
    particularly after keywords like "details of", "about", "for".
    
    Args:
        message: User's message
        
    Returns:
        Property name if found, None otherwise
    """
    message_lower = message.lower()
    
    # Patterns to extract property name
    patterns = [
        r'details?\s+(?:of|about|for)\s+([a-zA-Z0-9\s]+?)(?:\s|$)',
        r'(?:show|tell)\s+me\s+(?:about|more\s+about)\s+([a-zA-Z0-9\s]+?)(?:\s|$)',
        r'information\s+(?:on|about)\s+([a-zA-Z0-9\s]+?)(?:\s|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message_lower)
        if match:
            property_name = match.group(1).strip()
            logger.debug(f"Extracted property name: {property_name}")
            return property_name
    
    return None


async def _show_property_details(
    tools: Dict[str, Any],
    owner_profile_id: str,
    property_name: str,
    chat_id: str
) -> Optional[Dict[str, Any]]:
    """
    Show detailed information about a specific property.
    
    This function searches for the property by name, then retrieves
    and formats detailed information including courts, amenities, etc.
    
    Args:
        tools: Tool registry
        owner_profile_id: Owner profile ID
        property_name: Name of the property to show details for
        chat_id: Chat ID for logging
        
    Returns:
        State update dict with response, or None if property not found
    """
    try:
        # First, get all properties to find the one matching the name
        get_owner_properties = tools.get("get_owner_properties")
        if not get_owner_properties:
            logger.error("get_owner_properties tool not found")
            return None
        
        properties = await get_owner_properties(owner_profile_id=int(owner_profile_id))
        
        # Find property by name (case-insensitive partial match)
        matching_property = None
        property_name_lower = property_name.lower()
        
        for prop in properties:
            if property_name_lower in prop.get("name", "").lower():
                matching_property = prop
                break
        
        if not matching_property:
            logger.info(f"No property found matching name: {property_name}")
            return None
        
        property_id = matching_property.get("id")
        
        # Get detailed information about the property
        get_property_details = tools.get("get_property_details")
        if not get_property_details:
            logger.error("get_property_details tool not found")
            return None
        
        details = await get_property_details(
            property_id=property_id,
            owner_profile_id=int(owner_profile_id)
        )
        
        if not details:
            logger.warning(f"Failed to get details for property_id={property_id}")
            return None
        
        # Format the detailed response
        response = _format_property_details(details)
        
        logger.info(f"Showing details for property: {details.get('name')}")
        
        return {
            "response_content": response,
            "response_type": "text",
            "response_metadata": {
                "property_id": property_id,
                "property_name": details.get("name")
            }
        }
        
    except Exception as e:
        logger.error(f"Error showing property details: {e}", exc_info=True)
        return None


def _format_property_details(details: Dict[str, Any]) -> str:
    """
    Format property details into a readable response.
    
    Args:
        details: Property details dictionary
        
    Returns:
        Formatted response string
    """
    name = details.get("name", "Unknown")
    description = details.get("description", "")
    address = details.get("address", "")
    city = details.get("city", "")
    state = details.get("state", "")
    phone = details.get("phone", "")
    email = details.get("email", "")
    amenities = details.get("amenities", [])
    courts = details.get("courts", [])
    
    # Build response
    lines = [f"📍 {name}"]
    
    if description:
        lines.append(f"\n{description}")
    
    # Location
    location_parts = []
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if state:
        location_parts.append(state)
    
    if location_parts:
        lines.append(f"\n📌 Location: {', '.join(location_parts)}")
    
    # Contact
    if phone:
        lines.append(f"📞 Phone: {phone}")
    if email:
        lines.append(f"📧 Email: {email}")
    
    # Courts
    if courts:
        lines.append(f"\n🎾 Available Courts ({len(courts)}):")
        for court in courts:
            court_name = court.get("name", "Unnamed")
            sport_type = court.get("sport_type", "").title()
            status = "✅ Active" if court.get("is_active") else "❌ Inactive"
            lines.append(f"  • {court_name} - {sport_type} ({status})")
    
    # Amenities
    if amenities:
        lines.append(f"\n✨ Amenities:")
        for amenity in amenities:
            lines.append(f"  • {amenity}")
    
    return "\n".join(lines)
