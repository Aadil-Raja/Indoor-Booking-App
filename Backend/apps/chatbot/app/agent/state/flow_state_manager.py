"""
Flow state management utilities.

This module provides functions for managing flow_state, which contains temporary
conversation state including current intent, booking progress, and cached data.
Flow state is cleared after booking completion or cancellation.

Requirements: 3.1, 3.9, 15.1, 15.5
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def initialize_flow_state() -> Dict[str, Any]:
    """
    Create an empty flow_state with default structure.
    
    Initializes flow_state with all fields set to None or empty values.
    This function is called when starting a new conversation or after
    clearing state following booking completion.
    
    Returns:
        Dict[str, Any]: Empty flow_state with proper structure
        
    Example:
        flow_state = initialize_flow_state()
        # Returns:
        # {
        #     "current_intent": None,
        #     "property_id": None,
        #     "property_name": None,
        #     "court_id": None,
        #     "court_name": None,
        #     "date": None,
        #     "time_slot": None,
        #     "booking_step": None,
        #     "owner_properties": None,
        #     "context": {}
        # }
    
    Requirements: 3.1, 3.9
    """
    flow_state = {
        "current_intent": None,
        "property_id": None,
        "property_name": None,
        "court_id": None,
        "court_name": None,
        "date": None,
        "time_slot": None,
        "booking_step": None,
        "owner_properties": None,
        "context": {}
    }
    
    logger.debug("Initialized empty flow_state")
    return flow_state


def validate_flow_state(flow_state: Dict[str, Any]) -> bool:
    """
    Check if flow_state has valid structure.
    
    Validates that flow_state is a dictionary and contains the expected fields.
    Does not validate field values, only structure. This is used to detect
    corrupted state that needs reinitialization.
    
    Args:
        flow_state: Flow state dictionary to validate
        
    Returns:
        bool: True if structure is valid, False otherwise
        
    Example:
        valid = validate_flow_state(state["flow_state"])
        if not valid:
            state["flow_state"] = initialize_flow_state()
    
    Requirements: 3.1, 3.9
    """
    if not isinstance(flow_state, dict):
        logger.warning(f"Invalid flow_state type: {type(flow_state)}, expected dict")
        return False
    
    # Define expected fields (all are optional, but structure should exist)
    expected_fields = {
        "current_intent",
        "property_id",
        "property_name",
        "court_id",
        "court_name",
        "date",
        "time_slot",
        "booking_step",
        "owner_properties",
        "context"
    }
    
    # Check if all expected fields exist (values can be None)
    actual_fields = set(flow_state.keys())
    
    # Allow extra fields for forward compatibility, but require core fields
    if not expected_fields.issubset(actual_fields):
        missing_fields = expected_fields - actual_fields
        logger.warning(f"Flow state missing required fields: {missing_fields}")
        return False
    
    # Validate context is a dict if present
    if "context" in flow_state and flow_state["context"] is not None:
        if not isinstance(flow_state["context"], dict):
            logger.warning(f"Invalid context type: {type(flow_state['context'])}, expected dict")
            return False
    
    logger.debug("Flow state structure is valid")
    return True


def update_flow_state(
    current_flow_state: Dict[str, Any],
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge state updates into current flow_state.
    
    Updates flow_state with new values from the updates dictionary.
    Performs a shallow merge for top-level fields and deep merge for
    the context field to preserve existing context data.
    
    Includes error handling for corrupted state.
    
    Args:
        current_flow_state: Current flow state dictionary
        updates: Dictionary of fields to update
        
    Returns:
        Dict[str, Any]: Updated flow_state
        
    Example:
        updated = update_flow_state(
            current_flow_state={"property_id": None, "context": {"step": 1}},
            updates={"property_id": 123, "context": {"property_name": "Court A"}}
        )
        # Returns: {"property_id": 123, "context": {"step": 1, "property_name": "Court A"}}
    
    Requirements: 3.9, 15.1, 20.2
    """
    # Handle corrupted flow_state (Requirement 20.2)
    if not isinstance(current_flow_state, dict):
        logger.error(
            f"Current flow_state is not a dict: {type(current_flow_state)}, "
            "initializing new state"
        )
        current_flow_state = initialize_flow_state()
    
    if not isinstance(updates, dict):
        logger.error(
            f"Updates is not a dict: {type(updates)}, skipping update"
        )
        return current_flow_state
    
    # Validate flow_state structure before updating
    if not validate_flow_state(current_flow_state):
        logger.error(
            "Flow state structure invalid before update, reinitializing"
        )
        current_flow_state = initialize_flow_state()
    
    # Create a copy to avoid mutating the original
    try:
        updated_state = current_flow_state.copy()
    except Exception as e:
        logger.error(f"Error copying flow_state: {e}, reinitializing")
        updated_state = initialize_flow_state()
    
    # Update all fields except context (shallow merge)
    for key, value in updates.items():
        try:
            if key == "context":
                # Deep merge for context field
                if "context" not in updated_state or updated_state["context"] is None:
                    updated_state["context"] = {}
                
                if isinstance(value, dict):
                    updated_state["context"].update(value)
                else:
                    logger.warning(f"Context update value is not a dict: {type(value)}")
            else:
                # Shallow merge for other fields
                updated_state[key] = value
        except Exception as e:
            logger.error(f"Error updating field {key}: {e}, skipping field")
            continue
    
    logger.debug(f"Updated flow_state with fields: {list(updates.keys())}")
    return updated_state


def clear_flow_state() -> Dict[str, Any]:
    """
    Reset flow_state after booking completion or cancellation.
    
    This function is called when a booking is successfully created or
    when the user cancels the booking process. It returns a fresh
    empty flow_state to start a new conversation flow.
    
    Returns:
        Dict[str, Any]: Empty flow_state with default structure
        
    Example:
        # After successful booking
        state["flow_state"] = clear_flow_state()
        
    Requirements: 15.5
    """
    logger.info("Clearing flow_state after booking completion/cancellation")
    return initialize_flow_state()


def clear_booking_field(
    flow_state: Dict[str, Any],
    field_name: str
) -> Dict[str, Any]:
    """
    Clear a specific booking field and its related fields from flow_state.
    
    This function supports selective field updates for reversibility.
    When a user changes a specific booking detail, only that field and
    dependent fields are cleared while preserving other information.
    
    Field clearing rules:
    - property: clears property_id, property_name, and all downstream fields
    - court: clears court_id, court_name, and all downstream fields
    - date: clears date and all downstream fields
    - time_slot: clears only time_slot
    
    Args:
        flow_state: Current flow state dictionary
        field_name: Name of the field to clear ("property", "court", "date", "time_slot")
        
    Returns:
        Dict[str, Any]: Updated flow_state with cleared fields
        
    Example:
        # User wants to change property
        flow_state = clear_booking_field(flow_state, "property")
        # Clears: property_id, property_name, court_id, court_name, date, time_slot
        
    Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
    """
    if not isinstance(flow_state, dict):
        logger.warning("Flow state is not a dict, cannot clear field")
        return flow_state
    
    # Create a copy to avoid mutating the original
    updated_state = flow_state.copy()
    
    if field_name == "property":
        # Clear property and all downstream fields
        updated_state["property_id"] = None
        updated_state["property_name"] = None
        updated_state["court_id"] = None
        updated_state["court_name"] = None
        updated_state["date"] = None
        updated_state["time_slot"] = None
        updated_state["booking_step"] = None
        logger.info("Cleared property and all downstream booking fields")
        
    elif field_name == "court":
        # Clear court and all downstream fields
        updated_state["court_id"] = None
        updated_state["court_name"] = None
        updated_state["date"] = None
        updated_state["time_slot"] = None
        # Update booking step to property_selected
        if updated_state.get("property_id"):
            updated_state["booking_step"] = "property_selected"
        else:
            updated_state["booking_step"] = None
        logger.info("Cleared court and all downstream booking fields")
        
    elif field_name == "date":
        # Clear date and all downstream fields
        updated_state["date"] = None
        updated_state["time_slot"] = None
        # Update booking step to court_selected
        if updated_state.get("court_id"):
            updated_state["booking_step"] = "court_selected"
        elif updated_state.get("property_id"):
            updated_state["booking_step"] = "property_selected"
        else:
            updated_state["booking_step"] = None
        logger.info("Cleared date and all downstream booking fields")
        
    elif field_name == "time_slot":
        # Clear only time_slot
        updated_state["time_slot"] = None
        # Update booking step to date_selected
        if updated_state.get("date"):
            updated_state["booking_step"] = "date_selected"
        elif updated_state.get("court_id"):
            updated_state["booking_step"] = "court_selected"
        elif updated_state.get("property_id"):
            updated_state["booking_step"] = "property_selected"
        else:
            updated_state["booking_step"] = None
        logger.info("Cleared time_slot field")
        
    else:
        logger.warning(f"Unknown field name for clearing: {field_name}")
    
    return updated_state
