"""
Flow state management utilities.

This module provides functions for managing flow_state, which contains temporary
conversation state including router results, pending actions, and cached data.
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
        #     "property_id": None,
        #     "property_name": None,
        #     "court_id": None,
        #     "court_type": None,
        #     "available_properties": [],
        #     "owner_properties_initialized": False,
        #     "last_node": None,
        #     "awaiting_input": None,
        #     "pending_actions": [],
        #     "requested_actions": [],
        #     "router_result": {},
        #     "bot_response": "",
        #     "available_courts": []
        # }
    
    Requirements: 3.1, 3.9
    """
    flow_state = {
        "property_id": None,
        "property_name": None,
        "court_id": None,
        "court_type": None,
        "available_properties": [],
        "owner_properties_initialized": False,
        "last_node": None,
        "awaiting_input": None,  # None | "property_selection" | "court_selection"
        "pending_actions": [],  # actions waiting because some input was missing
        "requested_actions": [],  # actions from current message
        "available_courts": []
    }
    
    logger.debug("Initialized empty flow_state")
    return flow_state


def ensure_flow_state_fields(flow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure flow_state has all required fields without losing existing data.
    
    Adds missing fields with default values while preserving existing data.
    This is used when the flow_state structure is updated with new fields.
    
    Args:
        flow_state: Existing flow state dictionary
        
    Returns:
        Dict[str, Any]: Flow state with all required fields
        
    Example:
        # Old flow_state missing new fields
        old_state = {"property_id": 123, "court_id": 456}
        
        # Ensure all fields exist
        updated = ensure_flow_state_fields(old_state)
        # Returns: {"property_id": 123, "court_id": 456, "owner_properties_initialized": False, ...}
    """
    if not isinstance(flow_state, dict):
        logger.warning(f"Invalid flow_state type: {type(flow_state)}, initializing new")
        return initialize_flow_state()
    
    # Get default structure
    default_state = initialize_flow_state()
    
    # Merge: keep existing values, add missing fields with defaults
    merged_state = default_state.copy()
    merged_state.update(flow_state)
    
    # Special handling for router_result - merge dicts
    if "router_result" in flow_state and isinstance(flow_state["router_result"], dict):
        merged_router_result = default_state["router_result"].copy()
        merged_router_result.update(flow_state["router_result"])
        merged_state["router_result"] = merged_router_result
    
    logger.debug("Ensured flow_state has all required fields")
    return merged_state


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
        "property_id",
        "property_name",
        "court_id",
        "court_type",
        "available_properties",
        "owner_properties_initialized",
        "last_node",
        "awaiting_input",
        "pending_actions",
        "requested_actions",
        "available_courts"
    }
    
    # Check if all expected fields exist (values can be None)
    actual_fields = set(flow_state.keys())
    
    # Allow extra fields for forward compatibility, but require core fields
    if not expected_fields.issubset(actual_fields):
        missing_fields = expected_fields - actual_fields
        logger.warning(f"Flow state missing required fields: {missing_fields}")
        return False
    
    # Validate context is a dict if present
    if "router_result" in flow_state and flow_state["router_result"] is not None:
        if not isinstance(flow_state["router_result"], dict):
            logger.warning(f"Invalid router_result type: {type(flow_state['router_result'])}, expected dict")
            return False
    
    # Validate list fields
    if "pending_actions" in flow_state and flow_state["pending_actions"] is not None:
        if not isinstance(flow_state["pending_actions"], list):
            logger.warning(f"Invalid pending_actions type: {type(flow_state['pending_actions'])}, expected list")
            return False
    
    if "requested_actions" in flow_state and flow_state["requested_actions"] is not None:
        if not isinstance(flow_state["requested_actions"], list):
            logger.warning(f"Invalid requested_actions type: {type(flow_state['requested_actions'])}, expected list")
            return False
    
    if "available_properties" in flow_state and flow_state["available_properties"] is not None:
        if not isinstance(flow_state["available_properties"], list):
            logger.warning(f"Invalid available_properties type: {type(flow_state['available_properties'])}, expected list")
            return False
    
    if "available_courts" in flow_state and flow_state["available_courts"] is not None:
        if not isinstance(flow_state["available_courts"], list):
            logger.warning(f"Invalid available_courts type: {type(flow_state['available_courts'])}, expected list")
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
    the router_result field to preserve existing router data.
    
    Includes error handling for corrupted state.
    
    Args:
        current_flow_state: Current flow state dictionary
        updates: Dictionary of fields to update
        
    Returns:
        Dict[str, Any]: Updated flow_state
        
    Example:
        updated = update_flow_state(
            current_flow_state={"property_id": None, "router_result": {"intent": "booking"}},
            updates={"property_id": 123, "router_result": {"confidence": 0.95}}
        )
        # Returns: {"property_id": 123, "router_result": {"intent": "booking", "confidence": 0.95}}
    
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
    
    # Update all fields except router_result (shallow merge)
    for key, value in updates.items():
        try:
            if key == "router_result":
                # Deep merge for router_result field
                if "router_result" not in updated_state or updated_state["router_result"] is None:
                    updated_state["router_result"] = {}
                
                if isinstance(value, dict):
                    updated_state["router_result"].update(value)
                else:
                    logger.warning(f"router_result update value is not a dict: {type(value)}")
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
