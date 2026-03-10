"""
Unavailable service handler - handles cases where service cannot be provided.

This node handles two main scenarios:
1. No properties available (owner has no facilities in system)
2. Property exists but has no courts available

Provides contextual, friendly messages to guide users appropriately.

Requirements: 1.1, 2.1
"""

from typing import Optional
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def unavailable_service_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle cases where service is unavailable.
    
    This node is reached when:
    - Owner has no properties in the system
    - Owner has a property but it has no courts configured
    
    Provides contextual messages based on the specific unavailability reason,
    personalized with business_name and property_name where applicable.
    
    Args:
        state: ConversationState containing flow_state with unavailability info
        llm_provider: Optional LLMProvider (not used in this node)
    
    Returns:
        ConversationState with appropriate unavailability message
    """
    # 1. Extract state
    chat_id = state["chat_id"]
    owner_profile_id = state["owner_profile_id"]
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Processing unavailable service for chat {chat_id}")
    
    # 2. Get unavailability details
    unavailable_reason = flow_state.get("unavailable_reason", "unknown")
    property_name = flow_state.get("property_name")
    
    # 3. Fetch owner profile for business_name
    owner_profile = await _fetch_owner_profile(owner_profile_id, chat_id)
    business_name = owner_profile.get("business_name") or "our facility"
    
    # 4. Generate appropriate message based on reason
    if unavailable_reason == "no_properties":
        response = _generate_no_properties_message(business_name)
        logger.info(f"Generated no properties message for chat {chat_id}")
    elif unavailable_reason == "no_courts":
        response = _generate_no_courts_message(business_name, property_name)
        logger.info(f"Generated no courts message for chat {chat_id} - "
                   f"property={property_name}")
    else:
        # Fallback for unknown reasons
        response = _generate_generic_unavailable_message(business_name)
        logger.warning(f"Unknown unavailable reason '{unavailable_reason}' for chat {chat_id}, "
                      f"using generic message")
    
    # 5. Set response in state
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {
        "service_unavailable": True,
        "reason": unavailable_reason
    }
    
    # 6. Track last node
    state["flow_state"]["last_node"] = "unavailable_service"
    
    logger.info(f"Unavailable service handler completed for chat {chat_id} - "
               f"reason={unavailable_reason}")
    
    return state


def _generate_no_properties_message(business_name: str) -> str:
    """
    Generate message when owner has no properties in system.
    
    This is shown when the owner profile exists but has no properties
    configured. Provides helpful guidance for users to check back later.
    
    Args:
        business_name: Name of the business for personalization
    
    Returns:
        Formatted message string
    """
    return (
        f"Hello! I am {business_name}'s assistant.\n\n"
        "We currently don't have any facilities available in our system.\n\n"
        "Please check back later or contact us directly for more information.\n"
        "We apologize for the inconvenience!"
    )


def _generate_no_courts_message(business_name: str, property_name: Optional[str]) -> str:
    """
    Generate message when property exists but has no courts.
    
    This is shown when a property is configured but has no courts available
    for booking. Uses property_name if available for personalization.
    
    Args:
        business_name: Name of the business for personalization
        property_name: Name of the property (optional)
    
    Returns:
        Formatted message string
    """
    # Use property_name if available, otherwise use business_name
    assistant_name = property_name if property_name else business_name
    
    return (
        f"Hello! I am {assistant_name}'s assistant.\n\n"
        "We currently don't have any courts available for booking.\n\n"
        "Please check back later or contact us for updates.\n"
        "Thank you for your patience!"
    )


def _generate_generic_unavailable_message(business_name: str) -> str:
    """
    Generate generic unavailable message for unknown cases.
    
    Fallback message when the specific unavailability reason is not recognized.
    
    Args:
        business_name: Name of the business for personalization
    
    Returns:
        Formatted message string
    """
    return (
        f"Hello! I am {business_name}'s assistant.\n\n"
        "Our booking service is temporarily unavailable.\n\n"
        "Please check back later or contact us directly for assistance.\n"
        "We apologize for the inconvenience!"
    )


async def _fetch_owner_profile(owner_profile_id: str, chat_id: str) -> dict:
    """
    Fetch owner profile for business_name.
    
    Uses the get_owner_profile tool from TOOL_REGISTRY to fetch
    owner profile data including business_name for personalization.
    
    Args:
        owner_profile_id: Owner profile ID as string
        chat_id: Chat ID for logging
    
    Returns:
        Dictionary with owner profile data, or default dict on error
    """
    try:
        # Validate owner_profile_id
        try:
            profile_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return {"business_name": "our facility"}  # Default fallback
        
        # Get the owner profile tool from registry
        get_owner_profile = TOOL_REGISTRY.get("get_owner_profile")
        if not get_owner_profile:
            logger.warning(f"get_owner_profile tool not found for chat {chat_id}")
            return {"business_name": "our facility"}
        
        # Fetch profile using tool
        profile_data = await get_owner_profile(owner_profile_id=profile_id)
        
        logger.info(f"Fetched owner profile for unavailable service - "
                   f"owner_profile_id={owner_profile_id}, chat={chat_id}")
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Error fetching owner profile for unavailable service in chat {chat_id}: {e}",
                    exc_info=True)
        return {"business_name": "our facility"}  # Fallback on error
