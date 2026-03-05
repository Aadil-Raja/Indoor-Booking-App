"""
Booking node prompts for LangChain agent-based booking flow.

This module defines prompt templates used by booking nodes to handle
the multi-step booking process including property selection, service selection,
date selection, time selection, and confirmation.

Requirements: 9.1, 9.2
"""

from typing import Dict, Any, List
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


# =============================================================================
# SELECT PROPERTY PROMPT
# =============================================================================

SELECT_PROPERTY_SYSTEM_TEMPLATE = """You are a helpful booking assistant helping a user select a sports facility.

Your task is to help the user choose a property from the available options.

Available Properties:
{properties_list}

Guidelines:
- Present the available properties in a clear, organized way
- Help the user understand their options
- Extract the user's selection from their message
- The user might select by:
  * Property name (e.g., "Downtown Sports Center")
  * Property number/position (e.g., "the first one", "number 2")
  * Property ID (e.g., "property 6")
- Be conversational and helpful
- If the selection is unclear, ask for clarification
- Once you identify the selected property, respond with ONLY the property ID as a number

Important:
- Your final response should be ONLY the property ID number when a valid selection is made
- If asking for clarification, provide a conversational response
- Do not make assumptions about which property the user wants
"""


def create_select_property_prompt(
    properties: List[Dict[str, Any]]
) -> ChatPromptTemplate:
    """
    Create a prompt for property selection assistant.
    
    Args:
        properties: List of available property dictionaries
        
    Returns:
        ChatPromptTemplate for property selection
    """
    # Format properties list
    properties_lines = []
    for i, prop in enumerate(properties, 1):
        prop_id = prop.get("id")
        name = prop.get("name", "Unknown Property")
        city = prop.get("city", "")
        address = prop.get("address", "")
        
        line = f"{i}. {name} (ID: {prop_id})"
        if city:
            line += f" - {city}"
        if address:
            line += f", {address}"
        
        properties_lines.append(line)
    
    properties_list = "\n".join(properties_lines) if properties_lines else "No properties available"
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", SELECT_PROPERTY_SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    return prompt.partial(properties_list=properties_list)


# =============================================================================
# SELECT SERVICE PROMPT
# =============================================================================

SELECT_SERVICE_SYSTEM_TEMPLATE = """You are a helpful booking assistant helping a user select a court/service.

Property: {property_name}

Available Courts:
{courts_list}

Guidelines:
- Present the available courts in a clear, organized way
- Help the user understand their options including sport type
- Extract the user's selection from their message
- The user might select by:
  * Court name (e.g., "Tennis Court A")
  * Court number/position (e.g., "the first one", "number 2")
  * Sport type (e.g., "tennis") - only if there's one court of that type
  * Court ID (e.g., "court 23")
- Be conversational and helpful
- If the selection is unclear, ask for clarification
- Once you identify the selected court, respond with ONLY the court ID as a number

Important:
- Your final response should be ONLY the court ID number when a valid selection is made
- If asking for clarification, provide a conversational response
- Do not make assumptions about which court the user wants
"""


def create_select_service_prompt(
    property_name: str,
    courts: List[Dict[str, Any]]
) -> ChatPromptTemplate:
    """
    Create a prompt for service/court selection assistant.
    
    Args:
        property_name: Name of the selected property
        courts: List of available court dictionaries
        
    Returns:
        ChatPromptTemplate for service selection
    """
    # Format courts list
    courts_lines = []
    for i, court in enumerate(courts, 1):
        court_id = court.get("id")
        name = court.get("name", "Unknown Court")
        sport_type = court.get("sport_type", "Unknown")
        
        line = f"{i}. {name} (ID: {court_id}) - Sport: {sport_type}"
        courts_lines.append(line)
    
    courts_list = "\n".join(courts_lines) if courts_lines else "No courts available"
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", SELECT_SERVICE_SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    return prompt.partial(
        property_name=property_name,
        courts_list=courts_list
    )


# =============================================================================
# SELECT DATE PROMPT
# =============================================================================

SELECT_DATE_SYSTEM_TEMPLATE = """You are a helpful booking assistant helping a user select a date for their booking.

Service: {service_name} at {property_name}

Guidelines:
- Help the user select a valid date for their booking
- Parse dates from various formats:
  * Relative: "today", "tomorrow", "next Monday"
  * ISO format: "2026-03-10"
  * Natural: "March 10", "March 10th"
  * Numeric: "3/10", "03/10/2026"
- Validate that the date is today or in the future (not in the past)
- Current date: {current_date}
- Be conversational and helpful
- If the date is unclear or invalid, ask for clarification
- Once you identify a valid date, respond with ONLY the date in ISO format (YYYY-MM-DD)

Important:
- Your final response should be ONLY the date in ISO format (YYYY-MM-DD) when a valid date is identified
- If asking for clarification or the date is invalid, provide a conversational response
- Do not accept dates in the past
- If user says "today", use {current_date}
"""


def create_select_date_prompt(
    property_name: str,
    service_name: str,
    current_date: str
) -> ChatPromptTemplate:
    """
    Create a prompt for date selection assistant.
    
    Args:
        property_name: Name of the selected property
        service_name: Name of the selected service/court
        current_date: Current date in ISO format (YYYY-MM-DD)
        
    Returns:
        ChatPromptTemplate for date selection
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SELECT_DATE_SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    return prompt.partial(
        property_name=property_name,
        service_name=service_name,
        current_date=current_date
    )


# =============================================================================
# SELECT TIME PROMPT
# =============================================================================

SELECT_TIME_SYSTEM_TEMPLATE = """You are a helpful booking assistant helping a user select a time slot for their booking.

Service: {service_name} at {property_name}
Date: {date}

Available Time Slots:
{slots_list}

Guidelines:
- Present the available time slots with pricing in a clear way
- Help the user understand their options
- Extract the user's selection from their message
- The user might select by:
  * Time (e.g., "2pm", "14:00", "2:00 PM")
  * Time range (e.g., "2pm to 3pm", "14:00-15:00")
  * Slot number/position (e.g., "the first one", "number 2")
  * Slot ID
- Be conversational and helpful
- If the selection is unclear, ask for clarification
- Once you identify the selected slot, respond with ONLY the slot's start time in HH:MM:SS format

Important:
- Your final response should be ONLY the start time in HH:MM:SS format when a valid selection is made
- If asking for clarification, provide a conversational response
- Do not make assumptions about which time slot the user wants
"""


def create_select_time_prompt(
    property_name: str,
    service_name: str,
    date: str,
    slots: List[Dict[str, Any]]
) -> ChatPromptTemplate:
    """
    Create a prompt for time slot selection assistant.
    
    Args:
        property_name: Name of the selected property
        service_name: Name of the selected service/court
        date: Selected date string
        slots: List of available time slot dictionaries
        
    Returns:
        ChatPromptTemplate for time selection
    """
    # Format slots list
    slots_lines = []
    for i, slot in enumerate(slots, 1):
        start_time = slot.get("start_time", "")
        end_time = slot.get("end_time", "")
        price = slot.get("price_per_hour", 0.0)
        label = slot.get("label", "")
        
        line = f"{i}. {start_time} - {end_time} (${price:.2f}/hour"
        if label:
            line += f" - {label}"
        line += ")"
        
        slots_lines.append(line)
    
    slots_list = "\n".join(slots_lines) if slots_lines else "No slots available"
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", SELECT_TIME_SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    return prompt.partial(
        property_name=property_name,
        service_name=service_name,
        date=date,
        slots_list=slots_list
    )


# =============================================================================
# CONFIRM BOOKING PROMPT
# =============================================================================

CONFIRM_BOOKING_SYSTEM_TEMPLATE = """You are a helpful booking assistant helping a user confirm their booking.

Booking Summary:
{booking_summary}

Guidelines:
- Present the booking summary clearly
- Ask for explicit confirmation
- Parse the user's response to determine their intent:
  * Confirmation: "yes", "confirm", "book it", "proceed", "ok"
  * Cancellation: "no", "cancel", "nevermind"
  * Modification: "change", "modify", "edit", "back"
- If user wants to modify, identify what they want to change:
  * Property/facility
  * Court/service
  * Date
  * Time
- Be conversational and helpful
- If the intent is unclear, ask for clarification
- Respond with ONE of these exact words based on user intent:
  * "CONFIRM" - user wants to proceed with booking
  * "CANCEL" - user wants to cancel
  * "CHANGE_PROPERTY" - user wants to change property
  * "CHANGE_SERVICE" - user wants to change court
  * "CHANGE_DATE" - user wants to change date
  * "CHANGE_TIME" - user wants to change time
  * "CLARIFY" - need clarification (provide conversational response)

Important:
- Your response should be ONE of the exact words above when intent is clear
- Only use "CLARIFY" if you need to ask the user a question
- Do not make assumptions about what the user wants to do
"""


def create_confirm_booking_prompt(
    flow_state: Dict[str, Any]
) -> ChatPromptTemplate:
    """
    Create a prompt for booking confirmation assistant.
    
    Args:
        flow_state: Dictionary containing all booking details
        
    Returns:
        ChatPromptTemplate for booking confirmation
    """
    # Build booking summary
    from datetime import datetime
    
    property_name = flow_state.get("property_name", "Unknown Property")
    service_name = flow_state.get("service_name", "Unknown Court")
    sport_type = flow_state.get("sport_type", "")
    date_str = flow_state.get("date", "")
    start_time = flow_state.get("start_time", "")
    end_time = flow_state.get("end_time", "")
    price = flow_state.get("price", 0.0)
    total_price = flow_state.get("total_price", 0.0)
    duration_hours = flow_state.get("duration_hours", 1.0)
    
    # Format date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        formatted_date = date_str
    
    summary_lines = [
        f"Property: {property_name}",
        f"Court: {service_name}",
    ]
    
    if sport_type:
        summary_lines.append(f"Sport: {sport_type}")
    
    summary_lines.extend([
        f"Date: {formatted_date}",
        f"Time: {start_time} - {end_time}",
        f"Duration: {duration_hours} hour(s)",
        f"Price: ${price:.2f}/hour",
        f"Total: ${total_price:.2f}"
    ])
    
    booking_summary = "\n".join(summary_lines)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", CONFIRM_BOOKING_SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])
    
    return prompt.partial(booking_summary=booking_summary)
