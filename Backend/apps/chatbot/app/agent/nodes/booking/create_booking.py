"""
Create booking node for booking subgraph.

This module implements the create_booking node that handles the final booking creation
in the booking flow. It parses the time_slot, calls the booking tool, handles success/failure,
and clears flow_state upon completion.

Requirements: 8.5, 15.5
"""

from typing import Dict, Any
import logging
from datetime import datetime, time

from app.agent.state.conversation_state import ConversationState
from app.agent.tools.booking_tool import create_booking_tool

logger = logging.getLogger(__name__)


async def create_booking(
    state: ConversationState,
    tools: Dict[str, Any]
) -> ConversationState:
    """
    Handle booking creation in booking flow.
    
    This node manages the final booking creation step. It:
    1. Parses time_slot into start_time and end_time
    2. Calls create_booking_tool with all booking data
    3. If success: clears flow_state and returns confirmation message - Req 15.5
    4. If failure: returns error and routes back to time_selection
    5. Validates all required data before proceeding - Req 8.5
    
    Implements Requirements:
    - 8.5: Validate each step's data before proceeding
    - 15.5: Clear flow_state when booking is completed or cancelled
    
    Args:
        state: ConversationState containing user_id, flow_state, and booking details
        tools: Tool registry containing booking tools
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          cleared flow_state (on success), and next_node decision
        
    Example:
        # Case 1: Successful booking creation
        state = {
            "chat_id": "123",
            "user_id": "456",
            "flow_state": {
                "property_id": 1,
                "property_name": "Sports Center",
                "court_id": 10,
                "court_name": "Tennis Court A",
                "date": "2024-12-25",
                "time_slot": "14:00-15:00",
                "total_price": 75.0,
                "booking_step": "confirming"
            },
            ...
        }
        result = await create_booking(state, tools)
        # result["response_content"] = "Booking confirmed! Your booking ID is..."
        # result["flow_state"] = {}  # Cleared
        # result["next_node"] = "end"
        
        # Case 2: Booking creation failure
        state = {
            "user_id": "456",
            "flow_state": {
                ...
                "time_slot": "14:00-15:00",
                "booking_step": "confirming"
            },
            ...
        }
        result = await create_booking(state, tools)
        # result["response_content"] = "Unable to create booking: Time slot already booked"
        # result["next_node"] = "select_time"
    """
    chat_id = state["chat_id"]
    user_id = state.get("user_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Creating booking for chat {chat_id}, user {user_id}"
    )
    
    # Validate that all required booking information is present (Requirement 8.5)
    required_fields = {
        "court_id": "court",
        "date": "date",
        "time_slot": "time slot"
    }
    
    missing_fields = []
    for field, display_name in required_fields.items():
        if not flow_state.get(field):
            missing_fields.append(display_name)
    
    if missing_fields:
        logger.error(
            f"Missing required booking information for chat {chat_id}: {missing_fields}"
        )
        
        response = (
            f"Some booking information is missing ({', '.join(missing_fields)}). "
            f"Let's start over."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_property"
        
        # Reset flow_state (Requirement 15.5)
        state["flow_state"] = {}
        
        return state
    
    # Validate user_id is present
    if not user_id:
        logger.error(f"Missing user_id for booking creation in chat {chat_id}")
        
        response = (
            "I'm having trouble identifying your account. "
            "Please try again or contact support."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        # Clear flow_state (Requirement 15.5)
        state["flow_state"] = {}
        
        return state
    
    # Extract booking details
    court_id = flow_state.get("court_id")
    date_str = flow_state.get("date")
    time_slot = flow_state.get("time_slot")
    
    # Parse date (Requirement 8.5)
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(
            f"Invalid date format in flow_state for chat {chat_id}: {date_str}, error: {e}"
        )
        
        response = (
            "There was an error with the selected date. "
            "Please select a date again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_date"
        
        # Clear date and subsequent fields
        flow_state["date"] = None
        flow_state["time_slot"] = None
        flow_state["booking_step"] = "court_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Parse time_slot into start_time and end_time (Requirement 8.5)
    try:
        start_time_str, end_time_str = time_slot.split("-")
        
        # Parse to time objects
        start_time = datetime.strptime(start_time_str.strip(), "%H:%M").time()
        end_time = datetime.strptime(end_time_str.strip(), "%H:%M").time()
        
        logger.debug(
            f"Parsed time_slot for chat {chat_id}: "
            f"start={start_time}, end={end_time}"
        )
        
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
    
    # Validate time range (end_time must be after start_time)
    if end_time <= start_time:
        logger.error(
            f"Invalid time range for chat {chat_id}: "
            f"start={start_time}, end={end_time}"
        )
        
        response = (
            "The end time must be after the start time. "
            "Please select a valid time slot."
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
    
    # Call create_booking_tool
    try:
        logger.info(
            f"Calling create_booking_tool for chat {chat_id}: "
            f"customer_id={user_id}, court_id={court_id}, "
            f"date={booking_date}, time={start_time}-{end_time}"
        )
        
        result = await create_booking_tool(
            customer_id=int(user_id),
            court_id=int(court_id),
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            notes=None  # Could be added to flow_state if needed
        )
        
        if not result:
            # Unexpected error - result is None
            logger.error(
                f"create_booking_tool returned None for chat {chat_id}"
            )
            
            response = (
                "An unexpected error occurred while creating your booking. "
                "Please try again later."
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            state["next_node"] = "end"
            
            # Clear flow_state (Requirement 15.5)
            state["flow_state"] = {}
            
            return state
        
        # Check if booking was successful
        if result.get("success"):
            # Booking created successfully
            booking_data = result.get("data", {})
            booking_id = booking_data.get("id")
            total_price = booking_data.get("total_price", 0.0)
            
            logger.info(
                f"Booking created successfully for chat {chat_id}: "
                f"booking_id={booking_id}, total_price=${total_price}"
            )
            
            # Format confirmation message
            property_name = flow_state.get("property_name", "the property")
            court_name = flow_state.get("court_name", "the court")
            
            # Format date
            try:
                formatted_date = booking_date.strftime("%A, %B %d, %Y")
            except:
                formatted_date = date_str
            
            # Format times for display
            display_start = _format_time_for_display(start_time)
            display_end = _format_time_for_display(end_time)
            
            response = (
                f"🎉 Booking confirmed!\n\n"
                f"Booking ID: #{booking_id}\n"
                f"Property: {property_name}\n"
                f"Court: {court_name}\n"
                f"Date: {formatted_date}\n"
                f"Time: {display_start} - {display_end}\n"
                f"Total: ${total_price:.2f}\n\n"
                f"Your booking is pending confirmation. "
                f"You'll receive a notification once it's confirmed."
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {
                "booking_id": booking_id,
                "booking_data": booking_data
            }
            state["next_node"] = "end"
            
            # Clear flow_state (Requirement 15.5)
            state["flow_state"] = {}
            
            return state
        
        else:
            # Booking creation failed
            error_message = result.get("message", "Unknown error")
            
            logger.warning(
                f"Booking creation failed for chat {chat_id}: {error_message}"
            )
            
            # Determine if error is related to time slot availability
            time_related_errors = [
                "already booked",
                "not available",
                "blocked",
                "conflict"
            ]
            
            is_time_error = any(
                keyword in error_message.lower()
                for keyword in time_related_errors
            )
            
            if is_time_error:
                # Route back to time selection
                response = (
                    f"Unable to create booking: {error_message}\n\n"
                    f"Let's select a different time slot."
                )
                
                state["response_content"] = response
                state["response_type"] = "text"
                state["response_metadata"] = {}
                state["next_node"] = "select_time"
                
                # Clear time_slot to force re-selection
                flow_state["time_slot"] = None
                flow_state["booking_step"] = "date_selected"
                state["flow_state"] = flow_state
                
            else:
                # Generic error - end flow
                response = (
                    f"Unable to create booking: {error_message}\n\n"
                    f"Please try again later or contact support if the problem persists."
                )
                
                state["response_content"] = response
                state["response_type"] = "text"
                state["response_metadata"] = {}
                state["next_node"] = "end"
                
                # Clear flow_state (Requirement 15.5)
                state["flow_state"] = {}
            
            return state
        
    except Exception as e:
        logger.error(
            f"Exception during booking creation for chat {chat_id}: {e}",
            exc_info=True
        )
        
        response = (
            "An unexpected error occurred while creating your booking. "
            "Please try again later."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        # Clear flow_state (Requirement 15.5)
        state["flow_state"] = {}
        
        return state


def _format_time_for_display(time_obj: time) -> str:
    """
    Format time object for user-friendly display.
    
    Converts 24-hour format to 12-hour format with AM/PM.
    
    Args:
        time_obj: Time object
        
    Returns:
        Formatted time string (e.g., "2:00 PM")
    """
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
