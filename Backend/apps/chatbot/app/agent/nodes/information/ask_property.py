"""
Ask property node - asks user to select a property.

This node is called when a property is required but missing.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState

logger = logging.getLogger(__name__)


async def ask_property(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Ask user to select a property.
    
    This node:
    1. Sets awaiting_input = "property_selection"
    2. Moves requested_actions to pending_actions
    3. Prepares property list response
    4. Stops the graph for this turn
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with property selection prompt
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Asking for property selection for chat {chat_id}")
    
    # Get available properties
    available_properties = flow_state.get("available_properties", [])
    
    # Set awaiting_input
    flow_state["awaiting_input"] = "property_selection"
    
    # Move requested_actions to pending_actions
    requested_actions = flow_state.get("requested_actions", [])
    flow_state["pending_actions"] = requested_actions
    flow_state["requested_actions"] = []
    
    # Prepare response
    if available_properties:
        response = "Please select a property:\n\n"
        for idx, prop in enumerate(available_properties, 1):
            response += f"{idx}. {prop.get('name')}\n"
    else:
        response = "No properties available. Please contact support."
    
    # Set response
    state["response_content"] = response
    state["response_type"] = "text"
    
    # Track last node
    flow_state["last_node"] = "information-ask_property"
    state["flow_state"] = flow_state
    
    logger.info(
        f"[ASK PROPERTY] Chat {chat_id}:\n"
        f"  Pending Actions: {flow_state.get('pending_actions')}\n"
        f"  Available Properties: {len(available_properties)}"
    )
    
    return state
