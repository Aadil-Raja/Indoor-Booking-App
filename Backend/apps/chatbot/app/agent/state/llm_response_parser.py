"""
LLM response parser utility for extracting structured data from LLM responses.

This module provides functions to parse and validate LLM responses that contain
routing decisions (next_node), user-facing messages, and state updates.

Requirements: 2.1, 2.5, 13.1, 13.2, 13.3, 13.4, 13.5
"""

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# Valid next_node values according to design specification
VALID_NEXT_NODES = {"greeting", "information", "booking"}


class LLMResponseParseError(Exception):
    """Exception raised when LLM response cannot be parsed."""
    pass


def parse_llm_response(
    llm_response: Dict[str, Any],
    current_node: Optional[str] = None,
    strict: bool = False
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Parse LLM response to extract next_node, message, and state_updates.
    
    This function validates the LLM response structure and extracts the three
    critical components needed for conversation flow:
    - next_node: Where to route the conversation next
    - message: The text response to show the user
    - state_updates: Updates to flow_state and bot_memory
    
    Args:
        llm_response: The raw response from the LLM provider
        current_node: The current node name (used as fallback if next_node is missing)
        strict: If True, raise exception on validation errors; if False, use defaults
    
    Returns:
        Tuple of (next_node, message, state_updates)
        
    Raises:
        LLMResponseParseError: If strict=True and validation fails
        
    Requirements:
        - 2.1: LLM SHALL return next_node field
        - 2.5: If LLM does not return next_node, default to current node
        - 13.1: LLM SHALL return structured response with next_node, message, state_updates
        - 13.2: next_node SHALL contain one of: "greeting", "information", "booking"
        - 13.3: message field SHALL contain text response
        - 13.4: state_updates field SHALL contain updates to flow_state or bot_memory
        - 13.5: System SHALL apply state_updates before routing
    """
    
    # Validate that llm_response is a dictionary
    if not isinstance(llm_response, dict):
        error_msg = f"LLM response must be a dictionary, got {type(llm_response)}"
        logger.error(error_msg)
        if strict:
            raise LLMResponseParseError(error_msg)
        return _get_default_response(current_node)
    
    # Extract and validate next_node (Requirement 2.1, 2.5, 13.2)
    next_node = _extract_next_node(llm_response, current_node, strict)
    
    # Extract and validate message (Requirement 13.3)
    message = _extract_message(llm_response, strict)
    
    # Extract and validate state_updates (Requirement 13.4)
    state_updates = _extract_state_updates(llm_response, strict)
    
    return next_node, message, state_updates


def _extract_next_node(
    llm_response: Dict[str, Any],
    current_node: Optional[str],
    strict: bool
) -> str:
    """
    Extract and validate next_node from LLM response.
    
    Requirements:
        - 2.1: LLM SHALL return next_node field
        - 2.5: If missing, default to current node
        - 13.2: next_node SHALL be one of: "greeting", "information", "booking"
    """
    next_node = llm_response.get("next_node")
    
    # Handle missing next_node (Requirement 2.5)
    if next_node is None:
        logger.warning(
            f"LLM response missing next_node field, defaulting to current node: {current_node}"
        )
        if strict:
            raise LLMResponseParseError("Missing required field: next_node")
        return current_node or "greeting"
    
    # Validate next_node value (Requirement 13.2)
    if next_node not in VALID_NEXT_NODES:
        logger.error(
            f"Invalid next_node value: {next_node}. "
            f"Valid values are: {VALID_NEXT_NODES}. "
            f"Defaulting to 'greeting'"
        )
        if strict:
            raise LLMResponseParseError(
                f"Invalid next_node: {next_node}. Must be one of {VALID_NEXT_NODES}"
            )
        return "greeting"  # Safe default
    
    return next_node


def _extract_message(llm_response: Dict[str, Any], strict: bool) -> str:
    """
    Extract and validate message from LLM response.
    
    Requirement 13.3: message field SHALL contain text response
    """
    message = llm_response.get("message")
    
    # Handle missing message
    if message is None:
        logger.error("LLM response missing message field")
        if strict:
            raise LLMResponseParseError("Missing required field: message")
        return "I'm processing your request. Please continue."
    
    # Validate message is a string
    if not isinstance(message, str):
        logger.error(f"Message field must be a string, got {type(message)}")
        if strict:
            raise LLMResponseParseError(f"Message must be string, got {type(message)}")
        return str(message)  # Attempt conversion
    
    # Validate message is non-empty
    if len(message.strip()) == 0:
        logger.warning("LLM response contains empty message")
        if strict:
            raise LLMResponseParseError("Message cannot be empty")
        return "I'm here to help. What would you like to do?"
    
    return message


def _extract_state_updates(llm_response: Dict[str, Any], strict: bool) -> Dict[str, Any]:
    """
    Extract and validate state_updates from LLM response.
    
    Requirement 13.4: state_updates field SHALL contain updates to flow_state or bot_memory
    """
    state_updates = llm_response.get("state_updates")
    
    # Handle missing state_updates
    if state_updates is None:
        logger.debug("LLM response missing state_updates field, using empty dict")
        return {}
    
    # Validate state_updates is a dictionary
    if not isinstance(state_updates, dict):
        logger.error(f"state_updates must be a dictionary, got {type(state_updates)}")
        if strict:
            raise LLMResponseParseError(
                f"state_updates must be dict, got {type(state_updates)}"
            )
        return {}
    
    # Validate structure: should contain flow_state and/or bot_memory
    valid_keys = {"flow_state", "bot_memory"}
    invalid_keys = set(state_updates.keys()) - valid_keys
    
    if invalid_keys:
        logger.warning(
            f"state_updates contains unexpected keys: {invalid_keys}. "
            f"Valid keys are: {valid_keys}"
        )
        if strict:
            raise LLMResponseParseError(
                f"state_updates contains invalid keys: {invalid_keys}"
            )
    
    # Validate nested structures are dictionaries
    if "flow_state" in state_updates and not isinstance(state_updates["flow_state"], dict):
        logger.error("flow_state in state_updates must be a dictionary")
        if strict:
            raise LLMResponseParseError("flow_state must be a dictionary")
        state_updates["flow_state"] = {}
    
    if "bot_memory" in state_updates and not isinstance(state_updates["bot_memory"], dict):
        logger.error("bot_memory in state_updates must be a dictionary")
        if strict:
            raise LLMResponseParseError("bot_memory must be a dictionary")
        state_updates["bot_memory"] = {}
    
    return state_updates


def _get_default_response(current_node: Optional[str]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Get default response when LLM response is completely invalid.
    
    Returns safe defaults that allow conversation to continue.
    """
    return (
        current_node or "greeting",
        "I'm having trouble processing your request. Please try again.",
        {}
    )


def validate_llm_response_structure(llm_response: Dict[str, Any]) -> bool:
    """
    Validate that LLM response has the correct structure without extracting values.
    
    This is useful for testing and validation purposes.
    
    Args:
        llm_response: The LLM response to validate
        
    Returns:
        True if structure is valid, False otherwise
    """
    try:
        parse_llm_response(llm_response, current_node="greeting", strict=True)
        return True
    except LLMResponseParseError:
        return False
