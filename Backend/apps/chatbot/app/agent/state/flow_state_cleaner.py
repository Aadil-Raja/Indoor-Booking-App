"""
Flow state cleaner - removes temporary fields before saving to database.

Temporary fields are used during flow execution but should not be persisted:
- router_result: LLM analysis result (temporary)
- execution_results: Action execution results (temporary)
- validation_error: Validation error flag (temporary)
- bot_response: Temporary response text (temporary)
- next_step: Routing decision (temporary)
- requested_actions: Current request actions (temporary)

Persistent fields that SHOULD be saved:
- property_id, property_name: Selected property
- court_id, court_type: Selected court
- available_properties: Cached property list
- available_courts: Cached court list
- owner_properties_initialized: Initialization flag
- last_node: Last executed node
- awaiting_input: What input we're waiting for
- pending_actions: Actions waiting for input
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Temporary fields that should NOT be saved to database
TEMPORARY_FIELDS = {
    "router_result",        # LLM router analysis (temporary per request)
    "execution_results",    # Action execution results (temporary per request)
    "validation_error",     # Validation error flag (temporary per request)
    "bot_response",         # Temporary response text (temporary per request)
    "next_step",            # Routing decision (temporary per request)
    "requested_actions",    # Current request actions (temporary per request)
}


# Persistent fields that SHOULD be saved to database
PERSISTENT_FIELDS = {
    "property_id",                    # Selected property ID
    "property_name",                  # Selected property name
    "court_id",                       # Selected court ID
    "court_type",                     # Selected court type
    "available_properties",           # Cached property list
    "available_courts",               # Cached court list (essential details only)
    "owner_properties_initialized",   # Properties fetched flag
    "last_node",                      # Last executed node
    "awaiting_input",                 # What input we're waiting for
    "pending_actions",                # Actions waiting for input
}


def clean_flow_state_for_db(flow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove temporary fields from flow_state before saving to database.
    
    This function filters out fields that are only needed during flow execution
    and should not be persisted to the database.
    
    Args:
        flow_state: Flow state dictionary (may contain temporary fields)
        
    Returns:
        Cleaned flow state with only persistent fields
        
    Example:
        dirty_state = {
            "property_id": 123,
            "router_result": {...},  # temporary
            "execution_results": {...},  # temporary
            "available_properties": [...]
        }
        
        clean_state = clean_flow_state_for_db(dirty_state)
        # Returns: {"property_id": 123, "available_properties": [...]}
    """
    if not isinstance(flow_state, dict):
        logger.warning(f"Invalid flow_state type: {type(flow_state)}, returning empty dict")
        return {}
    
    # Create cleaned state with only persistent fields
    cleaned_state = {}
    
    for key, value in flow_state.items():
        if key in PERSISTENT_FIELDS:
            cleaned_state[key] = value
        elif key in TEMPORARY_FIELDS:
            logger.debug(f"Removing temporary field from flow_state: {key}")
        else:
            # Unknown field - log warning but keep it for forward compatibility
            logger.warning(f"Unknown flow_state field '{key}', keeping it for safety")
            cleaned_state[key] = value
    
    # Log what was removed
    removed_fields = [k for k in flow_state.keys() if k in TEMPORARY_FIELDS]
    if removed_fields:
        logger.info(f"Cleaned flow_state: removed temporary fields {removed_fields}")
    
    return cleaned_state


def validate_cleaned_state(flow_state: Dict[str, Any]) -> bool:
    """
    Validate that flow_state doesn't contain temporary fields.
    
    This is a safety check to ensure temporary fields aren't accidentally
    saved to the database.
    
    Args:
        flow_state: Flow state to validate
        
    Returns:
        True if clean (no temporary fields), False if dirty
    """
    if not isinstance(flow_state, dict):
        return False
    
    # Check for temporary fields
    found_temporary = []
    for key in flow_state.keys():
        if key in TEMPORARY_FIELDS:
            found_temporary.append(key)
    
    if found_temporary:
        logger.error(
            f"Flow state contains temporary fields that should not be saved: "
            f"{found_temporary}"
        )
        return False
    
    return True


def get_temporary_fields() -> set:
    """
    Get the set of temporary field names.
    
    Returns:
        Set of temporary field names
    """
    return TEMPORARY_FIELDS.copy()


def get_persistent_fields() -> set:
    """
    Get the set of persistent field names.
    
    Returns:
        Set of persistent field names
    """
    return PERSISTENT_FIELDS.copy()
