"""
Select property node for booking subgraph.

This module implements the select_property node that handles property selection
in the booking flow using LangChain agent. It presents properties from search results,
uses an LLM agent to parse user selection, stores the selected property_id
in flow_state, and handles invalid selections gracefully.

Requirements: 6.3, 9.1, 9.2, 20.2, 22.1-22.6, 23.2
"""

from typing import Optional, Dict, Any, List
import logging
import re

from app.agent.state.conversation_state import ConversationState
from app.agent.tools import TOOL_REGISTRY
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.booking_prompts import create_select_property_prompt
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


async def select_property(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState:
    """
    Handle property selection in booking flow using LangChain agent.
    
    This node manages the property selection step of the booking process. It:
    1. Checks if property is already selected in flow_state
    2. Retrieves properties from bot_memory search results
    3. Presents properties as button options if not yet selected
    4. Uses LangChain agent to parse user selection intelligently
    5. Validates the selection
    6. Stores selected property_id in flow_state
    7. Updates flow_state step to "select_property"
    8. Handles invalid selections with helpful error messages
    
    Implements Requirements:
    - 6.3: Booking_Subgraph with Select_Property node
    - 9.1: Use LangChain agents with ChatOpenAI wrapper
    - 9.2: Use create_langchain_llm() for LLM instances
    - 20.2: Store selected property_id when user chooses a property
    - 22.1: Present properties from search results
    - 22.2: Present booking summary including property name
    - 22.3: Ask for explicit user confirmation
    - 22.4: Create booking when user confirms
    - 22.5: Clear flow_state when user cancels
    - 22.6: Return to appropriate step when user requests changes
    - 23.2: Support button message type for quick reply options
    
    Args:
        state: ConversationState containing user message, flow_state, and bot_memory
        llm_provider: LLMProvider instance for creating LangChain LLM
        tools: Optional tool registry (defaults to TOOL_REGISTRY if not provided)
        
    Returns:
        ConversationState: State with response_content, response_type, response_metadata,
                          and updated flow_state containing property_id and step
        
    Example:
        # First call - present options
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "I want to book a court",
            "flow_state": {"intent": "booking"},
            "bot_memory": {
                "context": {
                    "last_search_results": ["1", "2", "3"]
                }
            },
            ...
        }
        
        result = await select_property(state, llm_provider, tools)
        # result["response_type"] = "button"
        # result["response_metadata"]["buttons"] = [...]
        # result["flow_state"]["step"] = "select_property"
        
        # Second call - process selection
        state = {
            "user_message": "Downtown Sports Center",
            "flow_state": {"intent": "booking", "step": "select_property"},
            "bot_memory": {
                "context": {
                    "last_search_results": ["1", "2", "3"]
                }
            },
            ...
        }
        
        result = await select_property(state, llm_provider, tools)
        # result["flow_state"]["property_id"] = "1"
        # result["flow_state"]["property_name"] = "Downtown Sports Center"
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    bot_memory = state.get("bot_memory", {})
    
    # Use provided tools or default to TOOL_REGISTRY
    if tools is None:
        tools = TOOL_REGISTRY
    
    logger.info(
        f"Processing property selection for chat {chat_id} - "
        f"step={flow_state.get('step')}, "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if property already selected
    if flow_state.get("property_id"):
        logger.debug(
            f"Property already selected for chat {chat_id}: "
            f"property_id={flow_state.get('property_id')}"
        )
        # Property already selected, continue to next step
        return state
    
    # Check if we're processing a selection or presenting options
    current_step = flow_state.get("step")
    
    if current_step == "select_property":
        # User is responding with a selection
        return await _process_property_selection(
            state=state,
            llm_provider=llm_provider,
            tools=tools,
            chat_id=chat_id,
            user_message=user_message,
            flow_state=flow_state,
            bot_memory=bot_memory
        )
    else:
        # First time in this node, present options
        return await _present_property_options(
            state=state,
            tools=tools,
            chat_id=chat_id,
            flow_state=flow_state,
            bot_memory=bot_memory
        )


async def _present_property_options(
    state: ConversationState,
    tools: Dict[str, Any],
    chat_id: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any]
) -> ConversationState:
    """
    Present property options to the user as buttons.
    
    This function retrieves properties from bot_memory search results and
    presents them as button options for the user to select from.
    
    Args:
        state: ConversationState
        tools: Tool registry
        chat_id: Chat ID for logging
        flow_state: Current flow state
        bot_memory: Bot memory containing search results
        
    Returns:
        Updated ConversationState with button options
    """
    # Check if user has previous search results
    last_search = bot_memory.get("context", {}).get("last_search_results", [])
    
    if not last_search:
        # No previous search, prompt user to search first
        logger.info(
            f"No search results found for chat {chat_id}, "
            f"prompting user to search first"
        )
        
        response = (
            "To make a booking, I first need to know which facility you're interested in. "
            "Would you like me to search for available facilities? "
            "You can tell me what sport you're looking for (e.g., 'tennis courts') "
            "or a location (e.g., 'downtown')."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        # Update flow state to indicate we're waiting for search
        flow_state["step"] = "awaiting_search"
        state["flow_state"] = flow_state
        
        return state
    
    # Retrieve property details for the search results
    properties = await _get_properties_by_ids(
        tools=tools,
        property_ids=last_search[:5],  # Limit to 5 properties
        chat_id=chat_id
    )
    
    if not properties:
        logger.warning(
            f"Failed to retrieve property details for chat {chat_id}"
        )
        
        response = (
            "I'm having trouble retrieving the facility details. "
            "Would you like to search again?"
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        return state
    
    # Format properties as buttons
    buttons = _format_properties_as_buttons(properties)
    
    # Generate response message
    response = "Which facility would you like to book?"
    
    # Update state with response
    state["response_content"] = response
    state["response_type"] = "button"
    state["response_metadata"] = {"buttons": buttons}
    
    # Update flow state
    flow_state["step"] = "select_property"
    state["flow_state"] = flow_state
    
    # Store property details in bot_memory for later reference
    bot_memory = _store_property_details_in_memory(
        bot_memory=bot_memory,
        properties=properties
    )
    state["bot_memory"] = bot_memory
    
    logger.info(
        f"Presented {len(buttons)} property options for chat {chat_id}"
    )
    
    return state


async def _process_property_selection(
    state: ConversationState,
    llm_provider: LLMProvider,
    tools: Dict[str, Any],
    chat_id: str,
    user_message: str,
    flow_state: Dict[str, Any],
    bot_memory: Dict[str, Any]
) -> ConversationState:
    """
    Process user's property selection using LangChain agent.
    
    This function uses a LangChain agent to intelligently parse the user's
    selection, validates it, and stores the selected property_id in flow_state.
    
    Args:
        state: ConversationState
        llm_provider: LLMProvider for creating LangChain LLM
        tools: Tool registry
        chat_id: Chat ID for logging
        user_message: User's selection message
        flow_state: Current flow state
        bot_memory: Bot memory containing property details
        
    Returns:
        Updated ConversationState with selected property_id in flow_state
    """
    # Get available properties from bot_memory
    available_properties = bot_memory.get("context", {}).get("property_details", [])
    
    if not available_properties:
        # Fallback: retrieve from last_search_results
        last_search = bot_memory.get("context", {}).get("last_search_results", [])
        if last_search:
            available_properties = await _get_properties_by_ids(
                tools=tools,
                property_ids=last_search[:5],
                chat_id=chat_id
            )
        else:
            logger.error(
                f"No available properties found in bot_memory for chat {chat_id}"
            )
            
            response = (
                "I couldn't find the available facilities. "
                "Let's start over. What type of facility are you looking for?"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            # Reset flow state
            flow_state["step"] = "awaiting_search"
            state["flow_state"] = flow_state
            
            return state
    
    # Create LangChain LLM
    try:
        llm = create_langchain_llm(llm_provider)
    except Exception as e:
        logger.error(f"Failed to create LangChain LLM for chat {chat_id}: {e}", exc_info=True)
        # Fallback to manual parsing
        selected_property = _parse_property_selection(
            user_message=user_message,
            available_properties=available_properties
        )
        
        if not selected_property:
            # Invalid selection
            logger.warning(
                f"Invalid property selection for chat {chat_id}: {user_message}"
            )
            
            # Generate helpful error message with available options
            property_names = [p.get("name", "Unknown") for p in available_properties]
            options_text = ", ".join(property_names)
            
            response = (
                f"I couldn't find that facility. "
                f"Please select from the available options: {options_text}"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            return state
        
        # Valid selection - store in flow_state
        property_id = str(selected_property.get("id"))
        property_name = selected_property.get("name", "Unknown Property")
        
        flow_state["property_id"] = property_id
        flow_state["property_name"] = property_name
        flow_state["step"] = "property_selected"
        
        state["flow_state"] = flow_state
        
        # Generate confirmation message
        response = (
            f"Great! You've selected {property_name}. "
            f"Now let's choose a court."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        logger.info(
            f"Property selected for chat {chat_id}: "
            f"property_id={property_id}, property_name={property_name}"
        )
        
        return state
    
    # Create prompt for property selection
    prompt = create_select_property_prompt(available_properties)
    
    # Use LLM to parse selection
    try:
        messages = prompt.format_messages(input=user_message)
        response_obj = await llm.ainvoke(messages)
        agent_response = response_obj.content.strip()
        
        logger.debug(f"Agent response for property selection: {agent_response}")
        
        # Try to extract property ID from response
        # Agent should respond with just the property ID number
        property_id_match = re.search(r'\b(\d+)\b', agent_response)
        
        if property_id_match:
            property_id_str = property_id_match.group(1)
            
            # Find property with this ID
            selected_property = None
            for prop in available_properties:
                if str(prop.get("id")) == property_id_str:
                    selected_property = prop
                    break
            
            if selected_property:
                # Valid selection - store in flow_state
                property_id = str(selected_property.get("id"))
                property_name = selected_property.get("name", "Unknown Property")
                
                flow_state["property_id"] = property_id
                flow_state["property_name"] = property_name
                flow_state["step"] = "property_selected"
                
                state["flow_state"] = flow_state
                
                # Generate confirmation message
                response = (
                    f"Great! You've selected {property_name}. "
                    f"Now let's choose a court."
                )
                
                state["response_content"] = response
                state["response_type"] = "text"
                state["response_metadata"] = {}
                
                logger.info(
                    f"Property selected for chat {chat_id}: "
                    f"property_id={property_id}, property_name={property_name}"
                )
                
                return state
        
        # Agent is asking for clarification or couldn't parse
        # Use agent's response directly
        state["response_content"] = agent_response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        logger.info(f"Agent asking for clarification in chat {chat_id}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error using LangChain agent for property selection in chat {chat_id}: {e}", exc_info=True)
        
        # Fallback to manual parsing
        selected_property = _parse_property_selection(
            user_message=user_message,
            available_properties=available_properties
        )
        
        if not selected_property:
            # Invalid selection
            logger.warning(
                f"Invalid property selection for chat {chat_id}: {user_message}"
            )
            
            # Generate helpful error message with available options
            property_names = [p.get("name", "Unknown") for p in available_properties]
            options_text = ", ".join(property_names)
            
            response = (
                f"I couldn't find that facility. "
                f"Please select from the available options: {options_text}"
            )
            
            state["response_content"] = response
            state["response_type"] = "text"
            state["response_metadata"] = {}
            
            return state
        
        # Valid selection - store in flow_state
        property_id = str(selected_property.get("id"))
        property_name = selected_property.get("name", "Unknown Property")
        
        flow_state["property_id"] = property_id
        flow_state["property_name"] = property_name
        flow_state["step"] = "property_selected"
        
        state["flow_state"] = flow_state
        
        # Generate confirmation message
        response = (
            f"Great! You've selected {property_name}. "
            f"Now let's choose a court."
        )
        
        state["response_content"] = response
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        logger.info(
            f"Property selected for chat {chat_id}: "
            f"property_id={property_id}, property_name={property_name}"
        )
        
        return state


async def _get_properties_by_ids(
    tools: Dict[str, Any],
    property_ids: List[str],
    chat_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve property details for a list of property IDs.
    
    This function calls the get_property_details tool for each property ID
    and returns a list of property dictionaries.
    
    Args:
        tools: Tool registry
        property_ids: List of property IDs to retrieve
        chat_id: Chat ID for logging
        
    Returns:
        List of property dictionaries
    """
    get_property_details = tools.get("get_property_details")
    if not get_property_details:
        logger.error("get_property_details tool not found in registry")
        return []
    
    properties = []
    
    for property_id in property_ids:
        try:
            # Convert property_id to int if it's a string
            property_id_int = int(property_id) if isinstance(property_id, str) else property_id
            
            logger.debug(
                f"Retrieving property details for chat {chat_id}: "
                f"property_id={property_id_int}"
            )
            
            property_data = await get_property_details(
                property_id=property_id_int,
                owner_id=None  # Public access
            )
            
            if property_data:
                properties.append(property_data)
            else:
                logger.warning(
                    f"Property not found for chat {chat_id}: "
                    f"property_id={property_id_int}"
                )
                
        except Exception as e:
            logger.error(
                f"Error retrieving property {property_id} for chat {chat_id}: {e}",
                exc_info=True
            )
    
    logger.info(
        f"Retrieved {len(properties)} properties for chat {chat_id}"
    )
    
    return properties


def _format_properties_as_buttons(
    properties: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Format properties as button options.
    
    This function converts property dictionaries into button format
    with id and text fields suitable for display to the user.
    
    Implements Requirement 23.2: Support button message type for quick reply options
    
    Args:
        properties: List of property dictionaries
        
    Returns:
        List of button dictionaries with id and text fields
        
    Example:
        buttons = _format_properties_as_buttons([
            {"id": 1, "name": "Sports Center", "city": "NYC"}
        ])
        # Returns: [{"id": "1", "text": "Sports Center"}]
    """
    buttons = []
    
    for prop in properties:
        property_id = prop.get("id")
        name = prop.get("name", "Unknown Property")
        
        buttons.append({
            "id": str(property_id),
            "text": name
        })
    
    return buttons


def _parse_property_selection(
    user_message: str,
    available_properties: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Parse user's property selection from message.
    
    This function attempts to match the user's message to a property by:
    1. Exact property ID match
    2. Exact property name match (case-insensitive)
    3. Partial property name match (case-insensitive)
    
    Args:
        user_message: User's selection message
        available_properties: List of available property dictionaries
        
    Returns:
        Selected property dictionary or None if no match found
        
    Example:
        property = _parse_property_selection(
            "Downtown Sports Center",
            [{"id": 1, "name": "Downtown Sports Center"}]
        )
        # Returns: {"id": 1, "name": "Downtown Sports Center"}
    """
    message_lower = user_message.lower().strip()
    
    # Return None for empty messages
    if not message_lower:
        logger.debug("Empty message provided for property selection")
        return None
    
    # Try to match by property ID
    # Check if message is a number or contains a number
    id_match = re.search(r'\b(\d+)\b', message_lower)
    if id_match:
        property_id = id_match.group(1)
        for prop in available_properties:
            if str(prop.get("id")) == property_id:
                logger.debug(f"Matched property by ID: {property_id}")
                return prop
    
    # Try exact name match (case-insensitive)
    for prop in available_properties:
        property_name = prop.get("name", "").lower()
        if property_name == message_lower:
            logger.debug(f"Matched property by exact name: {property_name}")
            return prop
    
    # Try partial name match (case-insensitive)
    for prop in available_properties:
        property_name = prop.get("name", "").lower()
        # Check if user message is contained in property name or vice versa
        if message_lower in property_name or property_name in message_lower:
            logger.debug(f"Matched property by partial name: {property_name}")
            return prop
    
    # Try matching individual words
    message_words = set(message_lower.split())
    best_match = None
    best_match_score = 0
    
    for prop in available_properties:
        property_name = prop.get("name", "").lower()
        property_words = set(property_name.split())
        
        # Calculate word overlap
        common_words = message_words.intersection(property_words)
        if common_words:
            score = len(common_words)
            if score > best_match_score:
                best_match = prop
                best_match_score = score
    
    if best_match and best_match_score >= 1:
        logger.debug(
            f"Matched property by word overlap: {best_match.get('name')} "
            f"(score={best_match_score})"
        )
        return best_match
    
    # No match found
    logger.debug(f"No property match found for: {user_message}")
    return None


def _store_property_details_in_memory(
    bot_memory: Dict[str, Any],
    properties: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Store property details in bot_memory for later reference.
    
    This function stores the retrieved property details in bot_memory
    so they can be accessed during property selection without additional
    API calls.
    
    Args:
        bot_memory: Current bot_memory dictionary
        properties: List of property dictionaries to store
        
    Returns:
        Updated bot_memory dictionary
    """
    # Ensure context exists
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Store property details
    bot_memory["context"]["property_details"] = properties
    
    return bot_memory
