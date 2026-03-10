"""
Intent detection node - uses LLM to decide routing.

Simple routing only:
- "greeting" for greetings
- "information" for questions
- "booking" for reservations
- "unavailable_service" for service unavailability cases
"""

from typing import Optional
import logging

from langchain_core.messages import HumanMessage

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.intent_prompts import get_routing_prompt
from app.agent.utils.llm_logger import get_llm_logger
from app.agent.utils.json_parser import parse_llm_json_response, extract_json_field
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Use LLM to decide routing (greeting/information/booking/unavailable_service).
    
    Uses conversation context for better routing of ambiguous messages.
    Falls back to "greeting" if LLM fails.
    
    New users (owner_properties not initialized) are forced to greeting.
    
    Service availability checks:
    - If owner has no properties → route to unavailable_service
    - If property has no courts → route to unavailable_service
    """
    user_message = state["user_message"]
    recent_messages = state.get("messages", [])
    flow_state = state.get("flow_state", {})
    owner_profile_id = state["owner_profile_id"]
    chat_id = state["chat_id"]
    
    logger.info(
        f"Determining routing for chat {chat_id} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if owner_properties have been initialized
    owner_properties_initialized = flow_state.get("owner_properties_initialized", False)
    
    if not owner_properties_initialized:
        # New user - force to greeting to initialize properties
        logger.info(
            f"New user detected (owner_properties not initialized) for chat {chat_id}, "
            f"forcing route to greeting"
        )
        state["next_node"] = "greeting"
        state["is_first_message"] = True
        return state
    
    # Check service availability before routing
    availability_check = await _check_service_availability(
        owner_profile_id=owner_profile_id,
        flow_state=flow_state,
        chat_id=chat_id
    )
    
    if not availability_check["available"]:
        # Service unavailable - route to unavailable_service node
        logger.info(
            f"Service unavailable for chat {chat_id} - "
            f"reason={availability_check['reason']}, routing to unavailable_service"
        )
        
        # Set unavailability details in flow_state
        flow_state["unavailable_reason"] = availability_check["reason"]
        if availability_check.get("property_name"):
            flow_state["property_name"] = availability_check["property_name"]
        
        state["flow_state"] = flow_state
        state["next_node"] = "unavailable_service"
        return state
    
    # Service available - use LLM for routing decision
    if llm_provider:
        next_node = await _llm_routing_decision(
            user_message=user_message,
            recent_messages=recent_messages,
            last_node=flow_state.get("last_node"),
            llm_provider=llm_provider,
            chat_id=chat_id
        )
    else:
        logger.warning(
            f"No LLM provider, defaulting to greeting for chat {chat_id}"
        )
        next_node = "greeting"
    
    # Store next_node for graph routing
    state["next_node"] = next_node
    
    logger.info(f"Routing decision for chat {chat_id}: next_node={next_node}")
    
    return state


async def _llm_routing_decision(
    user_message: str,
    recent_messages: list,
    last_node: str,
    llm_provider: LLMProvider,
    chat_id: str
) -> str:
    """
    Call LLM to get routing decision with conversation context.
    
    Returns: next_node ("greeting" | "information" | "booking")
    Defaults to "greeting" if LLM fails.
    """
    # Get formatted prompt with context
    prompt = get_routing_prompt(
        message=user_message,
        recent_messages=recent_messages,
        last_node=last_node
    )
    
    # Get LLM logger
    llm_logger = get_llm_logger()
    
    try:
        # Create LangChain ChatOpenAI instance
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.0,  # Consistent routing
            max_tokens=50     # Just need the node name
        )
        
        # Call LLM
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        response_content = response.content.strip()
        
        # Log the LLM call
        llm_logger.log_llm_call(
            node_name="intent_detection",
            prompt=prompt,
            response=response_content,
            parameters={"temperature": 0.0, "max_tokens": 50}
        )
        
        # Parse JSON response using utility function
        llm_response = parse_llm_json_response(
            response=response_content,
            fallback={"next_node": "greeting"},
            context=f"intent_detection for chat {chat_id}"
        )
        
        # Extract next_node with validation
        next_node = extract_json_field(
            parsed_json=llm_response,
            field="next_node",
            default="greeting",
            field_type=str
        )
        
        # Validate next_node
        valid_nodes = ["greeting", "information", "booking"]
        if next_node not in valid_nodes:
            logger.warning(
                f"Invalid next_node '{next_node}' for chat {chat_id}, "
                f"defaulting to greeting"
            )
            return "greeting"
        
        logger.info(f"LLM routing for chat {chat_id}: next_node={next_node}")
        return next_node
            
    except LLMProviderError as e:
        logger.error(f"LLM routing failed for chat {chat_id}: {e}", exc_info=True)
        return "greeting"
    except Exception as e:
        logger.error(f"Unexpected error for chat {chat_id}: {e}", exc_info=True)
        return "greeting"



async def _check_service_availability(
    owner_profile_id: str,
    flow_state: dict,
    chat_id: str
) -> dict:
    """
    Check if service is available for the owner.
    
    Checks two conditions:
    1. Owner has properties in the system
    2. Properties have courts available
    
    Uses cached properties from flow_state if available, otherwise fetches fresh.
    
    Args:
        owner_profile_id: Owner profile ID as string
        flow_state: Flow state containing cached properties
        chat_id: Chat ID for logging
    
    Returns:
        Dictionary with:
        - available: bool (True if service available)
        - reason: str (unavailability reason if not available)
        - property_name: str (optional, property name if no courts)
    """
    try:
        # Get cached properties from flow_state
        properties = flow_state.get("available_properties", [])
        
        # If not cached, fetch fresh
        if not properties:
            logger.info(f"Properties not cached, fetching for chat {chat_id}")
            properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        
        # Check 1: Does owner have any properties?
        if not properties or len(properties) == 0:
            logger.warning(f"No properties found for owner {owner_profile_id} in chat {chat_id}")
            return {
                "available": False,
                "reason": "no_properties"
            }
        
        # Check 2: Do properties have courts?
        # Get the selected property or default to first property
        selected_property_id = flow_state.get("selected_property_id")
        
        if selected_property_id:
            # Check specific property
            property_to_check = next(
                (p for p in properties if p.get("id") == selected_property_id),
                None
            )
            if property_to_check:
                has_courts = await _check_property_has_courts(
                    property_id=selected_property_id,
                    owner_profile_id=owner_profile_id,
                    chat_id=chat_id
                )
                if not has_courts:
                    logger.warning(
                        f"Property {selected_property_id} has no courts for chat {chat_id}"
                    )
                    return {
                        "available": False,
                        "reason": "no_courts",
                        "property_name": property_to_check.get("name")
                    }
        else:
            # Check if ANY property has courts
            any_property_has_courts = False
            for prop in properties:
                prop_id = prop.get("id")
                if prop_id:
                    has_courts = await _check_property_has_courts(
                        property_id=prop_id,
                        owner_profile_id=owner_profile_id,
                        chat_id=chat_id
                    )
                    if has_courts:
                        any_property_has_courts = True
                        break
            
            if not any_property_has_courts:
                logger.warning(f"No properties have courts for owner {owner_profile_id} in chat {chat_id}")
                # Use first property name for message
                first_property_name = properties[0].get("name") if properties else None
                return {
                    "available": False,
                    "reason": "no_courts",
                    "property_name": first_property_name
                }
        
        # All checks passed - service is available
        logger.info(f"Service available for chat {chat_id}")
        return {"available": True}
        
    except Exception as e:
        logger.error(
            f"Error checking service availability for chat {chat_id}: {e}",
            exc_info=True
        )
        # On error, assume service is available to avoid blocking users
        return {"available": True}


async def _fetch_owner_properties(owner_profile_id: str, chat_id: str) -> list:
    """
    Fetch owner properties using tool registry.
    
    Args:
        owner_profile_id: Owner profile ID as string
        chat_id: Chat ID for logging
    
    Returns:
        List of property dictionaries, or empty list on error
    """
    try:
        # Validate owner_profile_id
        try:
            owner_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return []
        
        # Get the property tool from registry
        get_owner_properties = TOOL_REGISTRY.get("get_owner_properties")
        
        if not get_owner_properties:
            logger.warning(f"get_owner_properties tool not found for chat {chat_id}")
            return []
        
        # Fetch properties with error handling
        properties = await get_owner_properties(owner_profile_id=owner_id)
        
        if not isinstance(properties, list):
            logger.warning(
                f"get_owner_properties returned non-list for chat {chat_id}: {type(properties)}"
            )
            return []
        
        logger.info(f"Fetched {len(properties)} properties for chat {chat_id}")
        return properties
        
    except Exception as e:
        logger.error(f"Error fetching owner properties for chat {chat_id}: {e}", exc_info=True)
        return []


async def _check_property_has_courts(
    property_id: int,
    owner_profile_id: str,
    chat_id: str
) -> bool:
    """
    Check if a property has any courts available.
    
    Args:
        property_id: Property ID to check
        owner_profile_id: Owner profile ID as string
        chat_id: Chat ID for logging
    
    Returns:
        True if property has courts, False otherwise
    """
    try:
        # Validate owner_profile_id
        try:
            owner_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return False
        
        # Get the court tool from registry
        get_property_courts = TOOL_REGISTRY.get("get_property_courts")
        
        if not get_property_courts:
            logger.warning(f"get_property_courts tool not found for chat {chat_id}")
            return False
        
        # Fetch courts for property
        courts = await get_property_courts(property_id=property_id, owner_id=owner_id)
        
        if not isinstance(courts, list):
            logger.warning(
                f"get_property_courts returned non-list for property {property_id} "
                f"in chat {chat_id}: {type(courts)}"
            )
            return False
        
        has_courts = len(courts) > 0
        logger.debug(
            f"Property {property_id} has {len(courts)} courts for chat {chat_id}"
        )
        
        return has_courts
        
    except Exception as e:
        logger.error(
            f"Error checking courts for property {property_id} in chat {chat_id}: {e}",
            exc_info=True
        )
        return False
