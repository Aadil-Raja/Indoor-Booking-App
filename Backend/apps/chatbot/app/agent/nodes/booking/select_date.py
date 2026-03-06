"""
Select date node for booking subgraph.

This module implements the select_date node that handles date selection
in the booking flow using LangChain agent. It uses an LLM agent to parse dates
from user messages (supporting various formats), validates that dates are in the future,
stores the selected date in flow_state, and handles invalid dates gracefully.

Requirements: 7.3, 8.2, 8.5, 17.1, 17.2, 17.3, 17.4, 17.5
"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import re

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.booking_prompts import create_select_date_prompt
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


async def select_date(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle date selection in booking flow with LLM parsing.
    
    This node manages the date selection step of the booking process. It:
    1. Checks if date is already selected in flow_state (skip if exists) - Req 7.3
    2. Passes current date (YYYY-MM-DD format) to LLM in the prompt context - Req 17.1, 17.5
    3. Uses LLM to parse date from user message (natural language → YYYY-MM-DD) - Req 17.2, 17.3
    4. Supports natural language like "tomorrow", "next Monday", etc. by providing current date context - Req 17.4
    5. Validates date format and future date - Req 8.5
    6. If date parsed: stores in flow_state and updates booking_step to "date_selected" - Req 8.2
    7. If date not parsed: asks user for date
    8. Returns next_node decision for routing
    
    Supported date formats:
    - Relative: "today", "tomorrow", "next Monday", "in 3 days"
    - ISO format: "2024-12-25", "2024/12/25"
    - Natural: "December 25", "Dec 25", "25 December"
    - Numeric: "12/25", "25/12/2024"
    
    Implements Requirements:
    - 7.3: Skip date selection step when Flow_State contains date
    - 8.2: Update booking_step field in Flow_State when step is completed
    - 8.5: Validate each step's data before proceeding to the next step
    - 17.1: LLM receives current date in ISO format (YYYY-MM-DD) as part of conversation context
    - 17.2: LLM calculates "tomorrow" as current_date + 1 day
    - 17.3: LLM calculates "next Monday" based on current date
    - 17.4: LLM converts all natural language date references to YYYY-MM-DD format
    - 17.5: Current date included in all LLM prompts that involve date selection or parsing
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          updated flow_state containing date and booking_step, and next_node decision
        
    Example:
        # Case 1: Date already selected (skip)
        state = {
            "chat_id": "123",
            "flow_state": {"date": "2024-12-25"},
            ...
        }
        result = await select_date(state, llm_provider)
        # result["next_node"] = "select_time"
        
        # Case 2: First call - prompt for date
        state = {
            "chat_id": "123",
            "user_message": "Tennis Court A",
            "flow_state": {
                "property_id": "1",
                "court_id": "10",
                "booking_step": "court_selected"
            },
            ...
        }
        
        result = await select_date(state, llm_provider)
        # result["response_content"] = "When would you like to book?"
        # result["flow_state"]["booking_step"] = "awaiting_date_selection"
        # result["next_node"] = "wait_for_selection"
        
        # Case 3: Process date selection
        state = {
            "user_message": "tomorrow",
            "flow_state": {
                "property_id": "1",
                "court_id": "10",
                "booking_step": "awaiting_date_selection"
            },
            ...
        }
        
        result = await select_date(state, llm_provider)
        # result["flow_state"]["date"] = "2024-01-16"
        # result["flow_state"]["booking_step"] = "date_selected"
        # result["next_node"] = "select_time"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing date selection for chat {chat_id} - "
        f"booking_step={flow_state.get('booking_step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Step 1: Check if date already selected (Requirement 7.3)
    if flow_state.get("date"):
        logger.debug(
            f"Date already selected for chat {chat_id}: "
            f"date={flow_state.get('date')}"
        )
        # Date already selected, skip to next step
        state["next_node"] = "select_time"
        return state
    
    # Step 2: Check if court is selected
    court_id = flow_state.get("court_id")
    if not court_id:
        logger.warning(
            f"No court selected for chat {chat_id}, cannot select date"
        )
        
        response = (
            "Please select a court first before choosing a date."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_court"
        
        return state
    
    # Step 3: Check if we're processing a selection or presenting options
    current_step = flow_state.get("booking_step")
    
    if current_step == "awaiting_date_selection":
        # User is responding with a date
        return await _process_date_selection(
            state=state,
            llm_provider=llm_provider,
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
        Updated ConversationState with date prompt and next_node decision
    """
    court_name = flow_state.get("court_name", "the court")
    
    # Generate helpful prompt with examples
    response = (
        f"When would you like to book {court_name}? "
        f"You can say something like 'tomorrow', 'next Monday', "
        f"or provide a specific date like '2024-12-25'."
    )
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    # Update flow state (Requirement 8.2)
    flow_state["booking_step"] = "awaiting_date_selection"
    state["flow_state"] = flow_state
    
    # Wait for user selection
    state["next_node"] = "wait_for_selection"
    
    logger.info(
        f"Prompted for date selection in chat {chat_id}"
    )
    
    return state


async def _process_date_selection(
    state: ConversationState,
    llm_provider: LLMProvider,
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Process user's date selection using LangChain agent with current date context.
    
    This function uses a LangChain agent to intelligently parse the user's
    date input with current date context for natural language parsing,
    validates it's in the future, and stores the selected date in flow_state.
    
    Implements Requirements:
    - 17.1: Pass current date in ISO format to LLM
    - 17.2: Support "tomorrow" calculation
    - 17.3: Support "next Monday" calculation
    - 17.4: Convert natural language to YYYY-MM-DD format
    - 17.5: Include current date in all date-related prompts
    - 8.2: Update booking_step when date is selected
    - 8.5: Validate date before proceeding
    
    Args:
        state: ConversationState
        llm_provider: LLMProvider for creating LangChain LLM
        chat_id: Chat ID for logging
        user_message: User's date input
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with selected date in flow_state and next_node decision
    """
    # Create LangChain LLM
    try:
        llm = create_langchain_llm(llm_provider)
    except Exception as e:
        logger.error(f"Failed to create LangChain LLM for chat {chat_id}: {e}", exc_info=True)
        # Fallback to manual parsing
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
            state["next_node"] = "wait_for_selection"
            
            return state
        
        # Validate date is in the future (Requirement 8.5)
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
            state["next_node"] = "wait_for_selection"
            
            return state
        
        # Valid date - store in flow_state
        date_str = parsed_date.strftime("%Y-%m-%d")
        
        flow_state["date"] = date_str
        flow_state["booking_step"] = "date_selected"  # Requirement 8.2
        
        state["flow_state"] = flow_state
        
        # Generate confirmation message
        formatted_date = parsed_date.strftime("%A, %B %d, %Y")
        court_name = flow_state.get("court_name", "the court")
        
        response = (
            f"Perfect! You've selected {formatted_date} for {court_name}. "
            f"Now let's choose a time slot."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_time"
        
        logger.info(
            f"Date selected for chat {chat_id}: date={date_str}"
        )
        
        return state
    
    # Create prompt for date selection with current date context (Requirements 17.1, 17.5)
    property_name = flow_state.get("property_name", "the property")
    court_name = flow_state.get("court_name", "the court")
    current_date = datetime.now().date().strftime("%Y-%m-%d")  # ISO format
    
    prompt = create_select_date_prompt(property_name, court_name, current_date)
    
    # Use LLM to parse date
    try:
        messages = prompt.format_messages(input=user_message)
        response_obj = await llm.ainvoke(messages)
        agent_response = response_obj.content.strip()
        
        logger.debug(f"Agent response for date selection: {agent_response}")
        
        # Try to extract ISO date from response (YYYY-MM-DD)
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', agent_response)
        
        if date_match:
            try:
                parsed_date = datetime.strptime(date_match.group(0), "%Y-%m-%d").date()
                
                # Validate date is in the future (Requirement 8.5)
                today = datetime.now().date()
                if parsed_date < today:
                    response = (
                        f"The date {parsed_date.strftime('%B %d, %Y')} is in the past. "
                        f"Please provide a date that is today or in the future."
                    )
                    
                    state["response_content"] = response
                    state["response_type"] = "text"
                    state["response_metadata"] = {}
                    state["next_node"] = "wait_for_selection"
                    
                    return state
                
                # Valid date - store in flow_state
                date_str = parsed_date.strftime("%Y-%m-%d")
                
                flow_state["date"] = date_str
                flow_state["booking_step"] = "date_selected"  # Requirement 8.2
                
                state["flow_state"] = flow_state
                
                # Generate confirmation message
                formatted_date = parsed_date.strftime("%A, %B %d, %Y")
                
                response = (
                    f"Perfect! You've selected {formatted_date} for {court_name}. "
                    f"Now let's choose a time slot."
                )
                
                state["response_content"] = response
                state["response_type"] = "text"
                state["response_metadata"] = {}
                state["next_node"] = "select_time"
                
                logger.info(
                    f"Date selected for chat {chat_id}: date={date_str}"
                )
                
                return state
                
            except ValueError:
                pass
        
        # Agent is asking for clarification or couldn't parse
        state["response_content"] = agent_response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "wait_for_selection"
        
        logger.info(f"Agent asking for clarification in chat {chat_id}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error using LangChain agent for date selection in chat {chat_id}: {e}", exc_info=True)
        
        # Fallback to manual parsing
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
            state["next_node"] = "wait_for_selection"
            
            return state
        
        # Validate date is in the future (Requirement 8.5)
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
            state["next_node"] = "wait_for_selection"
            
            return state
        
        # Valid date - store in flow_state
        date_str = parsed_date.strftime("%Y-%m-%d")
        
        flow_state["date"] = date_str
        flow_state["booking_step"] = "date_selected"  # Requirement 8.2
        
        state["flow_state"] = flow_state
        
        # Generate confirmation message
        formatted_date = parsed_date.strftime("%A, %B %d, %Y")
        court_name = flow_state.get("court_name", "the court")
        
        response = (
            f"Perfect! You've selected {formatted_date} for {court_name}. "
            f"Now let's choose a time slot."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_time"
        
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
