"""
Check requirements node - determines what's needed for requested actions.

This node checks if all required inputs exist for the requested actions.
If something is missing, it decides which question to ask next.

Important rule: Ask for only ONE missing thing at a time.
"""

import logging
from typing import Dict, Any, Optional

from app.agent.state.conversation_state import ConversationState

logger = logging.getLogger(__name__)


# Action requirements map
ACTION_REQUIREMENTS = {
    "property_details": {"property": True, "court": False},
    "court_details": {"property": True, "court": True},
    "pricing": {"property": True, "court": True},
    "media": {"property": True, "court": True},
}


async def check_requirements(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Check if all required inputs exist for requested actions.
    
    This node:
    1. Gets requested_actions from flow_state
    2. Checks ACTION_REQUIREMENTS for each action
    3. Determines what's missing (property or court)
    4. Sets next_step to ask for ONE missing thing
    5. Important: Ask for only ONE thing at a time (property first, then court)
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with next_step set
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Checking requirements for chat {chat_id}")
    
    # Get current state
    requested_actions = flow_state.get("requested_actions", [])
    property_id = flow_state.get("property_id")
    court_id = flow_state.get("court_id")
    
    logger.debug(
        f"Current state for chat {chat_id}: "
        f"actions={requested_actions}, property_id={property_id}, court_id={court_id}"
    )
    
    # If no actions requested, nothing to check
    if not requested_actions:
        logger.info(f"No actions requested for chat {chat_id}, routing to execute")
        flow_state["next_step"] = "execute_actions"
        flow_state["last_node"] = "information-check_requirements"
        state["flow_state"] = flow_state
        return state
    
    # Check what's needed for all requested actions
    needs_property = False
    needs_court = False
    
    for action in requested_actions:
        requirements = ACTION_REQUIREMENTS.get(action, {})
        if requirements.get("property"):
            needs_property = True
        if requirements.get("court"):
            needs_court = True
    
    logger.debug(
        f"Requirements for chat {chat_id}: "
        f"needs_property={needs_property}, needs_court={needs_court}"
    )
    
    # Determine next step (ask for ONE thing at a time)
    # Priority: property first, then court
    
    if needs_property and not property_id:
        # Property is needed but missing
        logger.info(f"Property missing for chat {chat_id}, routing to ask_property")
        flow_state["next_step"] = "ask_property"
    elif needs_court and not court_id:
        # Court is needed but missing (property exists)
        logger.info(f"Court missing for chat {chat_id}, routing to ask_court")
        flow_state["next_step"] = "ask_court"
    else:
        # All required inputs exist
        logger.info(f"All requirements met for chat {chat_id}, routing to execute")
        flow_state["next_step"] = "execute_actions"
    
    # Track last node
    flow_state["last_node"] = "information-check_requirements"
    state["flow_state"] = flow_state
    
    logger.info(
        f"[CHECK REQUIREMENTS RESULT] Chat {chat_id}:\n"
        f"  Requested Actions: {requested_actions}\n"
        f"  Needs Property: {needs_property} (Have: {property_id is not None})\n"
        f"  Needs Court: {needs_court} (Have: {court_id is not None})\n"
        f"  Next Step: {flow_state.get('next_step')}"
    )
    
    return state
