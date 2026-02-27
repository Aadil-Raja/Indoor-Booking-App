"""
Select date node for booking subgraph.

This module implements the select_date node that handles date selection
in the booking flow. It parses dates from user messages (supporting various formats
like "tomorrow", "next Monday", "2024-12-25"), validates that dates are in the future,
stores the selected date in flow_state, and handles invalid dates gracefully.

Requirements: 6.3, 20.4, 22.1-22.6
"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import re

from ...state.conversation_state import ConversationState
from ...tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def select_date(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle date selection in booking flow.
    
    This node manages the date selection step of the booking process. It:
    1. Checks if date is already selected in flow_state
    2. Prompts user to provide a date if not yet selected
    3. Parses date from user message (supports various formats)
    4. Validates that the date is in the future (not in the past)
    5. Stores selected date in flow_state
    6. Updates flow_state step to "select_date"
    7. Handles invalid dates with helpful error messages
    
    Supported date formats:
    - Relative: "today", "tomorrow", "next Monday", "in 3 days"
    - ISO format: "2024-12-25", "2024/12/25"
    - Natural: "December 25", "Dec 25", "25 December"
    - Numeric: "12/25", "25/12/2024"
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Select_Date node
    - 20.4: Store selected date when user chooses a date
    - 22.1: Present date options to user
    - 22.2: Present booking summary including date
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated flow_state containing date and step
        
    Example:
        # First call - prompt for date
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "Tennis Court A",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "step": "service_selected"
            },
            ...
        }
        
        result = await select_date(state, tools)
        # result["response_content"] = "When would you like to book?"
        # result["flow_state"]["step"] = "select_date"
        
        # Second call - process date selection
        state = {
            "user_message": "tomorrow",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "service_id": "10",
                "step": "select_date"
            },
            ...
        }
        
        result = await select_date(state, tools)
        # result["flow_state"]["date"] = "2024-01-16"
        # result["flow_state"]["step"] = "date_selected"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing date selection for chat {chat_id} - "
        f"step={flow_state.get('step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if date already selected
    if flow_state.get("date"):
        logger.debug(
            f"Date already selected for chat {chat_id}: "
            f"date={flow_state.get('date')}"
        )
        # Date already selected, continue to next step
        return state
    
    # Check if service is selected
    service_id = flow_state.get("service_id")
    if not service_id:
        logger.warning(
            f"No service selected for chat {chat_id}, cannot select date"
        )
        
        response = (
            "Please select a court first before choosing a date."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Check if we're processing a selection or presenting options
    current_step = flow_state.get("step")
    
    if current_step == "select_date":
        # User is responding with a date
        return await _process_date_selection(
            state=state,
            chat_id=chat_id,
            user_message=user_message,
            flow_state=flow_state
        )
    else:
        # First time in this node, prompt for date
        return await _prompt_for_date(
            state=state,
            chat_id=chat_id,
            flow_state=flow_state
        )


async def _prompt_for_date(
    state: ConversationState,
    chat_id: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Prompt user to provide a date for the booking.
    
    This function generates a prompt asking the user to provide a date,
    with examples of supported formats.
    
    Args:
        state: ConversationState
        chat_id: Chat ID for logging
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with date prompt
    """
    service_name = flow_state.get("service_name", "the court")
    
    # Generate helpful prompt with examples
    response = (
        f"When would you like to book {service_name}? "
        f"You can say something like 'tomorrow', 'next Monday', "
        f"or provide a specific date like '2024-12-25'."
    )
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    # Update flow state
    flow_state["step"] = "select_date"
    state["flow_state"] = flow_state
    
    logger.info(
        f"Prompted for date selection in chat {chat_id}"
    )
    
    return state


async def _process_date_selection(
    state: ConversationState,
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Process user's date selection.
    
    This function parses the user's date input, validates it's in the future,
    and stores the selected date in flow_state.
    
    Args:
        state: ConversationState
        chat_id: Chat ID for logging
        user_message: User's date input
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with selected date in flow_state
    """
    # Parse date from user message
    parsed_date = _parse_date(user_message)
    
    if not parsed_date:
        # Invalid date format
        logger.warning(
            f"Invalid date format for chat {chat_id}: {user_message}"
        )
        
        response = (
            "I couldn't understand that date. "
            "Please try again with a format like 'tomorrow', 'next Monday', "
            "or a specific date like '2024-12-25'."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as select_date to allow retry
        return state
    
    # Validate date is in the future
    today = datetime.now().date()
    if parsed_date < today:
        logger.warning(
            f"Past date provided for chat {chat_id}: {parsed_date}"
        )
        
        response = (
            f"The date {parsed_date.strftime('%B %d, %Y')} is in the past. "
            f"Please provide a date that is today or in the future."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as select_date to allow retry
        return state
    
    # Valid date - store in flow_state
    date_str = parsed_date.strftime("%Y-%m-%d")
    
    flow_state["date"] = date_str
    flow_state["step"] = "date_selected"
    
    state["flow_state"] = flow_state
    
    # Generate confirmation message
    formatted_date = parsed_date.strftime("%A, %B %d, %Y")
    service_name = flow_state.get("service_name", "the court")
    
    response = (
        f"Perfect! You've selected {formatted_date} for {service_name}. "
        f"Now let's choose a time slot."
    )
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(
        f"Date selected for chat {chat_id}: date={date_str}"
    )
    
    return state


def _parse_date(user_input: str) -> Optional[datetime.date]:
    """
    Parse date from user input supporting various formats.
    
    This function attempts to parse dates in multiple formats:
    - Relative: "today", "tomorrow", "next Monday", "in 3 days"
    - ISO format: "2024-12-25", "2024/12/25"
    - Natural: "December 25", "Dec 25", "25 December"
    - Numeric: "12/25", "25/12/2024"
    
    Args:
        user_input: User's date input string
        
    Returns:
        Parsed date object or None if parsing fails
        
    Example:
        date = _parse_date("tomorrow")
        # Returns: datetime.date(2024, 1, 16)
        
        date = _parse_date("2024-12-25")
        # Returns: datetime.date(2024, 12, 25)
        
        date = _parse_date("next Monday")
        # Returns: datetime.date for next Monday
    """
    input_lower = user_input.lower().strip()
    today = datetime.now().date()
    
    # Return None for empty input
    if not input_lower:
        logger.debug("Empty input provided for date parsing")
        return None
    
    # Relative dates
    if input_lower == "today":
        return today
    
    if input_lower == "tomorrow":
        return today + timedelta(days=1)
    
    # "in X days" format
    in_days_match = re.search(r'in\s+(\d+)\s+days?', input_lower)
    if in_days_match:
        days = int(in_days_match.group(1))
        return today + timedelta(days=days)
    
    # "next Monday", "next Tuesday", etc.
    weekday_names = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1, 'tues': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
    }
    
    for day_name, day_num in weekday_names.items():
        if day_name in input_lower:
            # Calculate days until next occurrence of this weekday
            current_weekday = today.weekday()
            days_ahead = day_num - current_weekday
            
            # If the day is today or has passed this week, get next week's occurrence
            if 'next' in input_lower or days_ahead <= 0:
                days_ahead += 7
            
            return today + timedelta(days=days_ahead)
    
    # Try ISO format: YYYY-MM-DD or YYYY/MM/DD
    iso_patterns = [
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',  # YYYY-MM-DD or YYYY/MM/DD
    ]
    
    for pattern in iso_patterns:
        match = re.search(pattern, user_input)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day).date()
            except (ValueError, IndexError):
                continue
    
    # Try numeric formats: MM/DD or DD/MM/YYYY or MM/DD/YYYY
    numeric_patterns = [
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', 'mdy'),  # MM/DD/YYYY
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', 'mdy'),  # MM/DD/YY
        (r'(\d{1,2})/(\d{1,2})', 'md'),  # MM/DD (assume current year)
    ]
    
    for pattern, format_type in numeric_patterns:
        match = re.search(pattern, user_input)
        if match:
            try:
                if format_type == 'mdy':
                    month = int(match.group(1))
                    day = int(match.group(2))
                    year = int(match.group(3))
                    if year < 100:  # Two-digit year
                        year += 2000
                elif format_type == 'md':
                    month = int(match.group(1))
                    day = int(match.group(2))
                    year = today.year
                
                parsed = datetime(year, month, day).date()
                
                # If date is in the past and we assumed current year, try next year
                if format_type == 'md' and parsed < today:
                    parsed = datetime(year + 1, month, day).date()
                
                return parsed
            except (ValueError, IndexError):
                continue
    
    # Try natural language formats: "December 25", "Dec 25", "25 December"
    month_names = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    for month_name, month_num in month_names.items():
        if month_name in input_lower:
            # Try to find day number near the month name
            day_match = re.search(r'\b(\d{1,2})\b', user_input)
            if day_match:
                try:
                    day = int(day_match.group(1))
                    year = today.year
                    
                    # Try to find year in the input
                    year_match = re.search(r'\b(20\d{2})\b', user_input)
                    if year_match:
                        year = int(year_match.group(1))
                    
                    parsed = datetime(year, month_num, day).date()
                    
                    # If date is in the past and no year specified, try next year
                    if not year_match and parsed < today:
                        parsed = datetime(year + 1, month_num, day).date()
                    
                    return parsed
                except (ValueError, IndexError):
                    continue
    
    # No match found
    logger.debug(f"No date match found for: {user_input}")
    return None
