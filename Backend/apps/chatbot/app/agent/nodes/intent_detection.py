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
    
    Validation layers (in order):
    1. Message format validation (length, emojis, spam)
    2. Service availability check (properties/courts)
    3. Message relevancy check (LLM)
    4. Intent routing decision (LLM)
    
    New users (owner_properties not initialized) are forced to greeting.
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
    
    # Layer 1: Quick message format validation (no LLM)
    validation_result = _validate_message_format(user_message)
    if not validation_result["valid"]:
        logger.info(
            f"Message validation failed for chat {chat_id} - "
            f"reason={validation_result['reason']}"
        )
        state["response_content"] = validation_result["message"]
        state["response_type"] = "text"
        state["response_metadata"] = {
            "validation_failed": True,
            "reason": validation_result["reason"]
        }
        state["next_node"] = None  # Don't route anywhere, end conversation
        return state
    
    # Layer 2: Service availability check (API calls)
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
    
    # Layer 3: Message relevancy check (LLM, unless conversational response)
    if _is_conversational_response(user_message):
        # Skip relevancy check for short conversational responses
        logger.debug(f"Conversational response detected for chat {chat_id}, skipping relevancy check")
    else:
        # Check message relevancy with LLM
        if llm_provider:
            relevancy_result = await _check_message_relevancy(
                user_message=user_message,
                recent_messages=recent_messages,
                llm_provider=llm_provider,
                chat_id=chat_id
            )
            
            if not relevancy_result["is_relevant"]:
                logger.info(
                    f"Message deemed irrelevant for chat {chat_id} - "
                    f"reason={relevancy_result.get('reason', 'unknown')}"
                )
                state["response_content"] = _generate_irrelevant_response()
                state["response_type"] = "text"
                state["response_metadata"] = {
                    "irrelevant_message": True,
                    "reason": relevancy_result.get("reason", "out_of_scope")
                }
                state["next_node"] = None  # Don't route anywhere
                return state
    
    # Layer 4: LLM routing decision (greeting/information/booking)
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


def _validate_message_format(user_message: str) -> dict:
    """
    Validate message format with quick checks (no LLM).
    
    Checks:
    1. Empty or whitespace only
    2. Too short (≤2 characters, excluding conversational responses)
    3. Only emojis
    4. Too long (>300 characters)
    5. Spam patterns (repeated characters)
    
    Args:
        user_message: User's message to validate
    
    Returns:
        Dictionary with:
        - valid: bool (True if valid)
        - reason: str (failure reason if not valid)
        - message: str (response message if not valid)
    """
    # 1. Empty or whitespace only
    if not user_message or not user_message.strip():
        return {
            "valid": False,
            "reason": "empty_message",
            "message": "Please send a message so I can assist you with booking a court."
        }
    
    cleaned_message = user_message.strip()
    
    # 2. Too short (≤2 characters, but allow conversational responses)
    if len(cleaned_message) <= 2 and not _is_conversational_response(user_message):
        return {
            "valid": False,
            "reason": "too_short",
            "message": "Your message is too short. Please describe what you need help with."
        }
    
    # 3. Only emojis
    if _is_only_emojis(cleaned_message):
        return {
            "valid": False,
            "reason": "only_emojis",
            "message": "I see you sent an emoji! 😊 How can I help you with booking a court today?"
        }
    
    # 4. Too long (>300 characters)
    if len(cleaned_message) > 300:
        return {
            "valid": False,
            "reason": "too_long",
            "message": "Your message is too long. Please send a shorter message (under 300 characters)."
        }
    
    # 5. Spam patterns (repeated characters)
    if _is_spam_pattern(cleaned_message):
        return {
            "valid": False,
            "reason": "spam_pattern",
            "message": "Please send a clear message about what you'd like to do."
        }
    
    # All checks passed
    return {"valid": True}


def _is_conversational_response(message: str) -> bool:
    """
    Check if message is a short conversational response.
    
    These responses are context-dependent (responding to bot's previous message)
    and should bypass relevancy checks.
    
    Args:
        message: User's message
    
    Returns:
        True if conversational response, False otherwise
    """
    conversational_responses = {
        "ok", "okay", "thanks", "thank you", "yes", "no", "sure",
        "got it", "alright", "fine", "cool", "great", "nope", "yep",
        "yeah", "nah", "k", "ty", "thx", "please", "pls"
    }
    
    cleaned = message.strip().lower()
    return cleaned in conversational_responses


def _is_only_emojis(message: str) -> bool:
    """
    Check if message contains only emojis (and whitespace).
    
    Args:
        message: User's message
    
    Returns:
        True if only emojis, False otherwise
    """
    import re
    
    # Remove whitespace
    no_whitespace = message.replace(" ", "").replace("\n", "").replace("\t", "")
    
    if not no_whitespace:
        return False
    
    # Emoji pattern (basic Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    # Check if entire message (without whitespace) is emojis
    return bool(emoji_pattern.fullmatch(no_whitespace))


def _is_spam_pattern(message: str) -> bool:
    """
    Check if message contains spam patterns (repeated characters).
    
    Args:
        message: User's message
    
    Returns:
        True if spam pattern detected, False otherwise
    """
    import re
    
    # Check for 5+ repeated characters (e.g., "aaaaa", "!!!!!")
    repeated_char_pattern = re.compile(r"(.)\1{4,}")
    if repeated_char_pattern.search(message):
        return True
    
    # Check for 3+ repeated words (e.g., "help help help help")
    words = message.lower().split()
    if len(words) >= 3:
        for i in range(len(words) - 2):
            if words[i] == words[i+1] == words[i+2]:
                return True
    
    return False


def _generate_irrelevant_response() -> str:
    """
    Generate response for irrelevant messages.
    
    Returns:
        Polite message explaining scope and offering help
    """
    return (
        "I'm an indoor sports facility booking assistant. "
        "I can help you with:\n\n"
        "• Booking courts (tennis, badminton, basketball, etc.)\n"
        "• Checking availability and pricing\n"
        "• Information about our facilities\n"
        "• Managing your bookings\n\n"
        "How can I assist you with booking today?"
    )


async def _check_message_relevancy(
    user_message: str,
    recent_messages: list,
    llm_provider: LLMProvider,
    chat_id: str
) -> dict:
    """
    Check if user message is relevant to indoor booking using LLM.
    
    Uses a focused prompt to determine if the message is within scope
    of indoor sports facility booking services.
    
    Args:
        user_message: User's message to check
        recent_messages: Recent conversation history (for context)
        llm_provider: LLM provider for relevancy check
        chat_id: Chat ID for logging
    
    Returns:
        Dictionary with:
        - is_relevant: bool (True if relevant)
        - reason: str (explanation from LLM)
    """
    from app.agent.prompts.intent_prompts import get_relevancy_check_prompt
    
    # Get formatted prompt with context (only last 2 messages for efficiency)
    prompt = get_relevancy_check_prompt(
        message=user_message,
        recent_messages=recent_messages[-2:] if recent_messages else []
    )
    
    # Get LLM logger
    llm_logger = get_llm_logger()
    
    try:
        # Create LangChain ChatOpenAI instance
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.0,  # Consistent relevancy checking
            max_tokens=100    # Just need is_relevant + brief reason
        )
        
        # Call LLM
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        response_content = response.content.strip()
        
        # Log the LLM call
        llm_logger.log_llm_call(
            node_name="intent_detection_relevancy",
            prompt=prompt,
            response=response_content,
            parameters={"temperature": 0.0, "max_tokens": 100}
        )
        
        # Parse JSON response
        relevancy_response = parse_llm_json_response(
            response=response_content,
            fallback={"is_relevant": True, "reason": "parse_error"},
            context=f"relevancy_check for chat {chat_id}"
        )
        
        # Extract is_relevant field
        is_relevant = extract_json_field(
            parsed_json=relevancy_response,
            field="is_relevant",
            default=True,  # Default to relevant on error (avoid false positives)
            field_type=bool
        )
        
        reason = relevancy_response.get("reason", "")
        
        logger.info(
            f"Relevancy check for chat {chat_id}: is_relevant={is_relevant}, "
            f"reason={reason}"
        )
        
        return {
            "is_relevant": is_relevant,
            "reason": reason
        }
        
    except LLMProviderError as e:
        logger.error(f"LLM relevancy check failed for chat {chat_id}: {e}", exc_info=True)
        # Default to relevant on error to avoid blocking users
        return {"is_relevant": True, "reason": "llm_error"}
    except Exception as e:
        logger.error(f"Unexpected error in relevancy check for chat {chat_id}: {e}", exc_info=True)
        return {"is_relevant": True, "reason": "unexpected_error"}



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
        owner_profile_id: Owner profile ID as string (not used, kept for signature)
        chat_id: Chat ID for logging
    
    Returns:
        True if property has courts, False otherwise
    """
    try:
        # Get the court tool from registry
        get_property_courts = TOOL_REGISTRY.get("get_property_courts")
        
        if not get_property_courts:
            logger.warning(f"get_property_courts tool not found for chat {chat_id}")
            return False
        
        # Fetch courts for property (without owner_id to use public service)
        courts = await get_property_courts(property_id=property_id)
        
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
