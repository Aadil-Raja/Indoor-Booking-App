"""
Ask court node - asks user to select a court.

This node is called when a court is required but missing.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

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
    
    # Note: requested_actions and pending_actions are already set by check_requirements
    # requested_actions = actions that can execute now (if any)
    # pending_actions = actions that need court
    
    # Prepare response with unique sport types
    if filtered_courts:
        # Get unique sport types from all courts
        unique_sport_types = set()
        for court in filtered_courts:
            sport_types = court.get("sport_types", [])
            for sport_type in sport_types:
                unique_sport_types.add(sport_type)
        
        response = "Please select a sport:\n\n"
        for idx, sport_type in enumerate(sorted(unique_sport_types), 1):
            response += f"{idx}. {sport_type}\n"
    else:
        response = "No courts available for this property."
    
    # Store question in flow_state (not response_content directly)
    # This allows format_response to combine with execution results
    flow_state["question"] = response
    
    # Track last node
    flow_state["last_node"] = "information-ask_court"
    state["flow_state"] = flow_state
    
    # Log ask court action
    llm_logger = get_llm_logger()
    ask_summary = (
        f"Pending Actions: {flow_state.get('pending_actions')}\n"
        f"Property ID: {property_id}\n"
        f"Available Courts: {len(filtered_courts)}\n"
        f"Response:\n{response}"
    )
    llm_logger.log_llm_call(
        node_name="ask_court",
        prompt="[No LLM call - asks user to select court from available list]",
        response=ask_summary,
        parameters=None
    )
    
    logger.info(
        f"[ASK COURT] Chat {chat_id}:\n"
        f"  Pending Actions: {flow_state.get('pending_actions')}\n"
        f"  Available Courts: {len(filtered_courts)}"
    )
    
    return state
