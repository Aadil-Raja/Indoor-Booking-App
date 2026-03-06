"""
Select court node for booking subgraph.

This module implements the select_court node that handles court selection
in the booking flow with auto-selection support. It checks if court is already
selected, fetches courts for the selected property, auto-selects when only one
court exists, and presents options when multiple courts are available.

Requirements: 7.2, 8.2, 14.1, 14.2, 14.3
"""

from typing import Dict, Any
import logging

from app.agent.state.conversation_state import ConversationState
from app.agent.tools.court_tool import get_property_courts_tool

logger = logging.getLogger(__name__)


async def select_court(
    state: ConversationState,
    tools: Dict[str, Any]
) -> ConversationState:
    """
    Handle court selection in booking flow with auto-selection support.
    
    This node manages the court selection step of the booking process. It:
    1. Checks if court_id already exists in flow_state (skip if exists) - Req 7.2
    2. Fetches courts for selected property using get_property_courts_tool
    3. Handles 0 courts: returns error message
    4. Handles 1 court: auto-selects and stores in flow_state - Req 14.1, 14.2, 14.3
    5. Handles multiple courts: presents list and waits for selection
    6. Updates booking_step to "court_selected" when complete - Req 8.2
    7. Returns next_node decision for routing
    
    Implements Requirements:
    - 7.2: Skip court selection step when Flow_State contains court_id
    - 8.2: Update booking_step field in Flow_State when step is completed
    - 14.1: Auto-select single court and store in Flow_State
    - 14.2: Skip court selection question when auto-selected
    - 14.3: Check number of available courts before asking selection questions
    
    Args:
        state: ConversationState containing user message, flow_state, and identifiers
        tools: Tool registry containing court tools
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          updated flow_state, and next_node decision
        
    Example:
        # Case 1: Court already selected (skip)
        state = {
            "chat_id": "123",
            "flow_state": {"court_id": 1, "court_name": "Court A"},
            ...
        }
        result = await select_court(state, tools)
        # result["next_node"] = "select_date"
        
        # Case 2: Single court (auto-select)
        state = {
            "chat_id": "123",
            "owner_profile_id": "456",
            "flow_state": {"property_id": 1, "property_name": "Sports Center"},
            ...
        }
        result = await select_court(state, tools)
        # result["flow_state"]["court_id"] = 1
        # result["flow_state"]["court_name"] = "Court A"
        # result["flow_state"]["booking_step"] = "court_selected"
        # result["next_node"] = "select_date"
        
        # Case 3: Multiple courts (present options)
        state = {
            "chat_id": "123",
            "owner_profile_id": "456",
            "flow_state": {"property_id": 1, "property_name": "Sports Center"},
            ...
        }
        result = await select_court(state, tools)
        # result["response_type"] = "button"
        # result["response_metadata"]["buttons"] = [...]
        # result["next_node"] = "wait_for_selection"
    """
    chat_id = state["chat_id"]
    owner_profile_id = state.get("owner_profile_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Processing court selection for chat {chat_id} - "
        f"court_id={flow_state.get('court_id')}"
    )
    
    # Step 1: Check if court already selected (Requirement 7.2)
    if flow_state.get("court_id"):
        logger.debug(
            f"Court already selected for chat {chat_id}: "
            f"court_id={flow_state.get('court_id')}, "
            f"court_name={flow_state.get('court_name')}"
        )
        # Court already selected, skip to next step
        state["next_node"] = "select_date"
        return state
    
    # Step 2: Verify property is selected
    property_id = flow_state.get("property_id")
    if not property_id:
        logger.error(
            f"Cannot select court without property_id for chat {chat_id}"
        )
        
        state["response_content"] = (
            "Please select a property first before choosing a court."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "select_property"
        
        return state
    
    # Step 3: Fetch courts for selected property (Requirement 14.3)
    logger.info(
        f"Fetching courts for property_id={property_id} for chat {chat_id}"
    )
    
    try:
        # Fetch courts using the tool
        courts = await get_property_courts_tool(
            property_id=int(property_id),
            owner_id=int(owner_profile_id) if owner_profile_id else None
        )
        
        logger.info(
            f"Fetched {len(courts)} courts for property_id={property_id} "
            f"for chat {chat_id}"
        )
        
    except Exception as e:
        logger.error(
            f"Error fetching courts for property_id={property_id} "
            f"for chat {chat_id}: {e}",
            exc_info=True
        )
        
        # Return error response
        state["response_content"] = (
            "I'm having trouble accessing the courts for this property. "
            "Please try again later."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        return state
    
    # Step 4: Handle different court counts
    court_count = len(courts)
    
    # Case 1: No courts (error)
    if court_count == 0:
        logger.warning(
            f"No courts found for property_id={property_id} for chat {chat_id}"
        )
        
        property_name = flow_state.get("property_name", "this property")
        
        state["response_content"] = (
            f"{property_name} doesn't have any courts available. "
            "Please contact support to add courts to your property."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        return state
    
    # Case 2: Single court (auto-select) - Requirements 14.1, 14.2, 14.3
    elif court_count == 1:
        court = courts[0]
        court_id = court.get("id")
        court_name = court.get("name", "Unknown Court")
        
        # Auto-select and store in flow_state (Requirement 14.1)
        flow_state["court_id"] = court_id
        flow_state["court_name"] = court_name
        flow_state["booking_step"] = "court_selected"  # Requirement 8.2
        state["flow_state"] = flow_state
        
        logger.info(
            f"Auto-selected single court for chat {chat_id}: "
            f"court_id={court_id}, court_name={court_name}"
        )
        
        # Skip court selection question (Requirement 14.2)
        # Proceed directly to date selection
        state["next_node"] = "select_date"
        
        # Optional: Set a message to inform user (can be empty for silent skip)
        state["response_content"] = f"Booking {court_name}."
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Case 3: Multiple courts (present options)
    else:
        logger.info(
            f"Presenting {court_count} court options for chat {chat_id}"
        )
        
        # Format courts as buttons
        buttons = []
        for court in courts:
            court_id = court.get("id")
            court_name = court.get("name", "Unknown Court")
            sport_type = court.get("sport_type", "")
            
            # Include sport type in button text if available
            button_text = f"{court_name}"
            if sport_type:
                button_text += f" ({sport_type})"
            
            buttons.append({
                "id": str(court_id),
                "text": button_text
            })
        
        # Generate response message
        property_name = flow_state.get("property_name", "this property")
        response = f"Which court at {property_name} would you like to book?"
        
        # Update state with response
        state["response_content"] = response
        state["response_type"] = "button"
        state["response_metadata"] = {"buttons": buttons}
        
        # Update flow state to indicate we're waiting for selection
        flow_state["booking_step"] = "awaiting_court_selection"
        state["flow_state"] = flow_state
        
        # Wait for user selection
        state["next_node"] = "wait_for_selection"
        
        return state
