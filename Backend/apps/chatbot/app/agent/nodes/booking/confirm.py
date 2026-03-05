"""
Confirm booking node for booking subgraph.

This module implements the confirm node that handles booking confirmation
in the booking flow using LangChain agent. It generates a comprehensive booking summary,
uses an LLM agent to parse user confirmation/cancellation/modification requests,
and updates flow_state accordingly.

Requirements: 6.3, 9.1, 9.2, 9.3, 22.1-22.6
"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.booking_prompts import create_confirm_booking_prompt
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


async def confirm_booking(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle booking confirmation in booking flow.
    
    This node manages the confirmation step of the booking process. It:
    1. Checks if all booking details are present in flow_state
    2. Generates a comprehensive booking summary with all details
    3. Asks for explicit user confirmation
    4. Parses user response (confirm, cancel, or modify)
    5. Updates flow_state step to "confirm" when presenting summary
    6. Updates flow_state step to "confirmed" when user confirms
    7. Clears booking fields from flow_state when user cancels
    8. Routes back to appropriate step when user requests modifications
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Confirm node
    - 22.1: Present booking summary with all details
    - 22.2: Include property name, court type, date, time, and price
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated flow_state with confirmation status
        
    Example:
        # First call - present summary
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "14:00",
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
                "step": "time_selected"
            },
            ...
        }
        
        result = await confirm_booking(state, tools)
        # result["response_content"] = "Here's your booking summary: ..."
        # result["flow_state"]["step"] = "confirm"
        
        # Second call - process confirmation
        state = {
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
                "step": "confirm"
            },
            ...
        }
        
        result = await confirm_booking(state, tools)
        # result["flow_state"]["step"] = "confirmed"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing booking confirmation for chat {chat_id} - "
        f"step={flow_state.get('step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if we're processing a confirmation response or presenting summary
    current_step = flow_state.get("step")
    
    if current_step == "confirm":
        # User is responding to confirmation prompt
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
            chat_id=chat_id,
            flow_state=flow_state
        )


async def _present_booking_summary(
    state: ConversationState,
    chat_id: str,
    flow_state: Dict[str, Any]
) -> ConversationState:
    """
    Present booking summary to the user for confirmation.
    
    This function generates a comprehensive booking summary with all details
    and asks for explicit user confirmation.
    
    Implements Requirements:
    - 22.1: Present booking summary with all details
    - 22.2: Include property name, court type, date, time, and price
    - 22.3: Ask for explicit user confirmation
    
    Args:
        state: ConversationState
        chat_id: Chat ID for logging
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with booking summary
    """
    # Validate all required booking details are present
    required_fields = [
        "property_id", "property_name",
        "service_id", "service_name", "sport_type",
        "date", "start_time", "end_time", "price"
    ]
    
    missing_fields = [field for field in required_fields if not flow_state.get(field)]
    
    if missing_fields:
        logger.error(
            f"Missing required booking fields for chat {chat_id}: {missing_fields}"
        )
        
        response = (
            "I'm missing some booking information. "
            "Let's start over. Which facility would you like to book?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Reset flow state
        flow_state["step"] = "select_property"
        # Clear booking fields
        for field in required_fields:
            flow_state.pop(field, None)
        state["flow_state"] = flow_state
        
        return state
    
    # Extract booking details
    property_name = flow_state.get("property_name")
    service_name = flow_state.get("service_name")
    sport_type = flow_state.get("sport_type")
    date_str = flow_state.get("date")
    start_time = flow_state.get("start_time")
    end_time = flow_state.get("end_time")
    price = flow_state.get("price")
    price_label = flow_state.get("price_label", "")
    
    # Format date for display
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        logger.warning(f"Invalid date format in flow_state: {date_str}")
        formatted_date = date_str
    
    # Format times for display
    display_start = _format_time_for_display(start_time)
    display_end = _format_time_for_display(end_time)
    
    # Calculate duration in hours
    try:
        start_obj = datetime.strptime(start_time, "%H:%M:%S").time()
        end_obj = datetime.strptime(end_time, "%H:%M:%S").time()
        
        # Calculate duration
        start_minutes = start_obj.hour * 60 + start_obj.minute
        end_minutes = end_obj.hour * 60 + end_obj.minute
        duration_minutes = end_minutes - start_minutes
        duration_hours = duration_minutes / 60
        
        # Calculate total price
        total_price = price * duration_hours
    except ValueError:
        logger.warning(f"Failed to calculate duration for times: {start_time} - {end_time}")
        duration_hours = 1.0
        total_price = price
    
    # Generate booking summary
    summary_lines = [
        "📋 **Booking Summary**",
        "",
        f"🏢 **Facility:** {property_name}",
        f"🎾 **Court:** {service_name} ({sport_type})",
        f"📅 **Date:** {formatted_date}",
        f"⏰ **Time:** {display_start} - {display_end}",
        f"💰 **Price:** ${price:.2f}/hour"
    ]
    
    if price_label:
        summary_lines.append(f"   ({price_label})")
    
    summary_lines.extend([
        f"⏱️ **Duration:** {duration_hours:.1f} hour(s)",
        f"💵 **Total:** ${total_price:.2f}",
        "",
        "Would you like to confirm this booking?",
        "",
        "Reply with:",
        "• 'yes' or 'confirm' to book",
        "• 'no' or 'cancel' to cancel",
        "• 'change' or 'modify' to make changes"
    ])
    
    response = "\n".join(summary_lines)
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    # Update flow state
    flow_state["step"] = "confirm"
    flow_state["total_price"] = total_price
    flow_state["duration_hours"] = duration_hours
    state["flow_state"] = flow_state
    
    logger.info(
        f"Presented booking summary for chat {chat_id}: "
        f"property={property_name}, service={service_name}, "
        f"date={date_str}, time={display_start}-{display_end}, "
        f"total=${total_price:.2f}"
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
    Process user's confirmation response using LangChain agent.
    
    This function uses a LangChain agent to intelligently parse the user's
    response to determine if they want to:
    - Confirm the booking (proceed to create booking)
    - Cancel the booking (clear flow_state)
    - Modify the booking (return to appropriate step)
    
    Implements Requirements:
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    
    Args:
        state: ConversationState
        chat_id: Chat ID for logging
        user_message: User's confirmation response
        flow_state: Current flow state
        
    Returns:
        Updated ConversationState with confirmation status
    """
    message_lower = user_message.lower().strip()
    
    # Try using LangChain agent for intelligent parsing
    try:
        llm = create_langchain_llm(llm_provider)
        prompt = create_confirm_booking_prompt(flow_state)
        
        messages = prompt.format_messages(input=user_message)
        response_obj = await llm.ainvoke(messages)
        agent_response = response_obj.content.strip().upper()
        
        logger.debug(f"Agent response for confirmation: {agent_response}")
        
        # Handle agent response
        if agent_response == "CONFIRM":
            # User confirmed the booking
            logger.info(f"User confirmed booking for chat {chat_id}")
            
            response = (
                "Great! I'm creating your booking now..."
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Update flow state to confirmed
            flow_state["step"] = "confirmed"
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CANCEL":
            # User cancelled the booking
            logger.info(f"User cancelled booking for chat {chat_id}")
            
            response = (
                "No problem! Your booking has been cancelled. "
                "Is there anything else I can help you with?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Clear all booking fields from flow_state
            booking_fields = [
                "property_id", "property_name",
                "service_id", "service_name", "sport_type",
                "date", "start_time", "end_time",
                "price", "price_label", "total_price", "duration_hours"
            ]
            
            for field in booking_fields:
                flow_state.pop(field, None)
            
            flow_state["step"] = "cancelled"
            flow_state["intent"] = None
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CHANGE_PROPERTY":
            # User wants to change property
            logger.info(f"User requested property change for chat {chat_id}")
            
            response = (
                "No problem! Let's select a different facility. "
                "Which facility would you like to book?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Clear property and subsequent selections
            flow_state.pop("property_id", None)
            flow_state.pop("property_name", None)
            flow_state.pop("service_id", None)
            flow_state.pop("service_name", None)
            flow_state.pop("sport_type", None)
            flow_state.pop("date", None)
            flow_state.pop("start_time", None)
            flow_state.pop("end_time", None)
            flow_state.pop("price", None)
            flow_state.pop("price_label", None)
            flow_state.pop("total_price", None)
            flow_state.pop("duration_hours", None)
            
            flow_state["step"] = "select_property"
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CHANGE_SERVICE":
            # User wants to change court
            logger.info(f"User requested court change for chat {chat_id}")
            
            response = (
                "No problem! Let's select a different court. "
                "Which court would you like to book?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Clear service and subsequent selections
            flow_state.pop("service_id", None)
            flow_state.pop("service_name", None)
            flow_state.pop("sport_type", None)
            flow_state.pop("date", None)
            flow_state.pop("start_time", None)
            flow_state.pop("end_time", None)
            flow_state.pop("price", None)
            flow_state.pop("price_label", None)
            flow_state.pop("total_price", None)
            flow_state.pop("duration_hours", None)
            
            flow_state["step"] = "property_selected"
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CHANGE_DATE":
            # User wants to change date
            logger.info(f"User requested date change for chat {chat_id}")
            
            response = (
                "No problem! Let's select a different date. "
                "When would you like to book?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Clear date and subsequent selections
            flow_state.pop("date", None)
            flow_state.pop("start_time", None)
            flow_state.pop("end_time", None)
            flow_state.pop("price", None)
            flow_state.pop("price_label", None)
            flow_state.pop("total_price", None)
            flow_state.pop("duration_hours", None)
            
            flow_state["step"] = "service_selected"
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CHANGE_TIME":
            # User wants to change time
            logger.info(f"User requested time change for chat {chat_id}")
            
            response = (
                "No problem! Let's select a different time slot. "
                "What time would you like to book?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Clear time and price
            flow_state.pop("start_time", None)
            flow_state.pop("end_time", None)
            flow_state.pop("price", None)
            flow_state.pop("price_label", None)
            flow_state.pop("total_price", None)
            flow_state.pop("duration_hours", None)
            
            flow_state["step"] = "date_selected"
            state["flow_state"] = flow_state
            
            return state
            
        elif agent_response == "CLARIFY":
            # Agent is asking for clarification - response should be conversational
            # Use the agent's actual response (before we uppercased it)
            messages = prompt.format_messages(input=user_message)
            response_obj = await llm.ainvoke(messages)
            agent_clarification = response_obj.content.strip()
            
            state["response_content"] = agent_clarification
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            logger.info(f"Agent asking for clarification in chat {chat_id}")
            
            return state
            
    except Exception as e:
        logger.error(f"Error using LangChain agent for confirmation in chat {chat_id}: {e}", exc_info=True)
        # Fall through to manual parsing below
    
    # Fallback to manual parsing
    # Detect confirmation intent
    confirmation_keywords = [
        "yes", "confirm", "book", "proceed", "ok", "okay",
        "sure", "correct", "right", "yep", "yeah", "yup"
    ]
    
    cancellation_keywords = [
        "no", "cancel", "nevermind", "never mind", "nope",
        "nah", "stop", "abort", "quit"
    ]
    
    modification_keywords = [
        "change", "modify", "edit", "update", "different",
        "back", "return", "redo"
    ]
    
    # Check for specific modification requests
    if any(keyword in message_lower for keyword in ["property", "facility", "location"]):
        # User wants to change property
        logger.info(f"User requested property change for chat {chat_id}")
        
        response = (
            "No problem! Let's select a different facility. "
            "Which facility would you like to book?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Clear property and subsequent selections
        flow_state.pop("property_id", None)
        flow_state.pop("property_name", None)
        flow_state.pop("service_id", None)
        flow_state.pop("service_name", None)
        flow_state.pop("sport_type", None)
        flow_state.pop("date", None)
        flow_state.pop("start_time", None)
        flow_state.pop("end_time", None)
        flow_state.pop("price", None)
        flow_state.pop("price_label", None)
        flow_state.pop("total_price", None)
        flow_state.pop("duration_hours", None)
        
        flow_state["step"] = "select_property"
        state["flow_state"] = flow_state
        
        return state
    
    elif any(keyword in message_lower for keyword in ["court", "service"]):
        # User wants to change court
        logger.info(f"User requested court change for chat {chat_id}")
        
        response = (
            "No problem! Let's select a different court. "
            "Which court would you like to book?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Clear service and subsequent selections
        flow_state.pop("service_id", None)
        flow_state.pop("service_name", None)
        flow_state.pop("sport_type", None)
        flow_state.pop("date", None)
        flow_state.pop("start_time", None)
        flow_state.pop("end_time", None)
        flow_state.pop("price", None)
        flow_state.pop("price_label", None)
        flow_state.pop("total_price", None)
        flow_state.pop("duration_hours", None)
        
        flow_state["step"] = "property_selected"
        state["flow_state"] = flow_state
        
        return state
    
    elif any(keyword in message_lower for keyword in ["date", "day"]):
        # User wants to change date
        logger.info(f"User requested date change for chat {chat_id}")
        
        response = (
            "No problem! Let's select a different date. "
            "When would you like to book?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Clear date and subsequent selections
        flow_state.pop("date", None)
        flow_state.pop("start_time", None)
        flow_state.pop("end_time", None)
        flow_state.pop("price", None)
        flow_state.pop("price_label", None)
        flow_state.pop("total_price", None)
        flow_state.pop("duration_hours", None)
        
        flow_state["step"] = "service_selected"
        state["flow_state"] = flow_state
        
        return state
    
    elif any(keyword in message_lower for keyword in ["time", "slot"]):
        # User wants to change time
        logger.info(f"User requested time change for chat {chat_id}")
        
        response = (
            "No problem! Let's select a different time slot. "
            "What time would you like to book?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Clear time and price
        flow_state.pop("start_time", None)
        flow_state.pop("end_time", None)
        flow_state.pop("price", None)
        flow_state.pop("price_label", None)
        flow_state.pop("total_price", None)
        flow_state.pop("duration_hours", None)
        
        flow_state["step"] = "date_selected"
        state["flow_state"] = flow_state
        
        return state
    
    # Check for general confirmation
    if any(keyword in message_lower for keyword in confirmation_keywords):
        # User confirmed the booking
        logger.info(f"User confirmed booking for chat {chat_id}")
        
        response = (
            "Great! I'm creating your booking now..."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Update flow state to confirmed
        flow_state["step"] = "confirmed"
        state["flow_state"] = flow_state
        
        return state
    
    # Check for cancellation
    elif any(keyword in message_lower for keyword in cancellation_keywords):
        # User cancelled the booking
        logger.info(f"User cancelled booking for chat {chat_id}")
        
        response = (
            "No problem! Your booking has been cancelled. "
            "Is there anything else I can help you with?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Clear all booking fields from flow_state
        booking_fields = [
            "property_id", "property_name",
            "service_id", "service_name", "sport_type",
            "date", "start_time", "end_time",
            "price", "price_label", "total_price", "duration_hours"
        ]
        
        for field in booking_fields:
            flow_state.pop(field, None)
        
        flow_state["step"] = "cancelled"
        flow_state["intent"] = None
        state["flow_state"] = flow_state
        
        return state
    
    # Check for general modification request
    elif any(keyword in message_lower for keyword in modification_keywords):
        # User wants to modify but didn't specify what
        logger.info(f"User requested modification for chat {chat_id}")
        
        response = (
            "What would you like to change?\n"
            "• Property/Facility\n"
            "• Court\n"
            "• Date\n"
            "• Time"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as confirm to allow user to specify what to change
        return state
    
    # Unclear response
    else:
        logger.warning(
            f"Unclear confirmation response for chat {chat_id}: {user_message}"
        )
        
        response = (
            "I'm not sure what you'd like to do. "
            "Please reply with:\n"
            "• 'yes' or 'confirm' to book\n"
            "• 'no' or 'cancel' to cancel\n"
            "• 'change' or 'modify' to make changes"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Keep step as confirm to allow retry
        return state


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
