"""
Select service node for booking subgraph.

This module implements the select_service node that handles court (service) selection
in the booking flow. It retrieves courts for the selected property, presents them as
list options with sport type information, parses user selection (court ID or court name),
stores the selected service_id in flow_state, and handles invalid selections gracefully.

Requirements: 6.3, 20.3, 22.1-22.6, 23.3
"""

from typing import Optional, Dict, Any, List
import logging
import re

from ...state.conversation_state import ConversationState
from ...tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def select_service(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle service (court) selection in booking flow.
    
    This node manages the service selection step of the booking process. It:
    1. Checks if service is already selected in flow_state
    2. Retrieves courts for the selected property using court tool
    3. Presents courts as list options with sport type information
    4. Parses user selection (court ID or court name)
    5. Validates the selection
    6. Stores selected service_id (court_id) in flow_state
    7. Updates flow_state step to "select_service"
    8. Handles invalid selections with helpful error messages
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Select_Service node
    - 20.3: Store selected service_id when user chooses a court
    - 22.1: Present courts from property
    - 22.2: Present booking summary including court type
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    - 23.3: Support list message type for multiple choice selections
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated flow_state containing service_id and step
        
    Example:
        # First call - present options
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "Downtown Sports Center",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "property_name": "Downtown Sports Center"
            },
            ...
        }
        
        result = await select_service(state, tools)
        # result["response_type"] = "list"
        # result["response_metadata"]["list_items"] = [...]
        # result["flow_state"]["step"] = "select_service"
        
        # Second call - process selection
        state = {
            "user_message": "Tennis Court A",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "property_name": "Downtown Sports Center",
                "step": "select_service"
            },
            ...
        }
        
        result = await select_service(state, tools)
        # result["flow_state"]["service_id"] = "10"
        # result["flow_state"]["service_name"] = "Tennis Court A"
        # result["flow_state"]["sport_type"] = "tennis"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    bot_memory = state.get("bot_memory", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing service selection for chat {chat_id} - "
        f"step={flow_state.get('step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if service already selected
    if flow_state.get("service_id"):
        logger.debug(
            f"Service already selected for chat {chat_id}: "
            f"service_id={flow_state.get('service_id')}"
        )
        # Service already selected, continue to next step
        return state
    
    # Check if property is selected
    property_id = flow_state.get("property_id")
    if not property_id:
        logger.warning(
            f"No property selected for chat {chat_id}, cannot select service"
        )
        
        response = (
            "Please select a facility first before choosing a court."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Check if we're processing a selection or presenting options
    current_step = flow_state.get("step")
    
    if current_step == "select_service":
        # User is responding with a selection
        return await _process_service_selection(
            state=state,
            tools=tools,
            chat_id=chat_id,
            user_message=user_message,
            flow_state=flow_state,
            bot_memory=bot_memory
        )
    else:
        # First time in this node, present options
        return await _present_service_options(
            state=state,
            tools=tools,
            chat_id=chat_id,
            flow_state=flow_state,
            bot_memory=bot_memory,
            property_id=property_id
        )


async def _present_service_options(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any],
    property_id: str
) -> ConversationState:
    """
    Present service (court) options to the user as a list.
    
    This function retrieves courts for the selected property and
    presents them as list options with sport type information.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        flow_state: Current flow state
        bot_memory: Bot memory
        property_id: Selected property ID
        
    Returns:
        Updated ConversationState with list options
    """
    # Retrieve courts for the property
    courts = await _get_property_courts(
        tools=tools,
        property_id=property_id,
        chat_id=chat_id
    )
    
    if not courts:
        logger.warning(
            f"No courts found for property {property_id} in chat {chat_id}"
        )
        
        property_name = flow_state.get("property_name", "this facility")
        response = (
            f"I couldn't find any courts available at {property_name}. "
            f"Would you like to select a different facility?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Format courts as list items
    list_items = _format_courts_as_list(courts)
    
    # Generate response message
    property_name = flow_state.get("property_name", "this facility")
    response = f"Great! Here are the available courts at {property_name}:"
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    # Update flow state
    flow_state["step"] = "select_service"
    state["flow_state"] = flow_state
    
    # Store court details in bot_memory for later reference
    bot_memory = _store_court_details_in_memory(
        bot_memory=bot_memory,
        courts=courts
    )
    state["bot_memory"] = bot_memory
    
    logger.info(
        f"Presented {len(list_items)} court options for chat {chat_id}"
    )
    
    return state


async def _process_service_selection(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any]
) -> ConversationState:
    """
    Process user's service (court) selection.
    
    This function parses the user's selection (court ID or court name),
    validates it, and stores the selected service_id in flow_state.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        user_message: User's selection message
        flow_state: Current flow state
        bot_memory: Bot memory containing court details
        
    Returns:
        Updated ConversationState with selected service_id in flow_state
    """
    # Get available courts from bot_memory
    available_courts = bot_memory.get("context", {}).get("court_details", [])
    
    if not available_courts:
        # Fallback: retrieve courts for the property
        property_id = flow_state.get("property_id")
        if property_id:
            available_courts = await _get_property_courts(
                tools=tools,
                property_id=property_id,
                chat_id=chat_id
            )
        else:
            logger.error(
                f"No property_id found in flow_state for chat {chat_id}"
            )
            
            response = (
                "I couldn't find the property information. "
                "Let's start over. Which facility would you like to book?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Reset flow state
            flow_state["step"] = "select_property"
            state["flow_state"] = flow_state
            
            return state
    
    # Parse user selection
    selected_court = _parse_court_selection(
        user_message=user_message,
        available_courts=available_courts
    )
    
    if not selected_court:
        # Invalid selection
        logger.warning(
            f"Invalid court selection for chat {chat_id}: {user_message}"
        )
        
        # Generate helpful error message with available options
        court_names = [
            f"{c.get('name', 'Unknown')} ({c.get('sport_type', 'Unknown sport')})"
            for c in available_courts
        ]
        options_text = ", ".join(court_names)
        
        response = (
            f"I couldn't find that court. "
            f"Please select from the available options: {options_text}"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as select_service to allow retry
        return state
    
    # Valid selection - store in flow_state
    service_id = str(selected_court.get("id"))
    service_name = selected_court.get("name", "Unknown Court")
    sport_type = selected_court.get("sport_type", "Unknown")
    
    flow_state["service_id"] = service_id
    flow_state["service_name"] = service_name
    flow_state["sport_type"] = sport_type
    flow_state["step"] = "service_selected"
    
    state["flow_state"] = flow_state
    
    # Generate confirmation message
    response = (
        f"Perfect! You've selected {service_name} ({sport_type}). "
        f"Now let's choose a date for your booking."
    )
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(
        f"Service selected for chat {chat_id}: "
        f"service_id={service_id}, service_name={service_name}, "
        f"sport_type={sport_type}"
    )
    
    return state


async def _get_property_courts(
    tools: Dict[str, Any],
    property_id: str,
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve courts for a specific property.
    
    This function calls the get_property_courts tool to retrieve
    all courts associated with the property.
    
    Args:
        tools: Tool registry
        property_id: Property ID to retrieve courts for
        chat_id: Chat ID for logging
        
    Returns:
        List of court dictionaries
    """
    get_property_courts = tools.get("get_property_courts")
    if not get_property_courts:
        logger.error("get_property_courts tool not found in registry")
        return []
    
    try:
        # Convert property_id to int if it's a string
        property_id_int = int(property_id) if isinstance(property_id, str) else property_id
        
        logger.debug(
            f"Retrieving courts for property in chat {chat_id}: "
            f"property_id={property_id_int}"
        )
        
        courts = await get_property_courts(
            property_id=property_id_int,
            owner_id=None  # Public access
        )
        
        if courts:
            logger.info(
                f"Retrieved {len(courts)} courts for property {property_id_int} "
                f"in chat {chat_id}"
            )
        else:
            logger.warning(
                f"No courts found for property {property_id_int} in chat {chat_id}"
            )
        
        return courts
        
    except Exception as e:
        logger.error(
            f"Error retrieving courts for property {property_id} in chat {chat_id}: {e}",
            exc_info=True
        )
        return []


def _format_courts_as_list(
    courts: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Format courts as list items with sport type information.
    
    This function converts court dictionaries into list item format
    with id, title, and description fields suitable for display to the user.
    
    Implements Requirement 23.3: Support list message type for multiple choice selections
    
    Args:
        courts: List of court dictionaries
        
    Returns:
        List of list item dictionaries with id, title, and description fields
        
    Example:
        list_items = _format_courts_as_list([
            {"id": 10, "name": "Court A", "sport_type": "tennis"}
        ])
        # Returns: [{"id": "10", "title": "Court A", "description": "Sport: tennis"}]
    """
    list_items = []
    
    for court in courts:
        court_id = court.get("id")
        name = court.get("name", "Unknown Court")
        sport_type = court.get("sport_type", "Unknown")
        
        list_items.append({
            "id": str(court_id),
            "title": name,
            "description": f"Sport: {sport_type}"
        })
    
    return list_items


def _parse_court_selection(
    user_message: str,
    available_courts: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Parse user's court selection from message.
    
    This function attempts to match the user's message to a court by:
    1. Exact court ID match
    2. Exact court name match (case-insensitive)
    3. Partial court name match (case-insensitive)
    4. Sport type match (if only one court of that sport type)
    
    Args:
        user_message: User's selection message
        available_courts: List of available court dictionaries
        
    Returns:
        Selected court dictionary or None if no match found
        
    Example:
        court = _parse_court_selection(
            "Tennis Court A",
            [{"id": 10, "name": "Tennis Court A", "sport_type": "tennis"}]
        )
        # Returns: {"id": 10, "name": "Tennis Court A", "sport_type": "tennis"}
    """
    message_lower = user_message.lower().strip()
    
    # Return None for empty messages
    if not message_lower:
        logger.debug("Empty message provided for court selection")
        return None
    
    # Try to match by court ID
    # Check if message is a number or contains a number
    id_match = re.search(r'\b(\d+)\b', message_lower)
    if id_match:
        court_id = id_match.group(1)
        for court in available_courts:
            if str(court.get("id")) == court_id:
                logger.debug(f"Matched court by ID: {court_id}")
                return court
    
    # Try exact name match (case-insensitive)
    for court in available_courts:
        court_name = court.get("name", "").lower()
        if court_name == message_lower:
            logger.debug(f"Matched court by exact name: {court_name}")
            return court
    
    # Try partial name match (case-insensitive)
    for court in available_courts:
        court_name = court.get("name", "").lower()
        # Check if user message is contained in court name or vice versa
        if message_lower in court_name or court_name in message_lower:
            logger.debug(f"Matched court by partial name: {court_name}")
            return court
    
    # Try matching by sport type (if only one court of that type)
    sport_keywords = {
        "tennis": ["tennis"],
        "basketball": ["basketball", "basket"],
        "badminton": ["badminton"],
        "squash": ["squash"],
        "volleyball": ["volleyball", "volley"]
    }
    
    for sport, keywords in sport_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            matching_courts = [
                c for c in available_courts
                if c.get("sport_type", "").lower() == sport
            ]
            if len(matching_courts) == 1:
                logger.debug(f"Matched court by sport type: {sport}")
                return matching_courts[0]
    
    # Try matching individual words (require at least 2 word matches or high overlap ratio)
    message_words = set(message_lower.split())
    best_match = None
    best_match_score = 0
    
    for court in available_courts:
        court_name = court.get("name", "").lower()
        court_words = set(court_name.split())
        
        # Calculate word overlap
        common_words = message_words.intersection(court_words)
        if common_words:
            score = len(common_words)
            # Require at least 2 matching words or high overlap ratio
            overlap_ratio = score / len(court_words)
            if score >= 2 or overlap_ratio >= 0.6:
                if score > best_match_score:
                    best_match = court
                    best_match_score = score
    
    if best_match and best_match_score >= 2:
        logger.debug(
            f"Matched court by word overlap: {best_match.get('name')} "
            f"(score={best_match_score})"
        )
        return best_match
    
    # No match found
    logger.debug(f"No court match found for: {user_message}")
    return None


def _store_court_details_in_memory(
    bot_memory: Dict[str, Any],
    courts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Store court details in bot_memory for later reference.
    
    This function stores the retrieved court details in bot_memory
    so they can be accessed during court selection without additional
    API calls.
    
    Args:
        bot_memory: Current bot_memory dictionary
        courts: List of court dictionaries to store
        
    Returns:
        Updated bot_memory dictionary
    """
    # Ensure context exists
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Store court details
    bot_memory["context"]["court_details"] = courts
    
    return bot_memory
