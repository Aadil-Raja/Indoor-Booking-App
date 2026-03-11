"""
Execute actions node - runs the requested information actions.

This node calls backend functions to get property details, court details,
pricing, and media based on requested_actions.
"""

import logging
from typing import Dict, Any, List

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY
from app.agent.utils.llm_logger import get_llm_logger

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
    court_ids = flow_state.get("court_ids", [])
    # Use first court_id since all courts in the array have same details (same sport type)
    court_id = court_ids[0] if court_ids else None
    
    logger.debug(
        f"Executing for chat {chat_id}: "
        f"actions={requested_actions}, property_id={property_id}, court_id={court_id} (from court_ids={court_ids})"
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
                    # Get full property data
                    full_data = await get_property_details(property_id=property_id)
                    
                    # Filter based on property_detail_fields
                    property_detail_fields = flow_state.get("property_detail_fields", ["all"])
                    filtered_data = _filter_property_data(full_data, property_detail_fields)
                    
                    results["property_details"] = {
                        "status": "success",
                        "data": filtered_data,
                        "fields": property_detail_fields
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
                    # Get full court data
                    full_data = await get_court_details(court_id=court_id)
                    
                    # Filter based on court_detail_fields
                    court_detail_fields = flow_state.get("court_detail_fields", ["all"])
                    filtered_data = _filter_court_data(full_data, court_detail_fields)
                    
                    results["court_details"] = {
                        "status": "success",
                        "data": filtered_data,
                        "fields": court_detail_fields
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
    flow_state["pending_action_params"] = {}
    flow_state["requested_actions"] = []
    
    # Track last node
    flow_state["last_node"] = "information-execute_actions"
    state["flow_state"] = flow_state
    
    # Log execution results
    llm_logger = get_llm_logger()
    execution_summary = (
        f"Executed Actions: {list(results.keys())}\n"
        f"Results Summary:\n"
    )
    for action, result in results.items():
        status = result.get("status")
        if status == "success":
            execution_summary += f"  ✓ {action}: Success\n"
        else:
            error = result.get("error", "Unknown error")
            execution_summary += f"  ✗ {action}: Failed - {error}\n"
    
    llm_logger.log_llm_call(
        node_name="execute_actions",
        prompt=f"[No LLM call - executes backend API calls for: {list(results.keys())}]",
        response=execution_summary,
        parameters=None
    )
    
    logger.info(
        f"[EXECUTE ACTIONS] Chat {chat_id}:\n"
        f"  Executed: {list(results.keys())}\n"
        f"  Results: {len(results)} actions completed"
    )
    
    return state


def _filter_property_data(full_data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Filter property data based on requested fields.
    
    Args:
        full_data: Complete property data from service
        fields: List of requested fields (location, contact, amenities, available_courts, description, all)
        
    Returns:
        Filtered property data dictionary
    """
    if not full_data:
        return full_data
    
    # If "all" is requested, return everything
    if "all" in fields:
        return full_data
    
    # Start with basic fields always included
    filtered = {
        "id": full_data.get("id"),
        "name": full_data.get("name"),
    }
    
    # Add fields based on request
    for field in fields:
        if field == "location":
            filtered["address"] = full_data.get("address")
            filtered["city"] = full_data.get("city")
            filtered["state"] = full_data.get("state")
            filtered["country"] = full_data.get("country")
            filtered["maps_link"] = full_data.get("maps_link")
        
        elif field == "contact":
            filtered["phone"] = full_data.get("phone")
            filtered["email"] = full_data.get("email")
        
        elif field == "amenities":
            filtered["amenities"] = full_data.get("amenities")
        
        elif field == "available_courts":
            filtered["courts"] = full_data.get("courts")
        
        elif field == "description":
            filtered["description"] = full_data.get("description")
    
    return filtered


def _filter_court_data(full_data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Filter court data based on requested fields.
    
    Args:
        full_data: Complete court data from service
        fields: List of requested fields (basic, pricing, all)
        
    Returns:
        Filtered court data dictionary with formatted pricing
    """
    if not full_data:
        return full_data
    
    # Start with basic fields always included
    filtered = {
        "id": full_data.get("id"),
        "name": full_data.get("name"),
    }
    
    # If "all" is requested, include basic + pricing
    if "all" in fields:
        fields = ["basic", "pricing"]
    
    # Add fields based on request
    for field in fields:
        if field == "basic":
            filtered["sport_types"] = full_data.get("sport_types")
            filtered["description"] = full_data.get("description")
            filtered["specifications"] = full_data.get("specifications")
            filtered["amenities"] = full_data.get("amenities")
        
        elif field == "pricing":
            # Format pricing rules nicely
            pricing_rules = full_data.get("pricing_rules", [])
            filtered["pricing"] = _format_pricing_rules(pricing_rules)
            filtered["base_price"] = full_data.get("base_price")
    
    return filtered


def _format_pricing_rules(pricing_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format pricing rules for better readability.
    
    Args:
        pricing_rules: Raw pricing rules from service
        
    Returns:
        Formatted pricing rules with readable day names and times
    """
    if not pricing_rules:
        return []
    
    DAY_NAMES = {
        0: "Monday",     # Fix: Day 0 is Monday
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }
    
    formatted_rules = []
    for rule in pricing_rules:
        # Convert day numbers to names
        days = rule.get("days", [])
        day_names = [DAY_NAMES.get(d, f"Day{d}") for d in days]
        
        # Format day range
        if len(day_names) == 7:
            day_str = "Every day"
        elif len(day_names) == 5 and set(days) == {0, 1, 2, 3, 4}:
            day_str = "Weekdays (Mon-Fri)"
        elif len(day_names) == 2 and set(days) == {5, 6}:
            day_str = "Weekends (Sat-Sun)"
        elif len(day_names) > 0:
            day_str = ", ".join(day_names)
        else:
            day_str = "No days specified"
        
        # Format times (remove seconds)
        start_time = rule.get("start_time", "")
        end_time = rule.get("end_time", "")
        if isinstance(start_time, str) and len(start_time) > 5:
            start_time = start_time[:5]  # "09:00:00" → "09:00"
        if isinstance(end_time, str) and len(end_time) > 5:
            end_time = end_time[:5]  # "17:00:00" → "17:00"
        
        formatted_rules.append({
            "label": rule.get("label", "Standard Rate"),
            "days": day_str,
            "time": f"{start_time} - {end_time}",
            "price_per_hour": rule.get("price_per_hour"),
            "formatted": f"{day_str}, {start_time}-{end_time}: PKR {rule.get('price_per_hour', 0)}/hour"
        })
    
    return formatted_rules
