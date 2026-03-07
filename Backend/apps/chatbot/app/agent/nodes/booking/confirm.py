"""
Confirm booking node for booking subgraph.

This module implements the confirm_booking node that handles booking confirmation
in the booking flow. It builds a booking summary, fetches pricing, uses LLM to check
for user confirmation, and routes appropriately based on user intent.

Requirements: 8.1, 8.3, 8.4
"""

from typing import Dict, Any
import logging
from datetime import datetime

from app.agent.state.conversation_state import ConversationState
from app.agent.tools.pricing_tool import get_pricing_tool
from app.services.llm.base import LLMProvider
from app.agent.prompts.booking_prompts import create_confirm_booking_prompt
from app.agent.nodes.booking.flow_validation import (
    validate_required_fields_for_step,
    get_booking_progress_summary
)

logger = logging.getLogger(__name__)


async def confirm_booking(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Dict[str, Any]
) -> ConversationState:
    """
    Handle booking confirmation in booking flow.
    
    This node manages the confirmation step of the booking process. It:
    1. Builds booking summary (property, court, date, time) - Req 8.1
    2. Fetches pricing using get_pricing_tool
    3. Uses LLM to check for user confirmation
    4. If confirmed: updates booking_step to "confirming" and routes to create_booking
    5. If user wants to modify: routes back to appropriate selection node - Req 8.3
    6. If cancelled: clears flow_state and ends - Req 8.4
    7. Returns next_node decision
    
    Implements Requirements:
    - 8.1: Present confirmation to user when all booking information is collected
    - 8.3: Allow user to modify booking details
    - 8.4: Handle booking cancellation
    
    Args:
        state: ConversationState containing user message, flow_state, and identifiers
        llm_provider: LLMProvider for creating LLM calls
        tools: Tool registry containing pricing tools
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          updated flow_state, and next_node decision
        
    Example:
        # Case 1: First call - present summary
        state = {
            "chat_id": "123",
            "user_message": "",
            "flow_state": {
                "property_id": 1,
                "property_name": "Sports Center",
                "court_id": 10,
                "court_name": "Tennis Court A",
                "date": "2024-12-25",
                "time_slot": "14:00-15:00",
                "booking_step": "time_selected"
            },
            ...
        }
        result = await confirm_booking(state, llm_provider, tools)
        # result["response_content"] = "Here's your booking summary..."
        # result["flow_state"]["booking_step"] = "awaiting_confirmation"
        # result["next_node"] = "wait_for_confirmation"
        
        # Case 2: User confirms
        state = {
            "user_message": "yes, confirm",
            "flow_state": {
                ...
                "booking_step": "awaiting_confirmation"
            },
            ...
        }
        result = await confirm_booking(state, llm_provider, tools)
        # result["flow_state"]["booking_step"] = "confirming"
        # result["next_node"] = "create_booking"
        
        # Case 3: User wants to modify
        state = {
            "user_message": "change the time",
            "flow_state": {
                ...
                "booking_step": "awaiting_confirmation"
            },
            ...
        }
        result = await confirm_booking(state, llm_provider, tools)
        # result["next_node"] = "select_time"
        
        # Case 4: User cancels
        state = {
            "user_message": "cancel",
            "flow_state": {
                ...
                "booking_step": "awaiting_confirmation"
            },
            ...
        }
        result = await confirm_booking(state, llm_provider, tools)
        # result["flow_state"] = {}  # Cleared
        # result["next_node"] = "end"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
    # Log booking progress for debugging
    progress = get_booking_progress_summary(flow_state)
    logger.info(
        f"Processing booking confirmation for chat {chat_id} - "
        f"progress={progress['completion_percentage']}%, "
        f"booking_step={flow_state.get('booking_step')}, "
        f"message_preview={user_message[:50] if user_message else 'N/A'}..."
    )
    
    # Validate prerequisites - all booking steps must be complete
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "confirm_booking",
        flow_state
    )
    if not is_valid:
        logger.warning(
            f"Cannot confirm booking without {missing_field} for chat {chat_id}, "
            f"redirecting to {redirect_node}"
        )
        
        state["response_content"] = (
            f"Some booking information is missing. Let's complete the {missing_field} selection."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = redirect_node
        
        return state
    
    # Check if we're presenting the summary or processing confirmation
    current_step = flow_state.get("booking_step")
    
    if current_step == "awaiting_confirmation":
        # User is responding to confirmation request
        return await _process_confirmation_response(
            state=state,
            llm_provider=llm_provider,
            chat_id=chat_id,
            user_message=user_message,
            flow_state=flow_state
        )
    else:
        # First time in this node, present booking summary
        return await _present_booking_summary(
            state=state,
            tools=tools,
            chat_id=chat_id,
            flow_state=flow_state
        )


async def _present_booking_summary(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Present booking summary to the user with pricing information.
    
    This function builds a comprehensive booking summary including all selected
    details and fetches pricing information to show the total cost.
    
    Implements Requirement 8.1: Present confirmation when all booking information is collected
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with booking summary and next_node decision
    """
    # Validate that all required booking information is present
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "confirm_booking",
        flow_state
    )
    
    if not is_valid:
        logger.error(
            f"Missing required booking information for chat {chat_id}: {missing_field}, "
            f"redirecting to {redirect_node}"
        )
        
        response = (
            f"Some booking information is missing. Let's complete the {missing_field} selection."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = redirect_node
        
        return state
    
    # Extract booking details
    property_name = flow_state.get("property_name")
    court_name = flow_state.get("court_name")
    court_id = flow_state.get("court_id")
    date_str = flow_state.get("date")
    time_slot = flow_state.get("time_slot")
    
    # Parse time_slot to get start and end times
    try:
        start_time_str, end_time_str = time_slot.split("-")
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.strptime(end_time_str, "%H:%M").time()
        
        # Calculate duration in hours
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_datetime = datetime.combine(datetime.today(), end_time)
        duration = (end_datetime - start_datetime).total_seconds() / 3600
        
    except (ValueError, AttributeError) as e:
        logger.error(
            f"Invalid time_slot format in flow_state for chat {chat_id}: {time_slot}, error: {e}"
        )
        
        response = (
            "There was an error with the selected time. "
            "Please select a time slot again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_time"
        
        # Clear time_slot
        flow_state["time_slot"] = None
        flow_state["booking_step"] = "date_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Parse date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        logger.error(
            f"Invalid date format in flow_state for chat {chat_id}: {date_str}"
        )
        formatted_date = date_str
        date_obj = None
    
    # Fetch pricing information
    pricing_info = None
    total_price = None
    price_per_hour = None
    
    if date_obj:
        try:
            pricing_data = await get_pricing_tool(
                court_id=int(court_id),
                date_val=date_obj
            )
            
            if pricing_data and pricing_data.get("pricing"):
                # Find applicable pricing rule for the start time
                for rule in pricing_data["pricing"]:
                    rule_start = datetime.strptime(rule["start_time"], "%H:%M:%S").time()
                    rule_end = datetime.strptime(rule["end_time"], "%H:%M:%S").time()
                    
                    if rule_start <= start_time < rule_end:
                        price_per_hour = rule["price_per_hour"]
                        total_price = price_per_hour * duration
                        pricing_info = {
                            "price_per_hour": price_per_hour,
                            "total_price": total_price,
                            "duration": duration,
                            "label": rule.get("label", "")
                        }
                        break
                
                if pricing_info:
                    logger.info(
                        f"Fetched pricing for chat {chat_id}: "
                        f"${price_per_hour}/hour, total=${total_price:.2f}"
                    )
                else:
                    logger.warning(
                        f"No pricing rule found for time {start_time} on {date_obj} "
                        f"for court {court_id} in chat {chat_id}"
                    )
            else:
                logger.warning(
                    f"No pricing data available for court {court_id} "
                    f"on {date_obj} in chat {chat_id}"
                )
                
        except Exception as e:
            logger.error(
                f"Error fetching pricing for chat {chat_id}: {e}",
                exc_info=True
            )
    
    # Build booking summary message
    summary_lines = [
        "Here's your booking summary:",
        "",
        f"📍 Property: {property_name}",
        f"🎾 Court: {court_name}",
        f"📅 Date: {formatted_date}",
        f"⏰ Time: {_format_time_for_display(start_time_str)} - {_format_time_for_display(end_time_str)}",
    ]
    
    if pricing_info:
        summary_lines.extend([
            f"⏱️ Duration: {duration:.1f} hour(s)",
            f"💰 Price: ${price_per_hour:.2f}/hour",
            f"💵 Total: ${total_price:.2f}"
        ])
        
        if pricing_info.get("label"):
            summary_lines.append(f"   ({pricing_info['label']})")
        
        # Store pricing in flow_state for booking creation
        flow_state["price_per_hour"] = price_per_hour
        flow_state["total_price"] = total_price
        flow_state["duration_hours"] = duration
    else:
        summary_lines.append("💰 Price: To be determined")
    
    summary_lines.extend([
        "",
        "Would you like to confirm this booking?"
    ])
    
    response = "\n".join(summary_lines)
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {
        "booking_summary": {
            "property_name": property_name,
            "court_name": court_name,
            "date": date_str,
            "formatted_date": formatted_date,
            "time_slot": time_slot,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "duration": duration if pricing_info else None,
            "price_per_hour": price_per_hour,
            "total_price": total_price
        }
    }
    
    # Update flow state
    flow_state["booking_step"] = "awaiting_confirmation"
    state["flow_state"] = flow_state
    
    # Wait for user confirmation
    state["next_node"] = "wait_for_confirmation"
    
    logger.info(
        f"Presented booking summary for chat {chat_id}"
    )
    
    return state


async def _process_confirmation_response(
    state: ConversationState,
    llm_provider: LLMProvider,
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Process user's response to booking confirmation using LLM.
    
    This function uses an LLM to intelligently parse the user's response
    and determine their intent: confirm, modify, or cancel.
    
    Implements Requirements:
    - 8.3: Allow user to modify booking details
    - 8.4: Handle booking cancellation
    
    Args:
        state: ConversationState
        llm_provider: LLMProvider for creating LLM calls
        chat_id: Chat ID for logging
        user_message: User's confirmation response
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with next_node decision based on user intent
    """
    # Use LLM to parse user intent
    try:
        # Get current date for validation context
        current_date = datetime.now().date().strftime("%Y-%m-%d")  # ISO format
        
        # Create confirmation prompt
        prompt = create_confirm_booking_prompt(flow_state, current_date)
        
        # Prepare messages for LLM
        messages = [
            {"role": "user", "content": user_message}
        ]
        
        # Call LLM
        llm_response = await llm_provider.invoke(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent parsing
            max_tokens=50  # Short response expected
        )
        
        # Extract response text
        response_text = llm_response.get("content", "").strip().upper()
        
        logger.debug(
            f"LLM confirmation response for chat {chat_id}: {response_text}"
        )
        
    except Exception as e:
        logger.error(
            f"Error calling LLM for confirmation parsing in chat {chat_id}: {e}",
            exc_info=True
        )
        # Fallback to simple keyword matching
        response_text = _parse_confirmation_fallback(user_message)
    
    # Route based on LLM response
    if response_text == "CONFIRM":
        # User confirmed - proceed to booking creation
        logger.info(f"Booking confirmed for chat {chat_id}")
        
        flow_state["booking_step"] = "confirming"
        state["flow_state"] = flow_state
        
        state["response_content"] = "Great! Creating your booking..."
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "create_booking"
        
        return state
    
    elif response_text == "CANCEL":
        # User cancelled - clear flow_state and end (Requirement 8.4)
        logger.info(f"Booking cancelled for chat {chat_id}")
        
        state["flow_state"] = {}  # Clear flow_state
        
        state["response_content"] = "No problem! Your booking has been cancelled. Let me know if you'd like to book something else."
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        return state
    
    elif response_text.startswith("CHANGE_"):
        # User wants to modify something (Requirement 8.3)
        change_type = response_text.replace("CHANGE_", "").lower()
        
        logger.info(
            f"Booking modification requested for chat {chat_id}: {change_type}"
        )
        
        # Route to appropriate selection node
        if change_type == "property":
            # Clear property and all subsequent selections
            flow_state["property_id"] = None
            flow_state["property_name"] = None
            flow_state["court_id"] = None
            flow_state["court_name"] = None
            flow_state["date"] = None
            flow_state["time_slot"] = None
            flow_state["booking_step"] = None
            
            state["response_content"] = "Sure! Let's select a different property."
            state["next_node"] = "select_property"
            
        elif change_type == "service" or change_type == "court":
            # Clear court and subsequent selections
            flow_state["court_id"] = None
            flow_state["court_name"] = None
            flow_state["date"] = None
            flow_state["time_slot"] = None
            flow_state["booking_step"] = "property_selected"
            
            state["response_content"] = "Sure! Let's select a different court."
            state["next_node"] = "select_court"
            
        elif change_type == "date":
            # Clear date and subsequent selections
            flow_state["date"] = None
            flow_state["time_slot"] = None
            flow_state["booking_step"] = "court_selected"
            
            state["response_content"] = "Sure! Let's select a different date."
            state["next_node"] = "select_date"
            
        elif change_type == "time":
            # Clear only time
            flow_state["time_slot"] = None
            flow_state["booking_step"] = "date_selected"
            
            state["response_content"] = "Sure! Let's select a different time."
            state["next_node"] = "select_time"
            
        else:
            # Unknown change type - default to property
            logger.warning(
                f"Unknown change type for chat {chat_id}: {change_type}, "
                f"defaulting to property selection"
            )
            
            flow_state["property_id"] = None
            flow_state["property_name"] = None
            flow_state["court_id"] = None
            flow_state["court_name"] = None
            flow_state["date"] = None
            flow_state["time_slot"] = None
            flow_state["booking_step"] = None
            
            state["response_content"] = "Sure! Let's start over with property selection."
            state["next_node"] = "select_property"
        
        state["flow_state"] = flow_state
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    elif response_text == "CLARIFY":
        # LLM needs clarification - ask user again
        logger.debug(f"Confirmation unclear for chat {chat_id}, asking again")
        
        state["response_content"] = (
            "I'm not sure what you'd like to do. "
            "Would you like to:\n"
            "- Confirm this booking (say 'yes' or 'confirm')\n"
            "- Make changes (say 'change' followed by what you want to change)\n"
            "- Cancel (say 'cancel' or 'no')"
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "wait_for_confirmation"
        
        return state
    
    else:
        # Unknown response - ask for clarification
        logger.warning(
            f"Unknown confirmation response for chat {chat_id}: {response_text}"
        )
        
        state["response_content"] = (
            "I didn't quite understand that. "
            "Would you like to confirm this booking? (yes/no)"
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "wait_for_confirmation"
        
        return state


def _parse_confirmation_fallback(user_message: str) -> str:
    """
    Fallback confirmation parsing using simple keyword matching.
    
    This function is used when LLM parsing fails or is unavailable.
    
    Args:
        user_message: User's message
        
    Returns:
        One of: "CONFIRM", "CANCEL", "CHANGE_PROPERTY", "CHANGE_SERVICE",
                "CHANGE_DATE", "CHANGE_TIME", "CLARIFY"
    """
    message_lower = user_message.lower().strip()
    
    # Check for confirmation
    confirm_keywords = ["yes", "confirm", "book", "proceed", "ok", "okay", "sure", "yep", "yeah"]
    if any(word in message_lower for word in confirm_keywords):
        return "CONFIRM"
    
    # Check for cancellation
    cancel_keywords = ["no", "cancel", "nevermind", "never mind", "stop", "don't"]
    if any(word in message_lower for word in cancel_keywords):
        return "CANCEL"
    
    # Check for modification
    if "change" in message_lower or "modify" in message_lower or "different" in message_lower:
        # Determine what to change
        if "property" in message_lower or "facility" in message_lower or "place" in message_lower:
            return "CHANGE_PROPERTY"
        elif "court" in message_lower or "service" in message_lower:
            return "CHANGE_SERVICE"
        elif "date" in message_lower or "day" in message_lower:
            return "CHANGE_DATE"
        elif "time" in message_lower or "slot" in message_lower:
            return "CHANGE_TIME"
        else:
            # Generic change - default to property
            return "CHANGE_PROPERTY"
    
    # Need clarification
    return "CLARIFY"


def _format_time_for_display(time_str: str) -> str:
    """
    Format time string for user-friendly display.
    
    Converts 24-hour format (HH:MM) to 12-hour format with AM/PM.
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        Formatted time string (e.g., "2:00 PM")
    """
    try:
        # Parse time string
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        
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
