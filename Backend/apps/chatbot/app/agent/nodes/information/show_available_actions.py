"""
Show available actions node - suggests what the user can do with selected property/court.

This node is called when a property or court is selected but no specific action was requested.
It offers to show details, location, media, etc.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


async def show_available_actions(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Show available actions for selected property/court.
    
    This node:
    1. Checks what's selected (property and/or court)
    2. Generates a helpful message suggesting available actions
    3. Sets response_content with suggestions
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with available actions message
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Showing available actions for chat {chat_id}")
    
    # Get current state
    property_id = flow_state.get("property_id")
    property_name = flow_state.get("property_name")
    court_ids = flow_state.get("court_ids", [])
    court_type = flow_state.get("court_type")
    validation_error = flow_state.get("validation_error")
    router_result = flow_state.get("router_result", {})
    unclear_reason = router_result.get("unclear_reason")
    
    # Build response based on what's selected
    response_parts = []
    
    # Add error message if present
    if validation_error:
        if validation_error == "invalid_property":
            response_parts.append("I couldn't find that property.")
        elif validation_error == "invalid_court":
            response_parts.append("I couldn't find that court.")
        elif validation_error == "unclear_message":
            # Use unclear_reason if available, otherwise generic message
            if unclear_reason:
                response_parts.append(unclear_reason)
            else:
                response_parts.append("I couldn't understand that.")
        else:
            response_parts.append("Something went wrong.")
        response_parts.append("")  # Empty line for spacing
        
        # Clear the error after showing it
        flow_state["validation_error"] = None
    
    if property_id and court_ids:
        # Both property and court selected
        response_parts.append(
            f"I can help you with {property_name} - {court_type}:"
        )
        response_parts.append("• Court details and description")
        response_parts.append("• Pricing information")
        response_parts.append("• Photos and media")
        response_parts.append("• Location and directions")
        response_parts.append("\nWhat would you like to know?")
        
    elif property_id:
        # Only property selected
        response_parts.append(
            f"I can help you with {property_name}:"
        )
        response_parts.append("• Property details and facilities")
        response_parts.append("• Available courts")
        response_parts.append("• Location and directions")
        response_parts.append("• Photos and media")
        response_parts.append("\nWhat would you like to know?")
    
    else:
        # No property or court selected - show generic help with available options
        available_properties = flow_state.get("available_properties", [])
        available_courts = flow_state.get("available_courts", [])
        
        response_parts.append("I can help you find information about sports facilities!")
        response_parts.append("\nYou can ask me about:")
        response_parts.append("• Property details and facilities")
        response_parts.append("• Court details and specifications")
        response_parts.append("• Pricing information")
        response_parts.append("• Location and directions")
        response_parts.append("• Photos and media")
        
        # Show available properties if any
        if available_properties:
            response_parts.append("\n📍 Available Properties:")
            for prop in available_properties[:5]:  # Show max 5
                response_parts.append(f"  • {prop.get('name')}")
            if len(available_properties) > 5:
                response_parts.append(f"  ... and {len(available_properties) - 5} more")
        
        # Show available courts if any
        if available_courts:
            # Get unique sport types
            unique_sports = set()
            for court in available_courts:
                sport_types = court.get('sport_types', [])
                for st in sport_types:
                    unique_sports.add(st)
            
            if unique_sports:
                response_parts.append("\n🏟️ Available Sports:")
                for sport in sorted(unique_sports):
                    response_parts.append(f"  • {sport}")
        
        response_parts.append("\nWhich property or sport would you like to know about?")
    
    response = "\n".join(response_parts)
    
    # Set response
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    # Track last node
    flow_state["last_node"] = "information-show_available_actions"
    state["flow_state"] = flow_state
    
    # Log the action
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        node_name="show_available_actions",
        prompt="[No LLM call - shows available actions for selected property/court]",
        response=response,
        parameters=None
    )
    
    logger.info(
        f"[SHOW AVAILABLE ACTIONS] Chat {chat_id}:\n"
        f"  Property: {property_name} (ID: {property_id})\n"
        f"  Court: {court_type} (IDs: {court_ids})"
    )
    
    return state
