"""
Execute actions node - runs the requested information actions.

This node calls backend functions to get property details, court details,
pricing, and media based on requested_actions.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def execute_actions(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Execute requested information actions.
    
    This node:
    1. Reads requested_actions from flow_state
    2. Reads property_id and court_id
    3. Calls appropriate backend functions for each action
    4. Collects results
    5. Stores results in flow_state for format_response
    6. Clears awaiting_input and pending_actions
    
    Args:
        state: Current conversation state
        tools: Tool registry for calling backend functions
        
    Returns:
        Updated state with execution results
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Executing actions for chat {chat_id}")
    
    # Get state
    requested_actions = flow_state.get("requested_actions", [])
    property_id = flow_state.get("property_id")
    court_id = flow_state.get("court_id")
    
    logger.debug(
        f"Executing for chat {chat_id}: "
        f"actions={requested_actions}, property_id={property_id}, court_id={court_id}"
    )
    
    # Results dictionary
    results = {}
    
    # Execute each action
    for action in requested_actions:
        try:
            if action == "property_details":
                # Call get_property_details tool
                get_property_details = TOOL_REGISTRY.get("get_property_details")
                if get_property_details and property_id:
                    data = await get_property_details(property_id=property_id)
                    results["property_details"] = {
                        "status": "success",
                        "data": data
                    }
                else:
                    results["property_details"] = {
                        "status": "error",
                        "error": "Property details tool not found or property_id missing"
                    }
                
            elif action == "court_details":
                # Call get_court_details tool
                get_court_details = TOOL_REGISTRY.get("get_court_details")
                if get_court_details and court_id:
                    data = await get_court_details(court_id=court_id)
                    results["court_details"] = {
                        "status": "success",
                        "data": data
                    }
                else:
                    results["court_details"] = {
                        "status": "error",
                        "error": "Court details tool not found or court_id missing"
                    }
                
            elif action == "pricing":
                # Call get_court_pricing tool
                get_court_pricing = TOOL_REGISTRY.get("get_court_pricing")
                if get_court_pricing and court_id:
                    data = await get_court_pricing(court_id=court_id)
                    results["pricing"] = {
                        "status": "success",
                        "data": data
                    }
                else:
                    results["pricing"] = {
                        "status": "error",
                        "error": "Pricing tool not found or court_id missing"
                    }
                
            elif action == "media":
                # For media, use court_details which includes media
                get_court_details = TOOL_REGISTRY.get("get_court_details")
                if get_court_details and court_id:
                    data = await get_court_details(court_id=court_id)
                    if data and "media" in data:
                        results["media"] = {
                            "status": "success",
                            "data": data["media"]
                        }
                    else:
                        results["media"] = {
                            "status": "success",
                            "data": []
                        }
                else:
                    results["media"] = {
                        "status": "error",
                        "error": "Media tool not found or court_id missing"
                    }
                
        except Exception as e:
            logger.error(f"Error executing action {action} for chat {chat_id}: {e}")
            results[action] = {
                "status": "error",
                "error": str(e)
            }
    
    # Store results
    flow_state["execution_results"] = results
    
    # Clear state after successful execution
    flow_state["awaiting_input"] = None
    flow_state["pending_actions"] = []
    flow_state["requested_actions"] = []
    
    # Track last node
    flow_state["last_node"] = "information-execute_actions"
    state["flow_state"] = flow_state
    
    logger.info(
        f"[EXECUTE ACTIONS] Chat {chat_id}:\n"
        f"  Executed: {list(results.keys())}\n"
        f"  Results: {len(results)} actions completed"
    )
    
    return state
