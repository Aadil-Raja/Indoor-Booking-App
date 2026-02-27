"""
Create pending booking node for booking subgraph.

This module implements the create_booking node that handles the final step
of creating a booking with pending status. It calls the booking tool to create
the booking, stores the booking_id in flow_state on success, handles errors
gracefully, clears booking fields from flow_state on completion, and generates
a confirmation message with booking details.

Requirements: 6.3, 8.1-8.6, 20.8, 22.1-22.6
"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime, time, date

from ...state.conversation_state import ConversationState
from ...tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def create_pending_booking(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Create a pending booking and generate confirmation message.
    
    This node manages the final step of the booking process. It:
    1. Retrieves all booking details from flow_state (user_id, service_id, date, start_time, end_time)
    2. Validates that all required fields are present
    3. Calls the create_booking_tool to create a booking with pending status
    4. Stores booking_id in flow_state on success
    5. Handles booking creation errors gracefully with retry information
    6. Clears booking-related fields from flow_state on completion
    7. Generates a confirmation message with booking details and booking_id
    8. Updates flow_state step to "booking_created"
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Create_Pending_Booking node
    - 8.1: Call booking_service.create_booking() when booking is confirmed
    - 8.2: Create booking with pending status
    - 8.3: Store booking_id in flow_state when booking is created successfully
    - 8.4: Inform user and retain booking details in flow_state for retry when booking creation fails
    - 8.5: Clear booking-specific fields from flow_state when booking is completed
    - 8.6: Preserve bot_memory for conversation context after booking completion
    - 20.8: Clear booking-related fields from Flow_State when booking is completed or cancelled
    - 22.1: Present booking summary with all details
    - 22.2: Include property name, court type, date, time, and price in summary
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    
    Args:
        state: ConversationState containing user_id, flow_state with booking details
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated flow_state with booking_id and cleared booking fields
        
    Example:
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "223e4567-e89b-12d3-a456-426614174000",
            "user_message": "yes, confirm",
            "flow_state": {
                "intent": "booking",
                "property_id": "1",
                "property_name": "Downtown Sports Center",
                "service_id": "10",
                "service_name": "Tennis Court A",
                "sport_type": "tennis",
                "date": "2024-12-25",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price": 50.0,
                "total_price": 50.0,
                "duration_hours": 1.0,
                "step": "confirmed"
            },
            ...
        }
        
        result = await create_pending_booking(state, tools)
        # result["flow_state"]["booking_id"] = 123
        # result["flow_state"]["step"] = "booking_created"
        # result["response_content"] contains confirmation with booking details
        # Booking fields cleared from flow_state
    """
    chat_id = state["chat_id"]
    user_id = state["user_id"]
    flow_state = state.get("flow_state", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Creating pending booking for chat {chat_id} - "
        f"step={flow_state.get('step')}"
    )
    
    # Validate required fields
    required_fields = ["service_id", "date", "start_time", "end_time"]
    missing_fields = [field for field in required_fields if not flow_state.get(field)]
    
    if missing_fields:
        logger.error(
            f"Missing required booking fields for chat {chat_id}: {missing_fields}"
        )
        
        response = (
            "I'm sorry, but some booking information is missing. "
            "Let's start the booking process again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Reset flow state to start booking process again
        flow_state["step"] = "select_property"
        _clear_booking_fields(flow_state)
        state["flow_state"] = flow_state
        
        return state
    
    # Extract booking details from flow_state
    service_id = flow_state.get("service_id")
    date_str = flow_state.get("date")
    start_time_str = flow_state.get("start_time")
    end_time_str = flow_state.get("end_time")
    
    # Parse date and time
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        booking_start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
        booking_end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
    except ValueError as e:
        logger.error(
            f"Invalid date/time format for chat {chat_id}: {e}"
        )
        
        response = (
            "There was an error with the booking date or time. "
            "Let's try selecting the date and time again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Reset to date selection
        flow_state["step"] = "service_selected"
        flow_state.pop("date", None)
        flow_state.pop("start_time", None)
        flow_state.pop("end_time", None)
        flow_state.pop("price", None)
        state["flow_state"] = flow_state
        
        return state
    
    # Convert user_id to int (it's stored as string in state)
    try:
        customer_id = int(user_id)
    except (ValueError, TypeError):
        logger.error(
            f"Invalid user_id format for chat {chat_id}: {user_id}"
        )
        
        response = (
            "There was an error with your user account. "
            "Please try again or contact support."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Convert service_id to int
    try:
        court_id = int(service_id)
    except (ValueError, TypeError):
        logger.error(
            f"Invalid service_id format for chat {chat_id}: {service_id}"
        )
        
        response = (
            "There was an error with the selected court. "
            "Let's try selecting a court again."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Reset to service selection
        flow_state["step"] = "property_selected"
        flow_state.pop("service_id", None)
        flow_state.pop("service_name", None)
        state["flow_state"] = flow_state
        
        return state
    
    # Call create_booking tool
    create_booking = tools.get("create_booking")
    if not create_booking:
        logger.error("create_booking tool not found in registry")
        
        response = (
            "I'm sorry, but there was a system error. "
            "Please try again later or contact support."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    logger.info(
        f"Calling create_booking tool for chat {chat_id}: "
        f"customer_id={customer_id}, court_id={court_id}, "
        f"date={booking_date}, time={booking_start_time}-{booking_end_time}"
    )
    
    try:
        result = await create_booking(
            customer_id=customer_id,
            court_id=court_id,
            booking_date=booking_date,
            start_time=booking_start_time,
            end_time=booking_end_time,
            notes=None  # Could be added to flow_state in future
        )
        
        if result and result.get("success"):
            # Booking created successfully
            booking_data = result.get("data", {})
            booking_id = booking_data.get("id")
            total_price = booking_data.get("total_price", flow_state.get("total_price", 0.0))
            
            logger.info(
                f"Booking created successfully for chat {chat_id}: "
                f"booking_id={booking_id}, total_price=${total_price}"
            )
            
            # Store booking_id in flow_state
            flow_state["booking_id"] = booking_id
            
            # Generate confirmation message
            response = _generate_confirmation_message(
                flow_state=flow_state,
                booking_id=booking_id,
                total_price=total_price
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Update flow state step
            flow_state["step"] = "booking_created"
            
            # Clear booking-related fields from flow_state
            _clear_booking_fields(flow_state)
            
            state["flow_state"] = flow_state
            
            logger.info(
                f"Booking process completed for chat {chat_id}, "
                f"booking fields cleared from flow_state"
            )
            
        else:
            # Booking creation failed
            error_message = result.get("message", "Unknown error") if result else "No response from booking service"
            
            logger.warning(
                f"Booking creation failed for chat {chat_id}: {error_message}"
            )
            
            # Generate error message with retry information
            response = _generate_error_message(
                flow_state=flow_state,
                error_message=error_message
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Keep booking details in flow_state for retry
            flow_state["step"] = "booking_failed"
            flow_state["error_message"] = error_message
            state["flow_state"] = flow_state
            
    except Exception as e:
        logger.error(
            f"Exception during booking creation for chat {chat_id}: {e}",
            exc_info=True
        )
        
        response = (
            "I'm sorry, but there was an unexpected error while creating your booking. "
            "Your booking details have been saved. Would you like to try again?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep booking details in flow_state for retry
        flow_state["step"] = "booking_failed"
        flow_state["error_message"] = str(e)
        state["flow_state"] = flow_state
    
    return state


def _clear_booking_fields(flow_state: Dict[str, Any]) -> None:
    """
    Clear booking-related fields from flow_state.
    
    This function removes all booking-specific fields from flow_state
    after successful booking creation, while preserving intent and step.
    
    Implements Requirement 8.5: Clear booking-specific fields from flow_state
    when booking is completed
    
    Args:
        flow_state: Flow state dictionary to clear
    """
    # Fields to clear after booking completion
    fields_to_clear = [
        "property_id",
        "property_name",
        "service_id",
        "service_name",
        "sport_type",
        "date",
        "start_time",
        "end_time",
        "price",
        "price_label",
        "total_price",
        "duration_hours",
        "error_message"
    ]
    
    for field in fields_to_clear:
        flow_state.pop(field, None)
    
    logger.debug(f"Cleared {len(fields_to_clear)} booking fields from flow_state")


def _generate_confirmation_message(
    flow_state: Dict[str, Any],
    booking_id: int,
    total_price: float
) -> str:
    """
    Generate confirmation message with booking details.
    
    This function creates a user-friendly confirmation message that includes
    all booking details and the booking_id for reference.
    
    Implements Requirements:
    - 22.1: Present booking summary with all details
    - 22.2: Include property name, court type, date, time, and price in summary
    
    Args:
        flow_state: Flow state containing booking details
        booking_id: ID of the created booking
        total_price: Total price of the booking
        
    Returns:
        Confirmation message string
    """
    property_name = flow_state.get("property_name", "the facility")
    service_name = flow_state.get("service_name", "the court")
    sport_type = flow_state.get("sport_type", "")
    date_str = flow_state.get("date", "")
    start_time_str = flow_state.get("start_time", "")
    end_time_str = flow_state.get("end_time", "")
    duration_hours = flow_state.get("duration_hours", 1.0)
    
    # Format date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        formatted_date = date_str
    
    # Format times
    display_start = _format_time_for_display(start_time_str)
    display_end = _format_time_for_display(end_time_str)
    
    # Build confirmation message
    message_parts = [
        "🎉 Booking Confirmed!",
        "",
        f"Your booking has been successfully created with ID: {booking_id}",
        "",
        "Booking Details:",
        f"📍 Location: {property_name}",
        f"🏟️ Court: {service_name}"
    ]
    
    if sport_type:
        message_parts.append(f"⚽ Sport: {sport_type.capitalize()}")
    
    message_parts.extend([
        f"📅 Date: {formatted_date}",
        f"⏰ Time: {display_start} - {display_end}",
        f"⏱️ Duration: {duration_hours} hour{'s' if duration_hours != 1 else ''}",
        f"💰 Total Price: ${total_price:.2f}",
        "",
        "Your booking is currently pending. You will receive a confirmation once payment is processed.",
        "",
        "Thank you for booking with us! Is there anything else I can help you with?"
    ])
    
    return "\n".join(message_parts)


def _generate_error_message(
    flow_state: Dict[str, Any],
    error_message: str
) -> str:
    """
    Generate error message with retry information.
    
    This function creates a user-friendly error message that explains
    what went wrong and offers options to retry or modify the booking.
    
    Implements Requirement 8.4: Inform user and retain booking details
    in flow_state for retry when booking creation fails
    
    Args:
        flow_state: Flow state containing booking details
        error_message: Error message from booking service
        
    Returns:
        Error message string
    """
    property_name = flow_state.get("property_name", "the facility")
    service_name = flow_state.get("service_name", "the court")
    date_str = flow_state.get("date", "")
    start_time_str = flow_state.get("start_time", "")
    end_time_str = flow_state.get("end_time", "")
    
    # Format date and times
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        formatted_date = date_str
    
    display_start = _format_time_for_display(start_time_str)
    display_end = _format_time_for_display(end_time_str)
    
    # Build error message
    message_parts = [
        "❌ Booking Failed",
        "",
        f"I'm sorry, but I couldn't create your booking: {error_message}",
        "",
        "Your booking details:",
        f"📍 {property_name}",
        f"🏟️ {service_name}",
        f"📅 {formatted_date}",
        f"⏰ {display_start} - {display_end}",
        "",
        "Would you like to:",
        "• Try booking again",
        "• Select a different time slot",
        "• Start a new booking",
        "",
        "Just let me know what you'd like to do!"
    ]
    
    return "\n".join(message_parts)


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
