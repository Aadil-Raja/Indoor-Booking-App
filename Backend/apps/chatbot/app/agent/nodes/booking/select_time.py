"""
Select time node for booking subgraph.

This module implements the select_time node that handles time slot selection
in the booking flow. It retrieves available time slots for the selected date,
gets pricing for each slot, presents them as list options, excludes blocked slots,
stores the selected time in flow_state, and handles invalid selections gracefully.

Requirements: 6.3, 10.1-10.6, 20.5, 22.1-22.6, 23.3
"""

from typing import Optional, Dict, Any, List
import logging
import re
from datetime import datetime, time

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def select_time(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle time slot selection in booking flow.
    
    This node manages the time slot selection step of the booking process. It:
    1. Checks if time is already selected in flow_state
    2. Retrieves available time slots for the selected date using availability tool
    3. Gets pricing information for each slot using pricing tool
    4. Presents slots with pricing as list options
    5. Excludes blocked slots from the options
    6. Parses user selection (time slot)
    7. Validates the selection
    8. Stores selected time (start_time, end_time) in flow_state
    9. Updates flow_state step to "select_time"
    10. Handles invalid selections with helpful error messages
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Select_Time node
    - 10.1: Integrate availability_service.check_blocked_slots() as a tool
    - 10.2: Integrate pricing_service.get_pricing_for_time_slot() as a tool
    - 10.3: Retrieve available time slots when user selects a date
    - 10.4: Include pricing information when displaying time slots
    - 10.5: Exclude blocked time slots from available options
    - 10.6: Suggest alternative dates when no slots are available
    - 20.5: Store selected time when user chooses a time slot
    - 22.1: Present time slots with pricing
    - 22.2: Present booking summary including time
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
                          and updated flow_state containing time and step
        
    Example:
        # First call - present options
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "2024-12-25",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "date": "2024-12-25",
                "step": "date_selected"
            },
            ...
        }
        
        result = await select_time(state, tools)
        # result["response_type"] = "list"
        # result["response_metadata"]["list_items"] = [...]
        # result["flow_state"]["step"] = "select_time"
        
        # Second call - process selection
        state = {
            "user_message": "14:00",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "date": "2024-12-25",
                "step": "select_time"
            },
            ...
        }
        
        result = await select_time(state, tools)
        # result["flow_state"]["start_time"] = "14:00:00"
        # result["flow_state"]["end_time"] = "15:00:00"
        # result["flow_state"]["price"] = 50.0
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    bot_memory = state.get("bot_memory", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing time selection for chat {chat_id} - "
        f"step={flow_state.get('step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if time already selected
    if flow_state.get("start_time") and flow_state.get("end_time"):
        logger.debug(
            f"Time already selected for chat {chat_id}: "
            f"start_time={flow_state.get('start_time')}, "
            f"end_time={flow_state.get('end_time')}"
        )
        # Time already selected, continue to next step
        return state
    
    # Check if date is selected
    date_str = flow_state.get("date")
    if not date_str:
        logger.warning(
            f"No date selected for chat {chat_id}, cannot select time"
        )
        
        response = (
            "Please select a date first before choosing a time slot."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Check if service is selected
    service_id = flow_state.get("service_id")
    if not service_id:
        logger.warning(
            f"No service selected for chat {chat_id}, cannot select time"
        )
        
        response = (
            "Please select a court first before choosing a time slot."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Check if we're processing a selection or presenting options
    current_step = flow_state.get("step")
    
    if current_step == "select_time":
        # User is responding with a time selection
        return await _process_time_selection(
            state=state,
            tools=tools,
            chat_id=chat_id,
            user_message=user_message,
            flow_state=flow_state,
            bot_memory=bot_memory
        )
    else:
        # First time in this node, present options
        return await _present_time_options(
            state=state,
            tools=tools,
            chat_id=chat_id,
            flow_state=flow_state,
            bot_memory=bot_memory,
            service_id=service_id,
            date_str=date_str
        )


async def _present_time_options(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any],
    service_id: str,
    date_str: str
) -> ConversationState:
    """
    Present time slot options to the user as a list.
    
    This function retrieves available time slots for the selected date,
    gets pricing for each slot, and presents them as list options.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        flow_state: Current flow state
        bot_memory: Bot memory
        service_id: Selected service (court) ID
        date_str: Selected date string (YYYY-MM-DD)
        
    Returns:
        Updated ConversationState with list options
    """
    # Parse date string
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(
            f"Invalid date format in flow_state for chat {chat_id}: {date_str}"
        )
        
        response = (
            "There was an error with the selected date. "
            "Please select a date again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Reset to date selection
        flow_state["step"] = "service_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Retrieve available time slots
    available_slots = await _get_available_time_slots(
        tools=tools,
        service_id=service_id,
        date_obj=date_obj,
        chat_id=chat_id
    )
    
    if not available_slots:
        logger.warning(
            f"No available slots found for service {service_id} "
            f"on {date_str} in chat {chat_id}"
        )
        
        service_name = flow_state.get("service_name", "this court")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        
        response = (
            f"I'm sorry, but there are no available time slots for {service_name} "
            f"on {formatted_date}. Would you like to try a different date?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step to allow date change
        flow_state["step"] = "date_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Format slots as list items with pricing
    list_items = _format_slots_as_list(available_slots)
    
    # Generate response message
    service_name = flow_state.get("service_name", "the court")
    formatted_date = date_obj.strftime("%A, %B %d, %Y")
    
    response = (
        f"Great! Here are the available time slots for {service_name} "
        f"on {formatted_date}:"
    )
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    # Update flow state
    flow_state["step"] = "select_time"
    state["flow_state"] = flow_state
    
    # Store slot details in bot_memory for later reference
    bot_memory = _store_slot_details_in_memory(
        bot_memory=bot_memory,
        slots=available_slots
    )
    state["bot_memory"] = bot_memory
    
    logger.info(
        f"Presented {len(list_items)} time slot options for chat {chat_id}"
    )
    
    return state


async def _process_time_selection(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any]
) -> ConversationState:
    """
    Process user's time slot selection.
    
    This function parses the user's selection (time slot),
    validates it, and stores the selected time in flow_state.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        user_message: User's selection message
        flow_state: Current flow state
        bot_memory: Bot memory containing slot details
        
    Returns:
        Updated ConversationState with selected time in flow_state
    """
    # Get available slots from bot_memory
    available_slots = bot_memory.get("context", {}).get("slot_details", [])
    
    if not available_slots:
        # Fallback: retrieve slots again
        service_id = flow_state.get("service_id")
        date_str = flow_state.get("date")
        
        if service_id and date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                available_slots = await _get_available_time_slots(
                    tools=tools,
                    service_id=service_id,
                    date_obj=date_obj,
                    chat_id=chat_id
                )
            except ValueError:
                logger.error(
                    f"Invalid date format in flow_state for chat {chat_id}: {date_str}"
                )
        
        if not available_slots:
            logger.error(
                f"No available slots found in bot_memory for chat {chat_id}"
            )
            
            response = (
                "I couldn't find the available time slots. "
                "Let's try selecting a date again."
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Reset to date selection
            flow_state["step"] = "service_selected"
            state["flow_state"] = flow_state
            
            return state
    
    # Parse user selection
    selected_slot = _parse_time_selection(
        user_message=user_message,
        available_slots=available_slots
    )
    
    if not selected_slot:
        # Invalid selection
        logger.warning(
            f"Invalid time selection for chat {chat_id}: {user_message}"
        )
        
        # Generate helpful error message with available options
        slot_times = [
            f"{s.get('start_time')} - {s.get('end_time')}"
            for s in available_slots[:5]  # Show first 5
        ]
        options_text = ", ".join(slot_times)
        
        response = (
            f"I couldn't find that time slot. "
            f"Please select from the available options: {options_text}"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as select_time to allow retry
        return state
    
    # Valid selection - store in flow_state
    start_time = selected_slot.get("start_time")
    end_time = selected_slot.get("end_time")
    price = selected_slot.get("price_per_hour")
    label = selected_slot.get("label", "")
    
    flow_state["start_time"] = start_time
    flow_state["end_time"] = end_time
    flow_state["price"] = price
    flow_state["price_label"] = label
    flow_state["step"] = "time_selected"
    
    state["flow_state"] = flow_state
    
    # Generate confirmation message
    service_name = flow_state.get("service_name", "the court")
    date_str = flow_state.get("date", "")
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        formatted_date = date_str
    
    # Format time for display (remove seconds if present)
    display_start = _format_time_for_display(start_time)
    display_end = _format_time_for_display(end_time)
    
    response = (
        f"Perfect! You've selected {display_start} - {display_end} "
        f"for {service_name} on {formatted_date}. "
        f"The price is ${price:.2f}/hour"
    )
    
    if label:
        response += f" ({label})"
    
    response += ". Let me prepare your booking summary."
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(
        f"Time selected for chat {chat_id}: "
        f"start_time={start_time}, end_time={end_time}, price=${price}"
    )
    
    return state


async def _get_available_time_slots(
    tools: Dict[str, Any],
    service_id: str,
    date_obj,
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve available time slots for a specific service and date.
    
    This function calls the get_available_slots tool to retrieve
    all available time slots with pricing information, excluding
    blocked slots and existing bookings.
    
    Args:
        tools: Tool registry
        service_id: Service (court) ID
        date_obj: Date object
        chat_id: Chat ID for logging
        
    Returns:
        List of slot dictionaries with start_time, end_time, price_per_hour, label
    """
    get_available_slots = tools.get("get_available_slots")
    if not get_available_slots:
        logger.error("get_available_slots tool not found in registry")
        return []
    
    try:
        # Convert service_id to int if it's a string
        service_id_int = int(service_id) if isinstance(service_id, str) else service_id
        
        logger.debug(
            f"Retrieving available slots for chat {chat_id}: "
            f"service_id={service_id_int}, date={date_obj}"
        )
        
        availability_data = await get_available_slots(
            court_id=service_id_int,
            date_val=date_obj
        )
        
        if availability_data and availability_data.get("available_slots"):
            slots = availability_data["available_slots"]
            logger.info(
                f"Retrieved {len(slots)} available slots for service {service_id_int} "
                f"on {date_obj} in chat {chat_id}"
            )
            return slots
        else:
            logger.warning(
                f"No available slots found for service {service_id_int} "
                f"on {date_obj} in chat {chat_id}"
            )
            return []
        
    except Exception as e:
        logger.error(
            f"Error retrieving available slots for service {service_id} "
            f"on {date_obj} in chat {chat_id}: {e}",
            exc_info=True
        )
        return []


def _format_slots_as_list(
    slots: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Format time slots as list items with pricing information.
    
    This function converts slot dictionaries into list item format
    with id, title, and description fields suitable for display to the user.
    
    Implements Requirement 23.3: Support list message type for multiple choice selections
    Implements Requirement 10.4: Include pricing information when displaying time slots
    
    Args:
        slots: List of slot dictionaries
        
    Returns:
        List of list item dictionaries with id, title, and description fields
        
    Example:
        list_items = _format_slots_as_list([
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            }
        ])
        # Returns: [{
        #     "id": "09:00:00",
        #     "title": "9:00 AM - 10:00 AM",
        #     "description": "$50.00/hour (Morning Rate)"
        # }]
    """
    list_items = []
    
    for slot in slots:
        start_time = slot.get("start_time")
        end_time = slot.get("end_time")
        price = slot.get("price_per_hour", 0.0)
        label = slot.get("label", "")
        
        # Format times for display
        display_start = _format_time_for_display(start_time)
        display_end = _format_time_for_display(end_time)
        
        # Create title
        title = f"{display_start} - {display_end}"
        
        # Create description with pricing
        description = f"${price:.2f}/hour"
        if label:
            description += f" ({label})"
        
        list_items.append({
            "id": start_time,  # Use start_time as ID
            "title": title,
            "description": description
        })
    
    return list_items


def _parse_time_selection(
    user_message: str,
    available_slots: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Parse user's time slot selection from message.
    
    This function attempts to match the user's message to a time slot by:
    1. Exact start_time match (with or without seconds)
    2. Time range match (e.g., "14:00 - 15:00")
    3. Partial time match (e.g., "14:00", "2pm", "2:00 PM")
    4. Slot index match (e.g., "1", "first", "second")
    
    Args:
        user_message: User's selection message
        available_slots: List of available slot dictionaries
        
    Returns:
        Selected slot dictionary or None if no match found
        
    Example:
        slot = _parse_time_selection(
            "14:00",
            [{"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 50.0}]
        )
        # Returns: {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 50.0}
    """
    message_lower = user_message.lower().strip()
    
    # Return None for empty messages
    if not message_lower:
        logger.debug("Empty message provided for time selection")
        return None
    
    # Try to match by slot index first (1, 2, 3, etc. or "first", "second", etc.)
    # This should be checked before time parsing to avoid "1" being interpreted as "1:00"
    index_keywords = {
        "first": 0, "1st": 0,
        "second": 1, "2nd": 1,
        "third": 2, "3rd": 2,
        "fourth": 3, "4th": 3,
        "fifth": 4, "5th": 4,
    }
    
    # Check for word-based index keywords
    for keyword, index in index_keywords.items():
        if keyword in message_lower.split():
            if 0 <= index < len(available_slots):
                logger.debug(f"Matched slot by index keyword: {index}")
                return available_slots[index]
    
    # Check for single digit index (only if it's the entire message or a standalone word)
    if message_lower.strip().isdigit():
        index = int(message_lower.strip()) - 1  # Convert to 0-based index
        if 0 <= index < len(available_slots):
            logger.debug(f"Matched slot by numeric index: {index}")
            return available_slots[index]
    
    # Try exact start_time match (with or without seconds)
    for slot in available_slots:
        start_time = slot.get("start_time", "")
        # Match with or without seconds
        if start_time.startswith(message_lower) or message_lower.startswith(start_time[:5]):
            logger.debug(f"Matched slot by exact start_time: {start_time}")
            return slot
    
    # Try to extract time from message (HH:MM format or just HH)
    time_pattern_with_minutes = r'\b(\d{1,2}):(\d{2})\b'
    time_match = re.search(time_pattern_with_minutes, user_message)
    
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        
        # Convert to 24-hour format if PM is mentioned
        if 'pm' in message_lower and hour < 12:
            hour += 12
        elif 'am' in message_lower and hour == 12:
            hour = 0
        
        # Format as HH:MM:SS
        time_str = f"{hour:02d}:{minute:02d}:00"
        
        # Try to match this time
        for slot in available_slots:
            if slot.get("start_time", "").startswith(time_str[:5]):
                logger.debug(f"Matched slot by parsed time: {time_str}")
                return slot
    
    # Try to extract time without colon (e.g., "2 pm", "14")
    time_pattern_hour_only = r'\b(\d{1,2})\s*(?:am|pm|AM|PM)?\b'
    time_match_hour = re.search(time_pattern_hour_only, user_message)
    
    if time_match_hour:
        hour = int(time_match_hour.group(1))
        minute = 0
        
        # Convert to 24-hour format if PM is mentioned
        if 'pm' in message_lower and hour < 12:
            hour += 12
        elif 'am' in message_lower and hour == 12:
            hour = 0
        
        # Format as HH:MM:SS
        time_str = f"{hour:02d}:{minute:02d}:00"
        
        # Try to match this time
        for slot in available_slots:
            if slot.get("start_time", "").startswith(time_str[:5]):
                logger.debug(f"Matched slot by parsed hour-only time: {time_str}")
                return slot
    
    # Try matching time range (e.g., "14:00 - 15:00")
    for slot in available_slots:
        start_time = slot.get("start_time", "")
        end_time = slot.get("end_time", "")
        
        # Format for comparison
        start_display = _format_time_for_display(start_time)
        end_display = _format_time_for_display(end_time)
        time_range = f"{start_display} - {end_display}".lower()
        
        if time_range in message_lower or message_lower in time_range:
            logger.debug(f"Matched slot by time range: {time_range}")
            return slot
    
    # No match found
    logger.debug(f"No time slot match found for: {user_message}")
    return None


def _format_time_for_display(time_str: str) -> str:
    """
    Format time string for user-friendly display.
    
    Converts 24-hour format (HH:MM:SS) to 12-hour format with AM/PM.
    
    Args:
        time_str: Time string in HH:MM:SS format
        
    Returns:
        Formatted time string (e.g., "2:00 PM")
        
    Example:
        display = _format_time_for_display("14:00:00")
        # Returns: "2:00 PM"
        
        display = _format_time_for_display("09:30:00")
        # Returns: "9:30 AM"
    """
    try:
        # Parse time string
        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
        
        # Format as 12-hour with AM/PM
        hour = time_obj.hour
        minute = time_obj.minute
        
        am_pm = "AM" if hour < 12 else "PM"
        
        # Convert to 12-hour format
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        
        # Format with or without minutes
        if minute == 0:
            return f"{hour}:00 {am_pm}"
        else:
            return f"{hour}:{minute:02d} {am_pm}"
        
    except ValueError:
        # If parsing fails, return original string
        logger.warning(f"Failed to parse time string: {time_str}")
        return time_str


def _store_slot_details_in_memory(
    bot_memory: Dict[str, Any],
    slots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Store slot details in bot_memory for later reference.
    
    This function stores the retrieved slot details in bot_memory
    so they can be accessed during time selection without additional
    API calls.
    
    Args:
        bot_memory: Current bot_memory dictionary
        slots: List of slot dictionaries to store
        
    Returns:
        Updated bot_memory dictionary
    """
    # Ensure context exists
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Store slot details
    bot_memory["context"]["slot_details"] = slots
    
    return bot_memory
