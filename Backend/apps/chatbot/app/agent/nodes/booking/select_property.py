"""
Select property node for booking subgraph.

This module implements the select_property node that handles property selection
in the booking flow with auto-selection support. It checks if property is already
selected, fetches owner properties on-demand, auto-selects when only one property
exists, and presents options when multiple properties are available.

Requirements: 5.2, 5.3, 6.1, 6.2, 6.4, 7.1, 8.2
"""

from typing import Dict, Any
import logging

from app.agent.state.conversation_state import ConversationState
from app.agent.tools.property_tool import get_owner_properties_tool
from app.agent.nodes.booking.flow_validation import (
    should_skip_to_next_step,
    get_booking_progress_summary
)

logger = logging.getLogger(__name__)


async def select_property(
    state: ConversationState,
    tools: Dict[str, Any]
) -> ConversationState:
    """
    Handle property selection in booking flow with auto-selection support.
    
    This node manages the property selection step of the booking process. It:
    1. Checks if property_id already exists in flow_state (skip if exists) - Req 7.1
    2. Fetches owner_properties if not cached in flow_state - Req 5.2, 5.3
    3. Handles 0 properties: returns error message
    4. Handles 1 property: auto-selects and stores in flow_state - Req 6.1, 6.2, 6.4
    5. Handles multiple properties: presents list and waits for selection
    6. Updates booking_step to "property_selected" when complete - Req 8.2
    7. Returns next_node decision for routing
    
    Implements Requirements:
    - 5.2: Fetch Owner_Properties when booking intent is determined
    - 5.3: Cache Owner_Properties in Flow_State
    - 6.1: Auto-select single property and store in Flow_State
    - 6.2: Skip property selection question when auto-selected
    - 6.4: Check Flow_State for existing property_id before asking
    - 7.1: Skip property selection step when Flow_State contains property_id
    - 8.2: Update booking_step field in Flow_State when step is completed
    
    Args:
        state: ConversationState containing user message, flow_state, and identifiers
        tools: Tool registry containing property tools
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          updated flow_state, and next_node decision
        
    Example:
        # Case 1: Property already selected (skip)
        state = {
            "chat_id": "123",
            "flow_state": {"property_id": 1, "property_name": "Sports Center"},
            ...
        }
        result = await select_property(state, tools)
        # result["next_node"] = "select_court"
        
        # Case 2: Single property (auto-select)
        state = {
            "chat_id": "123",
            "owner_profile_id": "456",
            "flow_state": {},
            ...
        }
        result = await select_property(state, tools)
        # result["flow_state"]["property_id"] = 1
        # result["flow_state"]["property_name"] = "Sports Center"
        # result["flow_state"]["booking_step"] = "property_selected"
        # result["next_node"] = "select_court"
        
        # Case 3: Multiple properties (present options)
        state = {
            "chat_id": "123",
            "owner_profile_id": "456",
            "flow_state": {},
            ...
        }
        result = await select_property(state, tools)
        # result["response_type"] = "button"
        # result["response_metadata"]["buttons"] = [...]
        # result["next_node"] = "wait_for_selection"
    """
    chat_id = state["chat_id"]
    owner_profile_id = state.get("owner_profile_id")
    flow_state = state.get("flow_state", {})
    
    # Log booking progress for debugging
    progress = get_booking_progress_summary(flow_state)
    logger.info(
        f"Processing property selection for chat {chat_id} - "
        f"progress={progress['completion_percentage']}%, "
        f"next_step={progress['next_step']}"
    )
    
    # Step 1: Check if property already selected (Requirement 7.1, 7.5, 7.6)
    should_skip, next_node = should_skip_to_next_step("select_property", flow_state)
    if should_skip:
        logger.debug(
            f"Property already selected for chat {chat_id}: "
            f"property_id={flow_state.get('property_id')}, "
            f"property_name={flow_state.get('property_name')}, "
            f"skipping to {next_node}"
        )
        # Property already selected, skip to next step
        state["next_node"] = next_node
        return state
    
    # Step 2: Fetch owner_properties if not cached (Requirements 5.2, 5.3)
    owner_properties = flow_state.get("owner_properties")
    
    if not owner_properties:
        logger.info(
            f"Fetching owner properties for chat {chat_id}: "
            f"owner_profile_id={owner_profile_id}"
        )
        
        try:
            # Fetch properties using the tool
            owner_properties = await get_owner_properties_tool(
                owner_profile_id=int(owner_profile_id)
            )
            
            # Cache in flow_state for future use (Requirement 5.3)
            flow_state["owner_properties"] = owner_properties
            state["flow_state"] = flow_state
            
            logger.info(
                f"Fetched and cached {len(owner_properties)} properties "
                f"in flow_state for chat {chat_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching owner properties for chat {chat_id}: {e}",
                exc_info=True
            )
            
            # Return error response
            state["response_content"] = (
                "I'm having trouble accessing your properties. "
                "Please try again later."
            )
            state["response_type"] = "text"
            state["response_metadata"] = {}
            state["next_node"] = "end"
            
            return state
    else:
        logger.debug(
            f"Using cached properties from flow_state for chat {chat_id}: "
            f"{len(owner_properties)} properties"
        )
    
    # Step 3: Handle different property counts
    property_count = len(owner_properties)
    
    # Case 1: No properties (error)
    if property_count == 0:
        logger.warning(f"No properties found for chat {chat_id}")
        
        state["response_content"] = (
            "You don't have any properties set up yet. "
            "Please add a property before making a booking."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "end"
        
        return state
    
    # Case 2: Single property (auto-select) - Requirements 6.1, 6.2, 6.4
    elif property_count == 1:
        property = owner_properties[0]
        property_id = property.get("id")
        property_name = property.get("name", "Unknown Property")
        
        # Auto-select and store in flow_state (Requirement 6.1)
        flow_state["property_id"] = property_id
        flow_state["property_name"] = property_name
        flow_state["booking_step"] = "property_selected"  # Requirement 8.2
        state["flow_state"] = flow_state
        
        logger.info(
            f"Auto-selected single property for chat {chat_id}: "
            f"property_id={property_id}, property_name={property_name}"
        )
        
        # Skip property selection question (Requirement 6.2)
        # Proceed directly to court selection
        state["next_node"] = "select_court"
        
        # Optional: Set a message to inform user (can be empty for silent skip)
        state["response_content"] = f"Booking for {property_name}."
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Case 3: Multiple properties (present options)
    else:
        logger.info(
            f"Presenting {property_count} property options for chat {chat_id}"
        )
        
        # Format properties as buttons
        buttons = []
        for prop in owner_properties:
            property_id = prop.get("id")
            property_name = prop.get("name", "Unknown Property")
            
            buttons.append({
                "id": str(property_id),
                "text": property_name
            })
        
        # Generate response message
        response = "Which facility would you like to book?"
        
        # Update state with response
        state["response_content"] = response
        state["response_type"] = "button"
        state["response_metadata"] = {"buttons": buttons}
        
        # Update flow state to indicate we're waiting for selection
        flow_state["booking_step"] = "awaiting_property_selection"
        state["flow_state"] = flow_state
        
        # Wait for user selection
        state["next_node"] = "wait_for_selection"
        
        return state
