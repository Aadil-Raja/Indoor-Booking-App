"""
Flow validation utilities for booking subgraph.

This module provides utilities to validate and enforce sequential ordering
in the booking flow, ensuring that steps are completed in the correct order:
property → court → date → time → confirm

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.3, 8.4
"""

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_next_incomplete_step(flow_state: Dict[str, Any]) -> str:
    """
    Determine the next incomplete step in the booking flow.
    
    This function checks flow_state to find the first incomplete step
    in the sequential booking flow: property → court → date → time → confirm.
    
    Implements Requirements:
    - 7.1: Skip property selection when property_id exists
    - 7.2: Skip court selection when court_id exists
    - 7.3: Skip date selection when date exists
    - 7.4: Skip time selection when time_slot exists
    - 7.6: Proceed directly to next incomplete step
    
    Args:
        flow_state: Current flow state dictionary
        
    Returns:
        Next node name: "select_property", "select_court", "select_date",
                       "select_time", or "confirm_booking"
        
    Example:
        # No data - start from property
        flow_state = {}
        next_step = get_next_incomplete_step(flow_state)
        # Returns: "select_property"
        
        # Property selected - go to court
        flow_state = {"property_id": 1, "property_name": "Sports Center"}
        next_step = get_next_incomplete_step(flow_state)
        # Returns: "select_court"
        
        # Property and court selected - go to date
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A"
        }
        next_step = get_next_incomplete_step(flow_state)
        # Returns: "select_date"
        
        # All data present - go to confirmation
        flow_state = {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00"
        }
        next_step = get_next_incomplete_step(flow_state)
        # Returns: "confirm_booking"
    """
    # Check each step in sequential order
    
    # Step 1: Property selection (Requirements 7.1)
    if not flow_state.get("property_id"):
        logger.debug("Next incomplete step: select_property")
        return "select_property"
    
    # Step 2: Court selection (Requirements 7.2)
    if not flow_state.get("court_id"):
        logger.debug("Next incomplete step: select_court")
        return "select_court"
    
    # Step 3: Date selection (Requirements 7.3)
    if not flow_state.get("date"):
        logger.debug("Next incomplete step: select_date")
        return "select_date"
    
    # Step 4: Time selection (Requirements 7.4)
    if not flow_state.get("time_slot"):
        logger.debug("Next incomplete step: select_time")
        return "select_time"
    
    # All steps complete - go to confirmation
    logger.debug("All booking steps complete, next: confirm_booking")
    return "confirm_booking"


def validate_booking_flow_sequence(
    current_node: str,
    flow_state: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that the current node is appropriate for the flow_state.
    
    This function ensures sequential ordering by checking if the current node
    should be skipped based on existing flow_state data, or if prerequisites
    are missing.
    
    Implements Requirements:
    - 7.5: Check flow_state before asking questions
    - 7.6: Proceed directly to next incomplete step
    - 8.1: Follow sequential ordering
    
    Args:
        current_node: Name of the current node being executed
        flow_state: Current flow state dictionary
        
    Returns:
        Tuple of (is_valid, redirect_node):
        - is_valid: True if current node is appropriate, False if should redirect
        - redirect_node: Node to redirect to if is_valid is False, None otherwise
        
    Example:
        # Trying to select court without property - invalid
        is_valid, redirect = validate_booking_flow_sequence(
            "select_court",
            {}
        )
        # Returns: (False, "select_property")
        
        # Trying to select property when already selected - invalid
        is_valid, redirect = validate_booking_flow_sequence(
            "select_property",
            {"property_id": 1, "property_name": "Sports Center"}
        )
        # Returns: (False, "select_court")
        
        # Selecting court with property selected - valid
        is_valid, redirect = validate_booking_flow_sequence(
            "select_court",
            {"property_id": 1, "property_name": "Sports Center"}
        )
        # Returns: (True, None)
    """
    # Get the next incomplete step
    next_step = get_next_incomplete_step(flow_state)
    
    # If current node matches next step, it's valid
    if current_node == next_step:
        logger.debug(
            f"Node {current_node} is valid for current flow_state"
        )
        return True, None
    
    # Current node doesn't match - should redirect
    logger.info(
        f"Node {current_node} should be skipped, redirecting to {next_step}"
    )
    return False, next_step


def should_skip_to_next_step(
    current_node: str,
    flow_state: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Determine if the current node should be skipped based on flow_state.
    
    This is a convenience function that checks if the current node's data
    already exists in flow_state and returns the next node to proceed to.
    
    Implements Requirements:
    - 7.1: Skip property selection when property_id exists
    - 7.2: Skip court selection when court_id exists
    - 7.3: Skip date selection when date exists
    - 7.4: Skip time selection when time_slot exists
    - 7.6: Proceed directly to next incomplete step
    
    Args:
        current_node: Name of the current node being executed
        flow_state: Current flow state dictionary
        
    Returns:
        Tuple of (should_skip, next_node):
        - should_skip: True if current node should be skipped, False otherwise
        - next_node: Node to proceed to if should_skip is True, None otherwise
        
    Example:
        # Property already selected - skip to court
        should_skip, next_node = should_skip_to_next_step(
            "select_property",
            {"property_id": 1, "property_name": "Sports Center"}
        )
        # Returns: (True, "select_court")
        
        # Property not selected - don't skip
        should_skip, next_node = should_skip_to_next_step(
            "select_property",
            {}
        )
        # Returns: (False, None)
    """
    # Check based on current node
    if current_node == "select_property":
        if flow_state.get("property_id"):
            # Property already selected, skip to court (Requirement 7.1)
            return True, "select_court"
        return False, None
    
    elif current_node == "select_court":
        if flow_state.get("court_id"):
            # Court already selected, skip to date (Requirement 7.2)
            return True, "select_date"
        return False, None
    
    elif current_node == "select_date":
        if flow_state.get("date"):
            # Date already selected, skip to time (Requirement 7.3)
            return True, "select_time"
        return False, None
    
    elif current_node == "select_time":
        if flow_state.get("time_slot"):
            # Time already selected, skip to confirmation (Requirement 7.4)
            return True, "confirm_booking"
        return False, None
    
    # Unknown node or no skip needed
    return False, None


def validate_required_fields_for_step(
    step: str,
    flow_state: Dict[str, Any]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that all required fields are present for a given step.
    
    This function checks if the prerequisites for a step are met,
    ensuring sequential ordering is maintained.
    
    Args:
        step: Name of the step to validate
        flow_state: Current flow state dictionary
        
    Returns:
        Tuple of (is_valid, missing_field, redirect_node):
        - is_valid: True if all prerequisites are met, False otherwise
        - missing_field: Name of the missing field if is_valid is False
        - redirect_node: Node to redirect to if is_valid is False
        
    Example:
        # Trying to select time without date
        is_valid, missing, redirect = validate_required_fields_for_step(
            "select_time",
            {"property_id": 1, "court_id": 10}
        )
        # Returns: (False, "date", "select_date")
    """
    # Define prerequisites for each step
    prerequisites = {
        "select_property": [],  # No prerequisites
        "select_court": ["property_id"],
        "select_date": ["property_id", "court_id"],
        "select_time": ["property_id", "court_id", "date"],
        "confirm_booking": ["property_id", "court_id", "date", "time_slot"]
    }
    
    # Get required fields for this step
    required_fields = prerequisites.get(step, [])
    
    # Check each required field
    for field in required_fields:
        if not flow_state.get(field):
            # Missing required field - determine redirect node
            if field == "property_id":
                redirect = "select_property"
            elif field == "court_id":
                redirect = "select_court"
            elif field == "date":
                redirect = "select_date"
            elif field == "time_slot":
                redirect = "select_time"
            else:
                redirect = "select_property"  # Default fallback
            
            logger.warning(
                f"Step {step} missing required field: {field}, "
                f"redirecting to {redirect}"
            )
            return False, field, redirect
    
    # All prerequisites met
    return True, None, None


def get_booking_progress_summary(flow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of the current booking progress.
    
    This function provides a structured view of which steps are complete
    and which are pending, useful for logging and debugging.
    
    Args:
        flow_state: Current flow state dictionary
        
    Returns:
        Dictionary with progress information:
        {
            "property_selected": bool,
            "court_selected": bool,
            "date_selected": bool,
            "time_selected": bool,
            "next_step": str,
            "completion_percentage": int
        }
        
    Example:
        summary = get_booking_progress_summary({
            "property_id": 1,
            "court_id": 10,
            "date": "2024-12-25"
        })
        # Returns: {
        #     "property_selected": True,
        #     "court_selected": True,
        #     "date_selected": True,
        #     "time_selected": False,
        #     "next_step": "select_time",
        #     "completion_percentage": 75
        # }
    """
    property_selected = bool(flow_state.get("property_id"))
    court_selected = bool(flow_state.get("court_id"))
    date_selected = bool(flow_state.get("date"))
    time_selected = bool(flow_state.get("time_slot"))
    
    # Calculate completion percentage
    completed_steps = sum([
        property_selected,
        court_selected,
        date_selected,
        time_selected
    ])
    total_steps = 4
    completion_percentage = int((completed_steps / total_steps) * 100)
    
    # Get next step
    next_step = get_next_incomplete_step(flow_state)
    
    return {
        "property_selected": property_selected,
        "court_selected": court_selected,
        "date_selected": date_selected,
        "time_selected": time_selected,
        "next_step": next_step,
        "completion_percentage": completion_percentage,
        "completed_steps": completed_steps,
        "total_steps": total_steps
    }
