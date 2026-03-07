"""
Validation utilities for booking data.

This module provides validation functions for dates, time slots, and booking data
with comprehensive error handling. It integrates with the error_handlers module
to provide user-friendly error messages.

Requirements: 20.4
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, date, time

logger = logging.getLogger(__name__)


def validate_date_format(
    date_string: str,
    context: Dict[str, Any]
) -> Tuple[bool, Optional[date], Optional[str]]:
    """
    Validate and parse date string.
    
    Accepts ISO format (YYYY-MM-DD) and attempts to parse the date.
    Returns validation result, parsed date, and error message if invalid.
    
    Args:
        date_string: Date string to validate
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (is_valid, parsed_date, error_message)
        
    Example:
        is_valid, date_obj, error = validate_date_format("2026-03-10", {"chat_id": "123"})
        if not is_valid:
            return error_message
            
    Requirement: 20.4
    """
    from app.agent.state.error_handlers import handle_invalid_date_format
    
    if not date_string or not isinstance(date_string, str):
        error_message, _ = handle_invalid_date_format(
            str(date_string),
            context
        )
        return (False, None, error_message)
    
    try:
        # Try parsing ISO format (YYYY-MM-DD)
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d").date()
        
        # Validate it's not in the past
        if parsed_date < date.today():
            logger.warning(
                f"Date is in the past: {date_string}",
                extra={"chat_id": context.get("chat_id")}
            )
            return (
                False,
                None,
                f"The date {date_string} is in the past. Please choose a future date."
            )
        
        logger.debug(f"Valid date: {date_string}")
        return (True, parsed_date, None)
        
    except ValueError as e:
        logger.warning(
            f"Invalid date format: {date_string}, error: {e}",
            extra={"chat_id": context.get("chat_id")}
        )
        error_message, _ = handle_invalid_date_format(date_string, context)
        return (False, None, error_message)


def validate_time_slot_format(
    time_slot_string: str,
    context: Dict[str, Any]
) -> Tuple[bool, Optional[Tuple[time, time]], Optional[str]]:
    """
    Validate and parse time slot string.
    
    Accepts format HH:MM-HH:MM (e.g., "10:00-11:00").
    Returns validation result, parsed (start_time, end_time), and error message if invalid.
    
    Args:
        time_slot_string: Time slot string to validate
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (is_valid, (start_time, end_time), error_message)
        
    Example:
        is_valid, times, error = validate_time_slot_format("10:00-11:00", {"chat_id": "123"})
        if not is_valid:
            return error_message
        start_time, end_time = times
        
    Requirement: 20.4
    """
    from app.agent.state.error_handlers import handle_invalid_time_slot_format
    
    if not time_slot_string or not isinstance(time_slot_string, str):
        error_message, _ = handle_invalid_time_slot_format(
            str(time_slot_string),
            context
        )
        return (False, None, error_message)
    
    try:
        # Split on hyphen
        if '-' not in time_slot_string:
            raise ValueError("Time slot must contain '-' separator")
        
        parts = time_slot_string.split('-')
        if len(parts) != 2:
            raise ValueError("Time slot must have exactly two times")
        
        start_str, end_str = parts[0].strip(), parts[1].strip()
        
        # Parse start and end times
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        # Validate end time is after start time
        if end_time <= start_time:
            logger.warning(
                f"End time must be after start time: {time_slot_string}",
                extra={"chat_id": context.get("chat_id")}
            )
            return (
                False,
                None,
                f"The end time must be after the start time in '{time_slot_string}'."
            )
        
        logger.debug(f"Valid time slot: {time_slot_string}")
        return (True, (start_time, end_time), None)
        
    except ValueError as e:
        logger.warning(
            f"Invalid time slot format: {time_slot_string}, error: {e}",
            extra={"chat_id": context.get("chat_id")}
        )
        error_message, _ = handle_invalid_time_slot_format(time_slot_string, context)
        return (False, None, error_message)


def validate_booking_data(
    flow_state: Dict[str, Any],
    context: Dict[str, Any]
) -> Tuple[bool, Optional[List[str]], Optional[str]]:
    """
    Validate that all required booking data is present.
    
    Checks that flow_state contains all required fields for creating a booking:
    - property_id
    - court_id
    - date
    - time_slot
    
    Args:
        flow_state: Flow state dictionary to validate
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (is_valid, missing_fields, error_message)
        
    Example:
        is_valid, missing, error = validate_booking_data(flow_state, {"chat_id": "123"})
        if not is_valid:
            return error_message
            
    Requirement: 20.4
    """
    from app.agent.state.error_handlers import handle_missing_required_booking_data
    
    required_fields = ["property_id", "court_id", "date", "time_slot"]
    missing_fields = []
    
    for field in required_fields:
        value = flow_state.get(field)
        if value is None or value == "":
            missing_fields.append(field)
    
    if missing_fields:
        logger.error(
            f"Missing required booking data: {missing_fields}",
            extra={"chat_id": context.get("chat_id")}
        )
        error_message, _, _ = handle_missing_required_booking_data(
            missing_fields,
            context
        )
        return (False, missing_fields, error_message)
    
    logger.debug("All required booking data present")
    return (True, None, None)


def validate_booking_data_consistency(
    flow_state: Dict[str, Any],
    context: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate that booking data is internally consistent.
    
    Checks for conflicts such as:
    - Court doesn't belong to selected property
    - Date is in the past
    - Time slot is invalid
    
    Args:
        flow_state: Flow state dictionary to validate
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (is_valid, conflicts, error_message)
        
    Example:
        is_valid, conflicts, error = validate_booking_data_consistency(
            flow_state,
            {"chat_id": "123"}
        )
        if not is_valid:
            return error_message
            
    Requirement: 20.4
    """
    from app.agent.state.error_handlers import handle_conflicting_booking_data
    
    conflicts = {}
    
    # Validate date is not in the past
    date_str = flow_state.get("date")
    if date_str:
        try:
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if booking_date < date.today():
                conflicts["date"] = "Date is in the past"
        except ValueError:
            conflicts["date"] = "Invalid date format"
    
    # Validate time slot format
    time_slot = flow_state.get("time_slot")
    if time_slot:
        is_valid, _, _ = validate_time_slot_format(time_slot, context)
        if not is_valid:
            conflicts["time_slot"] = "Invalid time slot format"
    
    # Check for property_id without property_name (or vice versa)
    property_id = flow_state.get("property_id")
    property_name = flow_state.get("property_name")
    if (property_id and not property_name) or (property_name and not property_id):
        conflicts["property"] = "Property ID and name mismatch"
    
    # Check for court_id without court_name (or vice versa)
    court_id = flow_state.get("court_id")
    court_name = flow_state.get("court_name")
    if (court_id and not court_name) or (court_name and not court_id):
        conflicts["court"] = "Court ID and name mismatch"
    
    if conflicts:
        logger.error(
            f"Booking data conflicts detected: {conflicts}",
            extra={"chat_id": context.get("chat_id")}
        )
        error_message, _, _ = handle_conflicting_booking_data(conflicts, context)
        return (False, conflicts, error_message)
    
    logger.debug("Booking data is consistent")
    return (True, None, None)


def parse_time_slot(time_slot: str) -> Tuple[Optional[time], Optional[time]]:
    """
    Parse time slot string into start and end time objects.
    
    This is a utility function for converting validated time slot strings
    into time objects for database operations.
    
    Args:
        time_slot: Time slot string in format HH:MM-HH:MM
        
    Returns:
        Tuple of (start_time, end_time) or (None, None) if parsing fails
        
    Example:
        start_time, end_time = parse_time_slot("10:00-11:00")
        
    Requirement: 20.4
    """
    try:
        if '-' not in time_slot:
            return (None, None)
        
        parts = time_slot.split('-')
        if len(parts) != 2:
            return (None, None)
        
        start_str, end_str = parts[0].strip(), parts[1].strip()
        
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        return (start_time, end_time)
        
    except Exception as e:
        logger.error(f"Error parsing time slot '{time_slot}': {e}")
        return (None, None)


def format_date_for_display(date_obj: date) -> str:
    """
    Format date object for user-friendly display.
    
    Args:
        date_obj: Date object to format
        
    Returns:
        Formatted date string (e.g., "Monday, March 10, 2026")
        
    Example:
        display_date = format_date_for_display(date(2026, 3, 10))
        # Returns: "Monday, March 10, 2026"
    """
    try:
        return date_obj.strftime("%A, %B %d, %Y")
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return str(date_obj)


def format_time_for_display(time_obj: time) -> str:
    """
    Format time object for user-friendly display.
    
    Args:
        time_obj: Time object to format
        
    Returns:
        Formatted time string (e.g., "10:00 AM")
        
    Example:
        display_time = format_time_for_display(time(10, 0))
        # Returns: "10:00 AM"
    """
    try:
        return time_obj.strftime("%I:%M %p")
    except Exception as e:
        logger.error(f"Error formatting time: {e}")
        return str(time_obj)
