"""
Select time node for booking subgraph.

This module implements the select_time node that handles time slot selection
in the booking flow using LangChain agent. It retrieves available time slots for the selected date,
gets pricing for each slot, uses an LLM agent to parse user selection, excludes blocked slots,
stores the selected time in flow_state, and handles invalid selections gracefully.

Requirements: 7.4, 8.2, 8.5
"""

from typing import Optional, Dict, Any, List
import logging
import re
from datetime import datetime, time, timedelta

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.booking_prompts import create_select_time_prompt
from app.services.llm.base import LLMProvider
from app.agent.nodes.booking.flow_validation import (
    should_skip_to_next_step,
    validate_required_fields_for_step,
    get_booking_progress_summary
)

logger = logging.getLogger(__name__)


async def select_time(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle time slot selection in booking flow.
    
    This node manages the time slot selection step of the booking process. It:
    1. Checks if time_slot exists in flow_state (skip if exists) - Req 7.4
    2. Fetches available slots using get_availability_tool (court_id, date)
    3. Uses LLM to parse time from user message or present available slots
    4. If slot is booked, shows available slots for that day
    5. If full day is booked, shows nearest available date
    6. Validates time_slot format (HH:MM-HH:MM)
    7. If time parsed: stores in flow_state and updates booking_step to "time_selected" - Req 8.2
    8. If time not parsed: presents available slots
    9. Returns next_node decision
    
    Implements Requirements:
    - 7.4: Skip time selection step when Flow_State contains time_slot
    - 8.2: Update booking_step field in Flow_State when step is completed
    - 8.5: Validate each step's data before proceeding to the next step
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        llm_provider: LLMProvider for creating LangChain LLM
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          updated flow_state containing time_slot and booking_step, and next_node decision
        
    Example:
        # Case 1: Time already selected (skip)
        state = {
            "chat_id": "123",
            "flow_state": {"time_slot": "14:00-15:00"},
            ...
        }
        result = await select_time(state, llm_provider)
        # result["next_node"] = "confirm_booking"
        
        # Case 2: First call - present options
        state = {
            "chat_id": "123",
            "flow_state": {
                "court_id": 10,
                "date": "2024-12-25",
                "booking_step": "date_selected"
            },
            ...
        }
        
        result = await select_time(state, llm_provider)
        # result["response_type"] = "list"
        # result["response_metadata"]["list_items"] = [...]
        # result["flow_state"]["booking_step"] = "awaiting_time_selection"
        # result["next_node"] = "wait_for_selection"
        
        # Case 3: Process selection
        state = {
            "user_message": "14:00",
            "flow_state": {
                "court_id": 10,
                "date": "2024-12-25",
                "booking_step": "awaiting_time_selection"
            },
            ...
        }
        
        result = await select_time(state, llm_provider)
        # result["flow_state"]["time_slot"] = "14:00-15:00"
        # result["flow_state"]["booking_step"] = "time_selected"
        # result["next_node"] = "confirm_booking"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    bot_memory = state.get("bot_memory", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    # Log booking progress for debugging
    progress = get_booking_progress_summary(flow_state)
    logger.info(
        f"Processing time selection for chat {chat_id} - "
        f"progress={progress['completion_percentage']}%, "
        f"next_step={progress['next_step']}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Step 1: Check if time_slot already selected (Requirement 7.4, 7.5, 7.6)
    should_skip, next_node = should_skip_to_next_step("select_time", flow_state)
    if should_skip:
        logger.debug(
            f"Time slot already selected for chat {chat_id}: "
            f"time_slot={flow_state.get('time_slot')}, "
            f"skipping to {next_node}"
        )
        # Time already selected, skip to next step
        state["next_node"] = next_node
        return state
    
    # Step 2: Validate prerequisites - date must be selected first
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "select_time",
        flow_state
    )
    if not is_valid:
        logger.warning(
            f"Cannot select time without {missing_field} for chat {chat_id}, "
            f"redirecting to {redirect_node}"
        )
        
        if missing_field == "property_id":
            message = "Please select a property first before choosing a time slot."
        elif missing_field == "court_id":
            message = "Please select a court first before choosing a time slot."
        elif missing_field == "date":
            message = "Please select a date first before choosing a time slot."
        else:
            message = f"Please complete the previous steps before selecting a time slot."
        
        state["response_content"] = message
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = redirect_node
        
        return state
    
    # Step 3: Get required data from flow_state
    date_str = flow_state.get("date")
    court_id = flow_state.get("court_id")
    
    # Step 4: Check if we're processing a selection or presenting options
    current_step = flow_state.get("booking_step")
    
    if current_step == "awaiting_time_selection":
        # User is responding with a time selection
        return await _process_time_selection(
            state=state,
            llm_provider=llm_provider,
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
            court_id=court_id,
            date_str=date_str
        )


async def _present_time_options(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any],
    court_id: int,
    date_str: str
) -> ConversationState:
    """
    Present time slot options to the user as a list.
    
    This function retrieves available time slots for the selected date,
    gets pricing for each slot, and presents them as list options.
    If no slots are available, suggests alternative dates.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        flow_state: Current flow state
        bot_memory: Bot memory
        court_id: Selected court ID
        date_str: Selected date string (YYYY-MM-DD)
        
    Returns:
        Updated ConversationState with list options and next_node decision
    """
    # Parse date string (Requirement 8.5)
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
        state["next_node"] = "select_date"
        
        # Reset to date selection
        flow_state["booking_step"] = "court_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Retrieve available time slots
    available_slots = await _get_available_time_slots(
        tools=tools,
        court_id=court_id,
        date_obj=date_obj,
        chat_id=chat_id
    )
    
    # Handle no available slots - suggest alternative dates
    if not available_slots:
        logger.warning(
            f"No available slots found for court {court_id} "
            f"on {date_str} in chat {chat_id}"
        )
        
        court_name = flow_state.get("court_name", "this court")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        
        # Try to find nearest available date
        nearest_date = await _find_nearest_available_date(
            tools=tools,
            court_id=court_id,
            start_date=date_obj,
            chat_id=chat_id
        )
        
        if nearest_date:
            nearest_formatted = nearest_date.strftime("%A, %B %d, %Y")
            response = (
                f"I'm sorry, but there are no available time slots for {court_name} "
                f"on {formatted_date}. The nearest available date is {nearest_formatted}. "
                f"Would you like to book for that date instead?"
            )
        else:
            response = (
                f"I'm sorry, but there are no available time slots for {court_name} "
                f"on {formatted_date}. Would you like to try a different date?"
            )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "wait_for_selection"
        
        # Keep step to allow date change
        flow_state["booking_step"] = "date_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Format slots as list items with pricing
    list_items = _format_slots_as_list(available_slots)
    
    # Generate response message
    court_name = flow_state.get("court_name", "the court")
    formatted_date = date_obj.strftime("%A, %B %d, %Y")
    
    response = (
        f"Great! Here are the available time slots for {court_name} "
        f"on {formatted_date}:"
    )
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    # Update flow state (Requirement 8.2)
    flow_state["booking_step"] = "awaiting_time_selection"
    state["flow_state"] = flow_state
    
    # Store slot details in bot_memory for later reference
    bot_memory = _store_slot_details_in_memory(
        bot_memory=bot_memory,
        slots=available_slots
    )
    state["bot_memory"] = bot_memory
    
    # Wait for user selection
    state["next_node"] = "wait_for_selection"
    
    logger.info(
        f"Presented {len(list_items)} time slot options for chat {chat_id}"
    )
    
    return state


async def _process_time_selection(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Dict[str, Any],
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any]
) -> ConversationState:
    """
    Process user's time slot selection using LangChain agent.
    
    This function uses a LangChain agent to intelligently parse the user's
    selection, validates it, and stores the selected time_slot in HH:MM-HH:MM format
    in flow_state.
    
    Implements Requirements:
    - 8.2: Update booking_step to "time_selected" when complete
    - 8.5: Validate time_slot format (HH:MM-HH:MM)
    
    Args:
        state: ConversationState
        llm_provider: LLMProvider for creating LangChain LLM
        tools: Tool registry
        chat_id: Chat ID for logging
        user_message: User's selection message
        flow_state: Current flow state
        bot_memory: Bot memory containing slot details
        
    Returns:
        Updated ConversationState with selected time_slot in flow_state and next_node decision
    """
    # Get available slots from bot_memory
    available_slots = bot_memory.get("context", {}).get("slot_details", [])
    
    if not available_slots:
        # Fallback: retrieve slots again
        court_id = flow_state.get("court_id")
        date_str = flow_state.get("date")
        
        if court_id and date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                available_slots = await _get_available_time_slots(
                    tools=tools,
                    court_id=court_id,
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
            state["next_node"] = "select_date"
            
            # Reset to date selection
            flow_state["booking_step"] = "court_selected"
            state["flow_state"] = flow_state
            
            return state
    
    # Try to parse selection using LLM
    selected_slot = await _parse_time_with_llm(
        llm_provider=llm_provider,
        user_message=user_message,
        available_slots=available_slots,
        flow_state=flow_state,
        chat_id=chat_id
    )
    
    # Fallback to manual parsing if LLM fails
    if not selected_slot:
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
            f"{_format_time_for_display(s.get('start_time'))} - {_format_time_for_display(s.get('end_time'))}"
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
        state["next_node"] = "wait_for_selection"
        
        return state
    
    # Valid selection - store in flow_state
    start_time = selected_slot.get("start_time")
    end_time = selected_slot.get("end_time")
    price = selected_slot.get("price_per_hour")
    label = selected_slot.get("label", "")
    
    # Format time_slot as HH:MM-HH:MM (Requirement 8.5)
    time_slot = _format_time_slot(start_time, end_time)
    
    flow_state["time_slot"] = time_slot
    flow_state["price"] = price
    flow_state["price_label"] = label
    flow_state["booking_step"] = "time_selected"  # Requirement 8.2
    
    state["flow_state"] = flow_state
    
    # Generate confirmation message
    court_name = flow_state.get("court_name", "the court")
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
        f"for {court_name} on {formatted_date}. "
        f"The price is ${price:.2f}/hour"
    )
    
    if label:
        response += f" ({label})"
    
    response += ". Let me prepare your booking summary."
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    state["next_node"] = "confirm_booking"
    
    logger.info(
        f"Time selected for chat {chat_id}: "
        f"time_slot={time_slot}, price=${price}"
    )
    
    return state


async def _get_available_time_slots(
    tools: Dict[str, Any],
    court_id: int,
    date_obj,
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve available time slots for a specific court and date.
    
    This function calls the get_available_slots tool to retrieve
    all available time slots with pricing information, excluding
    blocked slots and existing bookings.
    
    Args:
        tools: Tool registry
        court_id: Court ID
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
        # Convert court_id to int if it's a string
        court_id_int = int(court_id) if isinstance(court_id, str) else court_id
        
        logger.debug(
            f"Retrieving available slots for chat {chat_id}: "
            f"court_id={court_id_int}, date={date_obj}"
        )
        
        availability_data = await get_available_slots(
            court_id=court_id_int,
            date_val=date_obj
        )
        
        if availability_data and availability_data.get("available_slots"):
            slots = availability_data["available_slots"]
            logger.info(
                f"Retrieved {len(slots)} available slots for court {court_id_int} "
                f"on {date_obj} in chat {chat_id}"
            )
            return slots
        else:
            logger.warning(
                f"No available slots found for court {court_id_int} "
                f"on {date_obj} in chat {chat_id}"
            )
            return []
        
    except Exception as e:
        logger.error(
            f"Error retrieving available slots for court {court_id} "
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


def _format_time_slot(start_time: str, end_time: str) -> str:
    """
    Format time slot as HH:MM-HH:MM.
    
    Converts time strings from HH:MM:SS format to HH:MM-HH:MM format
    for storage in flow_state.
    
    Args:
        start_time: Start time in HH:MM:SS format
        end_time: End time in HH:MM:SS format
        
    Returns:
        Formatted time slot string (e.g., "14:00-15:00")
        
    Example:
        time_slot = _format_time_slot("14:00:00", "15:00:00")
        # Returns: "14:00-15:00"
    """
    try:
        # Extract HH:MM from HH:MM:SS
        start_hhmm = start_time[:5] if len(start_time) >= 5 else start_time
        end_hhmm = end_time[:5] if len(end_time) >= 5 else end_time
        
        return f"{start_hhmm}-{end_hhmm}"
    except Exception as e:
        logger.warning(f"Failed to format time slot: {e}")
        return f"{start_time}-{end_time}"


async def _find_nearest_available_date(
    tools: Dict[str, Any],
    court_id: int,
    start_date,
    chat_id: str,
    max_days: int = 14
) -> Optional[datetime.date]:
    """
    Find the nearest date with available time slots.
    
    This function searches for the next available date starting from
    start_date + 1 day, up to max_days in the future.
    
    Args:
        tools: Tool registry
        court_id: Court ID
        start_date: Starting date to search from
        chat_id: Chat ID for logging
        max_days: Maximum number of days to search ahead (default: 14)
        
    Returns:
        Date object for nearest available date, or None if none found
    """
    current_date = start_date + timedelta(days=1)
    end_date = start_date + timedelta(days=max_days)
    
    while current_date <= end_date:
        slots = await _get_available_time_slots(
            tools=tools,
            court_id=court_id,
            date_obj=current_date,
            chat_id=chat_id
        )
        
        if slots:
            logger.info(
                f"Found nearest available date for court {court_id}: {current_date}"
            )
            return current_date
        
        current_date += timedelta(days=1)
    
    logger.warning(
        f"No available dates found for court {court_id} "
        f"within {max_days} days from {start_date}"
    )
    return None


async def _parse_time_with_llm(
    llm_provider: LLMProvider,
    user_message: str,
    available_slots: List[Dict[str, Any]],
    flow_state: Dict[str, Any],
    chat_id: str
) -> Optional[Dict[str, Any]]:
    """
    Parse time selection using LLM.
    
    This function uses the LLM to intelligently parse the user's
    time selection from natural language input.
    
    Args:
        llm_provider: LLMProvider for creating LangChain LLM
        user_message: User's selection message
        available_slots: List of available slot dictionaries
        flow_state: Current flow state
        chat_id: Chat ID for logging
        
    Returns:
        Selected slot dictionary or None if parsing fails
    """
    try:
        llm = create_langchain_llm(llm_provider)
    except Exception as e:
        logger.error(f"Failed to create LangChain LLM for chat {chat_id}: {e}", exc_info=True)
        return None
    
    # Create prompt for time selection
    property_name = flow_state.get("property_name", "the property")
    court_name = flow_state.get("court_name", "the court")
    date_str = flow_state.get("date", "")
    current_date = datetime.now().date().strftime("%Y-%m-%d")  # ISO format
    
    prompt = create_select_time_prompt(property_name, court_name, date_str, available_slots, current_date)
    
    # Use LLM to parse selection
    try:
        messages = prompt.format_messages(input=user_message)
        response_obj = await llm.ainvoke(messages)
        agent_response = response_obj.content.strip()
        
        logger.debug(f"Agent response for time selection: {agent_response}")
        
        # Try to extract start time from response (HH:MM:SS format)
        time_match = re.search(r'(\d{2}):(\d{2}):(\d{2})', agent_response)
        
        if time_match:
            start_time_str = time_match.group(0)
            
            # Find slot with this start time
            for slot in available_slots:
                if slot.get("start_time") == start_time_str:
                    return slot
        
        # No match found
        return None
        
    except Exception as e:
        logger.error(f"Error using LangChain agent for time selection in chat {chat_id}: {e}", exc_info=True)
        return None
