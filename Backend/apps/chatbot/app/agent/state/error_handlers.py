"""
Comprehensive error handling utilities for the chatbot agent.

This module provides centralized error handling for LLM responses, state management,
tool invocations, and validation errors. It implements the error handling strategies
defined in the design document.

Requirements: 2.5, 20.1, 20.2, 20.3, 20.4
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# LLM Response Error Handlers (Requirement 20.1)
# ============================================================================

def handle_llm_api_error(
    error: Exception,
    context: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Handle LLM API failures with user-friendly error messages.
    
    This function handles various LLM API errors (connection, timeout, rate limit)
    and returns a safe default response that allows the conversation to continue.
    
    Args:
        error: The exception that occurred
        context: Context information (chat_id, current_node, etc.)
        
    Returns:
        Tuple of (next_node, message, state_updates)
        
    Example:
        try:
            response = await llm_provider.generate(prompt)
        except Exception as e:
            next_node, message, updates = handle_llm_api_error(e, {"chat_id": "123"})
            
    Requirement: 2.5, 20.1
    """
    from app.services.llm.base import (
        LLMConnectionError,
        LLMTimeoutError,
        LLMRateLimitError,
        LLMAuthenticationError,
        LLMProviderUnavailableError,
        LLMProviderError
    )
    
    chat_id = context.get("chat_id", "unknown")
    current_node = context.get("current_node", "greeting")
    
    # Map error types to user-friendly messages
    if isinstance(error, LLMConnectionError):
        logger.error(
            f"LLM connection error for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "I'm having trouble connecting to my service. "
            "Please try again in a moment."
        )
        
    elif isinstance(error, LLMTimeoutError):
        logger.error(
            f"LLM timeout error for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "My response is taking longer than expected. "
            "Please try again."
        )
        
    elif isinstance(error, LLMRateLimitError):
        logger.error(
            f"LLM rate limit error for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "I'm experiencing high demand right now. "
            "Please wait a moment and try again."
        )
        
    elif isinstance(error, LLMAuthenticationError):
        logger.critical(
            f"LLM authentication error for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "I'm experiencing a configuration issue. "
            "Please contact support."
        )
        
    elif isinstance(error, LLMProviderUnavailableError):
        logger.error(
            f"LLM provider unavailable for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "My service is temporarily unavailable. "
            "Please try again later."
        )
        
    elif isinstance(error, LLMProviderError):
        logger.error(
            f"LLM provider error for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "I encountered an error processing your request. "
            "Please try again."
        )
        
    else:
        logger.error(
            f"Unexpected error in LLM call for chat {chat_id}: {error}",
            exc_info=True
        )
        message = (
            "I'm having trouble processing your request. "
            "Please try again."
        )
    
    # Return safe defaults (Requirement 2.5)
    return (
        current_node or "greeting",  # Default to current node or greeting
        message,
        {}  # No state updates on error
    )


def handle_malformed_llm_response(
    response: Any,
    context: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Handle malformed LLM response structure.
    
    This function handles cases where the LLM returns a response that cannot
    be parsed or has an invalid structure.
    
    Args:
        response: The malformed response from LLM
        context: Context information (chat_id, current_node, etc.)
        
    Returns:
        Tuple of (next_node, message, state_updates)
        
    Requirement: 20.1
    """
    chat_id = context.get("chat_id", "unknown")
    current_node = context.get("current_node", "greeting")
    
    logger.error(
        f"Malformed LLM response for chat {chat_id}: {type(response)}",
        extra={"response": str(response)[:200]}  # Log first 200 chars
    )
    
    message = (
        "I'm having trouble understanding my own response. "
        "Let's try that again."
    )
    
    return (
        current_node or "greeting",
        message,
        {}
    )


# ============================================================================
# State Management Error Handlers (Requirement 20.2)
# ============================================================================

def handle_flow_state_corruption(
    flow_state: Any,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle corrupted flow_state by reinitializing.
    
    This function detects corrupted flow_state and returns a fresh initialized
    state to allow the conversation to continue.
    
    Args:
        flow_state: The potentially corrupted flow_state
        context: Context information (chat_id, etc.)
        
    Returns:
        Valid flow_state (either original if valid, or reinitialized)
        
    Example:
        flow_state = state.get("flow_state", {})
        flow_state = handle_flow_state_corruption(flow_state, {"chat_id": "123"})
        
    Requirement: 20.2
    """
    from app.agent.state.flow_state_manager import (
        validate_flow_state,
        initialize_flow_state
    )
    
    chat_id = context.get("chat_id", "unknown")
    
    # Check if flow_state is valid
    if not isinstance(flow_state, dict):
        logger.error(
            f"Flow state corruption detected for chat {chat_id}: "
            f"expected dict, got {type(flow_state)}"
        )
        return initialize_flow_state()
    
    # Validate structure
    if not validate_flow_state(flow_state):
        logger.error(
            f"Flow state structure invalid for chat {chat_id}, reinitializing"
        )
        return initialize_flow_state()
    
    # Flow state is valid
    return flow_state


async def handle_bot_memory_persistence_failure(
    error: Exception,
    context: Dict[str, Any]
) -> bool:
    """
    Handle bot_memory persistence failures.
    
    This function logs persistence failures but allows the conversation to
    continue. The memory will be lost but the conversation can proceed.
    
    Args:
        error: The exception that occurred during persistence
        context: Context information (chat_id, etc.)
        
    Returns:
        False to indicate persistence failed (for caller to handle)
        
    Example:
        try:
            await save_bot_memory(chat_id, bot_memory, db)
        except Exception as e:
            success = await handle_bot_memory_persistence_failure(e, {"chat_id": chat_id})
            
    Requirement: 20.2
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.error(
        f"Bot memory persistence failed for chat {chat_id}: {error}",
        exc_info=True
    )
    
    # Log but continue - memory will be lost but conversation can proceed
    logger.warning(
        f"Continuing conversation for chat {chat_id} without persisting memory"
    )
    
    return False


def handle_state_deserialization_error(
    error: Exception,
    state_type: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle state deserialization errors.
    
    This function handles errors when loading state from database or other
    storage. It returns an empty initialized state to allow recovery.
    
    Args:
        error: The deserialization exception
        state_type: Type of state ("flow_state" or "bot_memory")
        context: Context information (chat_id, etc.)
        
    Returns:
        Empty initialized state of the appropriate type
        
    Requirement: 20.2
    """
    from app.agent.state.flow_state_manager import initialize_flow_state
    
    chat_id = context.get("chat_id", "unknown")
    
    logger.error(
        f"State deserialization error for chat {chat_id}, "
        f"state_type={state_type}: {error}",
        exc_info=True
    )
    
    if state_type == "flow_state":
        logger.info(f"Reinitializing flow_state for chat {chat_id}")
        return initialize_flow_state()
    elif state_type == "bot_memory":
        logger.info(f"Reinitializing bot_memory for chat {chat_id}")
        return {
            "conversation_history": [],
            "user_preferences": {},
            "inferred_information": {},
            "context": {}
        }
    else:
        logger.warning(f"Unknown state_type: {state_type}, returning empty dict")
        return {}


# ============================================================================
# Tool Invocation Error Handlers (Requirement 20.3)
# ============================================================================

def handle_property_fetch_failure(
    error: Exception,
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle property fetch failures.
    
    Returns user-friendly error message and safe state to continue conversation.
    
    Args:
        error: The exception that occurred
        context: Context information (chat_id, owner_profile_id, etc.)
        
    Returns:
        Tuple of (error_message, response_metadata)
        
    Requirement: 20.3
    """
    chat_id = context.get("chat_id", "unknown")
    owner_profile_id = context.get("owner_profile_id", "unknown")
    
    logger.error(
        f"Property fetch failed for chat {chat_id}, "
        f"owner_profile_id={owner_profile_id}: {error}",
        exc_info=True
    )
    
    message = (
        "I'm having trouble accessing your properties right now. "
        "Please try again in a moment."
    )
    
    metadata = {
        "error_type": "property_fetch_failure",
        "recoverable": True
    }
    
    return (message, metadata)


def handle_court_fetch_failure(
    error: Exception,
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle court fetch failures.
    
    Returns user-friendly error message and safe state to continue conversation.
    
    Args:
        error: The exception that occurred
        context: Context information (chat_id, property_id, etc.)
        
    Returns:
        Tuple of (error_message, response_metadata)
        
    Requirement: 20.3
    """
    chat_id = context.get("chat_id", "unknown")
    property_id = context.get("property_id", "unknown")
    
    logger.error(
        f"Court fetch failed for chat {chat_id}, "
        f"property_id={property_id}: {error}",
        exc_info=True
    )
    
    message = (
        "I'm having trouble accessing the courts for this property. "
        "Please try again in a moment."
    )
    
    metadata = {
        "error_type": "court_fetch_failure",
        "recoverable": True
    }
    
    return (message, metadata)


def handle_availability_check_failure(
    error: Exception,
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle availability check failures.
    
    Returns user-friendly error message and safe state to continue conversation.
    
    Args:
        error: The exception that occurred
        context: Context information (chat_id, court_id, date, etc.)
        
    Returns:
        Tuple of (error_message, response_metadata)
        
    Requirement: 20.3
    """
    chat_id = context.get("chat_id", "unknown")
    court_id = context.get("court_id", "unknown")
    date = context.get("date", "unknown")
    
    logger.error(
        f"Availability check failed for chat {chat_id}, "
        f"court_id={court_id}, date={date}: {error}",
        exc_info=True
    )
    
    message = (
        "I'm having trouble checking availability right now. "
        "Please try again in a moment."
    )
    
    metadata = {
        "error_type": "availability_check_failure",
        "recoverable": True
    }
    
    return (message, metadata)


def handle_booking_creation_failure(
    error: Exception,
    context: Dict[str, Any],
    booking_data: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Handle booking creation failures.
    
    Returns user-friendly error message, next node for recovery, and metadata.
    
    Args:
        error: The exception that occurred
        context: Context information (chat_id, etc.)
        booking_data: The booking data that failed to create
        
    Returns:
        Tuple of (error_message, next_node, response_metadata)
        
    Requirement: 20.3
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.error(
        f"Booking creation failed for chat {chat_id}: {error}",
        extra={"booking_data": booking_data},
        exc_info=True
    )
    
    # Check if it's a conflict error (slot already booked)
    error_str = str(error).lower()
    if "conflict" in error_str or "already booked" in error_str:
        message = (
            "Sorry, that time slot was just booked by someone else. "
            "Let me show you other available times."
        )
        next_node = "select_time"  # Go back to time selection
    else:
        message = (
            "I encountered an error creating your booking. "
            "Please try selecting a different time slot."
        )
        next_node = "select_time"
    
    metadata = {
        "error_type": "booking_creation_failure",
        "recoverable": True,
        "suggested_action": "retry_with_different_time"
    }
    
    return (message, next_node, metadata)


# ============================================================================
# Validation Error Handlers (Requirement 20.4)
# ============================================================================

def handle_invalid_date_format(
    date_string: str,
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle invalid date format errors.
    
    Returns user-friendly error message with format guidance.
    
    Args:
        date_string: The invalid date string
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (error_message, response_metadata)
        
    Requirement: 20.4
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.warning(
        f"Invalid date format for chat {chat_id}: {date_string}"
    )
    
    message = (
        f"I couldn't understand the date '{date_string}'. "
        "Please use a format like 'March 10' or '2026-03-10', "
        "or try 'tomorrow' or 'next Monday'."
    )
    
    metadata = {
        "error_type": "invalid_date_format",
        "invalid_value": date_string,
        "expected_format": "YYYY-MM-DD or natural language"
    }
    
    return (message, metadata)


def handle_invalid_time_slot_format(
    time_string: str,
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Handle invalid time slot format errors.
    
    Returns user-friendly error message with format guidance.
    
    Args:
        time_string: The invalid time string
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (error_message, response_metadata)
        
    Requirement: 20.4
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.warning(
        f"Invalid time slot format for chat {chat_id}: {time_string}"
    )
    
    message = (
        f"I couldn't understand the time '{time_string}'. "
        "Please use a format like '10:00-11:00' or '2pm-3pm'."
    )
    
    metadata = {
        "error_type": "invalid_time_slot_format",
        "invalid_value": time_string,
        "expected_format": "HH:MM-HH:MM"
    }
    
    return (message, metadata)


def handle_missing_required_booking_data(
    missing_fields: list,
    context: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Handle missing required booking data errors.
    
    Returns user-friendly error message and next node to collect missing data.
    
    Args:
        missing_fields: List of missing field names
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (error_message, next_node, response_metadata)
        
    Requirement: 20.4
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.error(
        f"Missing required booking data for chat {chat_id}: {missing_fields}"
    )
    
    # Determine which node to route to based on first missing field
    field_to_node = {
        "property_id": "select_property",
        "court_id": "select_court",
        "date": "select_date",
        "time_slot": "select_time"
    }
    
    first_missing = missing_fields[0] if missing_fields else "property_id"
    next_node = field_to_node.get(first_missing, "select_property")
    
    message = (
        "Some booking information is missing. "
        "Let's start over to make sure we have everything."
    )
    
    metadata = {
        "error_type": "missing_required_data",
        "missing_fields": missing_fields,
        "recovery_node": next_node
    }
    
    return (message, next_node, metadata)


def handle_conflicting_booking_data(
    conflicts: Dict[str, Any],
    context: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Handle conflicting booking data errors.
    
    Returns user-friendly error message and next node to resolve conflicts.
    
    Args:
        conflicts: Dictionary describing the conflicts
        context: Context information (chat_id, etc.)
        
    Returns:
        Tuple of (error_message, next_node, response_metadata)
        
    Requirement: 20.4
    """
    chat_id = context.get("chat_id", "unknown")
    
    logger.error(
        f"Conflicting booking data for chat {chat_id}: {conflicts}"
    )
    
    message = (
        "I found some conflicting information in your booking. "
        "Let's start fresh to make sure everything is correct."
    )
    
    metadata = {
        "error_type": "conflicting_data",
        "conflicts": conflicts,
        "recovery_node": "select_property"
    }
    
    return (message, "select_property", metadata)


# ============================================================================
# Utility Functions
# ============================================================================

def log_error_with_context(
    error: Exception,
    error_type: str,
    context: Dict[str, Any],
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log error with full context for debugging.
    
    This utility function provides consistent error logging across all
    error handlers with structured context information.
    
    Args:
        error: The exception that occurred
        error_type: Type of error (e.g., "llm_api_error", "tool_failure")
        context: Context information (chat_id, user_id, etc.)
        extra_data: Additional data to log
    """
    log_data = {
        "error_type": error_type,
        "error_message": str(error),
        "chat_id": context.get("chat_id", "unknown"),
        "user_id": context.get("user_id", "unknown"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.error(
        f"Error occurred: {error_type}",
        extra=log_data,
        exc_info=True
    )
