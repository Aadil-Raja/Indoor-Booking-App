"""
Booking subgraph for LangGraph conversation management.

This module implements the booking flow subgraph that handles the multi-step
booking process. The subgraph wires together all booking nodes with conditional
routing logic to support:
- Sequential booking steps (property → service → date → time → confirm → create)
- Back navigation (user can go back to previous steps)
- Cancellation at any step
- Modification of booking details

Requirements: 6.3, 6.8, 22.1-22.6
"""

from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END

from app.agent.state.conversation_state import ConversationState
from app.agent.nodes.booking import (
    select_property,
    select_service,
    select_date,
    select_time,
    confirm_booking,
    create_pending_booking,
)

logger = logging.getLogger(__name__)


def create_booking_subgraph(tools: Dict[str, Any]) -> StateGraph:
    """
    Create the booking flow subgraph.
    
    This function creates a LangGraph StateGraph that manages the multi-step
    booking process. The graph includes:
    
    Nodes:
    - select_property: Present properties and handle property selection
    - select_service: Present courts/services and handle service selection
    - select_date: Present calendar and handle date selection
    - select_time: Present available time slots and handle time selection
    - confirm: Present booking summary and handle confirmation
    - create_booking: Create the booking in the system
    
    Routing:
    - Each node has conditional edges that check flow_state.step
    - Supports "continue" to next step, "back" to previous step, "cancel" to exit
    - User can say "back", "change X", "cancel", or "nevermind" at any step
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with nested nodes for booking flow
    - 6.8: Maintain state persistence between node transitions
    - 22.1: Present properties from search results
    - 22.2: Present booking summary including all details
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    
    Args:
        tools: Tool registry containing all agent tools
        
    Returns:
        Compiled StateGraph ready for execution
        
    Example:
        tools = TOOL_REGISTRY
        booking_graph = create_booking_subgraph(tools)
        
        # Execute the graph
        state = {
            "chat_id": "123",
            "user_message": "I want to book a court",
            "flow_state": {"intent": "booking"},
            ...
        }
        result = await booking_graph.ainvoke(state)
    """
    logger.info("Creating booking subgraph")
    
    # Initialize graph with ConversationState
    graph = StateGraph(ConversationState)
    
    # Add all booking nodes
    graph.add_node("select_property", lambda state: select_property(state, tools))
    graph.add_node("select_service", lambda state: select_service(state, tools))
    graph.add_node("select_date", lambda state: select_date(state, tools))
    graph.add_node("select_time", lambda state: select_time(state, tools))
    graph.add_node("confirm", lambda state: confirm_booking(state, tools))
    graph.add_node("create_booking", lambda state: create_pending_booking(state, tools))
    
    # Set entry point
    graph.set_entry_point("select_property")
    
    # Define conditional edges with routing functions
    
    # From select_property
    graph.add_conditional_edges(
        "select_property",
        route_property_selection,
        {
            "continue": "select_service",
            "cancel": END
        }
    )
    
    # From select_service
    graph.add_conditional_edges(
        "select_service",
        route_service_selection,
        {
            "continue": "select_date",
            "back": "select_property",
            "cancel": END
        }
    )
    
    # From select_date
    graph.add_conditional_edges(
        "select_date",
        route_date_selection,
        {
            "continue": "select_time",
            "back": "select_service",
            "cancel": END
        }
    )
    
    # From select_time
    graph.add_conditional_edges(
        "select_time",
        route_time_selection,
        {
            "continue": "confirm",
            "back": "select_date",
            "cancel": END
        }
    )
    
    # From confirm
    graph.add_conditional_edges(
        "confirm",
        route_confirmation,
        {
            "confirmed": "create_booking",
            "modify": "select_property",  # Allow full modification
            "cancel": END
        }
    )
    
    # From create_booking - always end
    graph.add_edge("create_booking", END)
    
    logger.info("Booking subgraph created successfully")
    
    # Compile and return the graph
    return graph.compile()


def route_property_selection(state: ConversationState) -> str:
    """
    Route based on property selection.
    
    This function checks if a property has been selected in flow_state.
    If property_id is present, route to next step. Otherwise, check for
    cancellation intent.
    
    Args:
        state: ConversationState containing flow_state and user_message
        
    Returns:
        "continue" if property selected, "cancel" otherwise
    """
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    # Check for cancellation
    if _is_cancel_intent(user_message):
        logger.info(f"Property selection cancelled for chat {state['chat_id']}")
        return "cancel"
    
    # Check if property selected
    if flow_state.get("property_id"):
        logger.debug(
            f"Property selected for chat {state['chat_id']}: "
            f"property_id={flow_state.get('property_id')}"
        )
        return "continue"
    
    # No property selected yet, stay in select_property
    # This shouldn't happen in normal flow, but handle gracefully
    logger.warning(
        f"No property selected for chat {state['chat_id']}, "
        f"routing to cancel"
    )
    return "cancel"


def route_service_selection(state: ConversationState) -> str:
    """
    Route based on service selection.
    
    This function checks the user's message for navigation intent (back, cancel)
    and checks if a service has been selected in flow_state.
    
    Args:
        state: ConversationState containing flow_state and user_message
        
    Returns:
        "continue" if service selected, "back" if user wants to go back,
        "cancel" if user wants to cancel
    """
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    # Check for back navigation
    if _is_back_intent(user_message):
        logger.info(f"Service selection - going back for chat {state['chat_id']}")
        return "back"
    
    # Check for cancellation
    if _is_cancel_intent(user_message):
        logger.info(f"Service selection cancelled for chat {state['chat_id']}")
        return "cancel"
    
    # Check if service selected
    if flow_state.get("service_id"):
        logger.debug(
            f"Service selected for chat {state['chat_id']}: "
            f"service_id={flow_state.get('service_id')}"
        )
        return "continue"
    
    # No service selected yet, stay in select_service
    logger.warning(
        f"No service selected for chat {state['chat_id']}, "
        f"routing to cancel"
    )
    return "cancel"


def route_date_selection(state: ConversationState) -> str:
    """
    Route based on date selection.
    
    This function checks the user's message for navigation intent (back, cancel)
    and checks if a date has been selected in flow_state.
    
    Args:
        state: ConversationState containing flow_state and user_message
        
    Returns:
        "continue" if date selected, "back" if user wants to go back,
        "cancel" if user wants to cancel
    """
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    # Check for back navigation
    if _is_back_intent(user_message):
        logger.info(f"Date selection - going back for chat {state['chat_id']}")
        return "back"
    
    # Check for cancellation
    if _is_cancel_intent(user_message):
        logger.info(f"Date selection cancelled for chat {state['chat_id']}")
        return "cancel"
    
    # Check if date selected
    if flow_state.get("date"):
        logger.debug(
            f"Date selected for chat {state['chat_id']}: "
            f"date={flow_state.get('date')}"
        )
        return "continue"
    
    # No date selected yet, stay in select_date
    logger.warning(
        f"No date selected for chat {state['chat_id']}, "
        f"routing to cancel"
    )
    return "cancel"


def route_time_selection(state: ConversationState) -> str:
    """
    Route based on time selection.
    
    This function checks the user's message for navigation intent (back, cancel)
    and checks if a time has been selected in flow_state.
    
    Args:
        state: ConversationState containing flow_state and user_message
        
    Returns:
        "continue" if time selected, "back" if user wants to go back,
        "cancel" if user wants to cancel
    """
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    # Check for back navigation
    if _is_back_intent(user_message):
        logger.info(f"Time selection - going back for chat {state['chat_id']}")
        return "back"
    
    # Check for cancellation
    if _is_cancel_intent(user_message):
        logger.info(f"Time selection cancelled for chat {state['chat_id']}")
        return "cancel"
    
    # Check if time selected
    if flow_state.get("time"):
        logger.debug(
            f"Time selected for chat {state['chat_id']}: "
            f"time={flow_state.get('time')}"
        )
        return "continue"
    
    # No time selected yet, stay in select_time
    logger.warning(
        f"No time selected for chat {state['chat_id']}, "
        f"routing to cancel"
    )
    return "cancel"


def route_confirmation(state: ConversationState) -> str:
    """
    Route based on user confirmation.
    
    This function checks the user's message to determine if they want to:
    - Confirm the booking (yes, confirm, book, proceed)
    - Modify the booking (change, modify, edit)
    - Cancel the booking (no, cancel, nevermind)
    
    Args:
        state: ConversationState containing user_message
        
    Returns:
        "confirmed" if user confirms, "modify" if user wants to change,
        "cancel" if user wants to cancel
    """
    user_message = state.get("user_message", "").lower()
    
    # Check for confirmation
    confirmation_keywords = ["yes", "confirm", "book", "proceed", "ok", "okay", "sure"]
    if any(word in user_message for word in confirmation_keywords):
        logger.info(f"Booking confirmed for chat {state['chat_id']}")
        return "confirmed"
    
    # Check for modification
    modification_keywords = ["change", "modify", "edit", "different", "another"]
    if any(word in user_message for word in modification_keywords):
        logger.info(f"Booking modification requested for chat {state['chat_id']}")
        return "modify"
    
    # Default to cancel for any other response
    logger.info(f"Booking cancelled for chat {state['chat_id']}")
    return "cancel"


def _is_back_intent(message: str) -> bool:
    """
    Check if user message indicates back navigation intent.
    
    Args:
        message: User message (lowercase)
        
    Returns:
        True if message indicates back intent, False otherwise
    """
    back_keywords = ["back", "previous", "go back", "return"]
    return any(keyword in message for keyword in back_keywords)


def _is_cancel_intent(message: str) -> bool:
    """
    Check if user message indicates cancellation intent.
    
    Args:
        message: User message (lowercase)
        
    Returns:
        True if message indicates cancel intent, False otherwise
    """
    cancel_keywords = ["cancel", "nevermind", "never mind", "stop", "quit", "exit"]
    return any(keyword in message for keyword in cancel_keywords)
