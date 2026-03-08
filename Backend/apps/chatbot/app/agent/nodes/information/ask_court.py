"""
Ask court node - asks user to select a court.

This node is called when a court is required but missing.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState

logger = logging.getLogger(__name__)


async def ask_court(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Ask user to select a court.
    
    This node:
    1. Sets awaiting_input = "court_selection"
    2. Moves requested_actions to pending_actions
    3. Prepares court list response (filtered by property)
    4. Stops the graph for this turn
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with court selection prompt
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Asking for court selection for chat {chat_id}")
    
    # Get available courts and current property
    available_courts = flow_state.get("available_courts", [])
    property_id = flow_state.get("property_id")
    
    # Filter courts by current property
    if property_id:
        filtered_courts = [
            c for c in available_courts
            if c.get("property_id") == property_id
        ]
    else:
        filtered_courts = available_courts
    
    # Set awaiting_input
    flow_state["awaiting_input"] = "court_selection"
    
    # Move requested_actions to pending_actions
    requested_actions = flow_state.get("requested_actions", [])
    flow_state["pending_actions"] = requested_actions
    flow_state["requested_actions"] = []
    
    # Prepare response with unique sport types
    if filtered_courts:
        # Get unique sport types
        sport_types = {}
        for idx, court in enumerate(filtered_courts, 1):
            sport_type = court.get("sport_type") or court.get("name", "Court")
            if sport_type not in sport_types:
                sport_types[sport_type] = idx
        
        response = "Please select a court:\n\n"
        for idx, sport_type in enumerate(sorted(sport_types.keys()), 1):
            response += f"{idx}. {sport_type}\n"
    else:
        response = "No courts available for this property."
    
    # Set response
    state["response_content"] = response
    state["response_type"] = "text"
    
    # Track last node
    flow_state["last_node"] = "information-ask_court"
    state["flow_state"] = flow_state
    
    logger.info(
        f"[ASK COURT] Chat {chat_id}:\n"
        f"  Pending Actions: {flow_state.get('pending_actions')}\n"
        f"  Available Courts: {len(filtered_courts)}"
    )
    
    return state
