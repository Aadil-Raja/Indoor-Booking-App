"""
Information node handler for LangGraph conversation management.

This module implements the information_node that handles all information-related
queries using LangChain AgentExecutor with automatic tool calling. It processes
queries about properties, courts, availability, pricing, and media.

The node uses LangChain's create_react_agent (ReAct pattern) to automatically select
and execute appropriate tools based on user queries, with reasoning and acting steps.

The node also implements reversibility by detecting when users want to change
specific booking attributes and clearing only those fields while preserving
other booking information.

Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5, 7.1-7.6,
             8.1-8.5, 9.1-9.6, 10.1-10.5, 11.1-11.5, 16.1-16.6
"""

from typing import Optional, Any
import logging

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.tools.information_tools import INFORMATION_TOOLS
from app.agent.tools.langchain_converter import create_langchain_tools
from app.agent.state.memory_manager import update_bot_memory
from app.agent.state.llm_response_parser import parse_llm_response
from app.agent.state.flow_state_manager import clear_booking_field, update_flow_state
from typing import Any

logger = logging.getLogger(__name__)


async def information_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle information queries using LangChain ReAct agent with automatic tool calling.
    
    This node processes all information-related queries about properties, courts,
    availability, pricing, and media. It uses a LangChain ReAct AgentExecutor that
    automatically selects and executes appropriate tools based on the user's query.
    
    The node also implements reversibility by detecting when users want to change
    specific booking attributes (property, court, date, time slot) and clearing
    only those fields while preserving other booking information.
    
    The ReAct (Reasoning + Acting) pattern allows the agent to:
    - Reason about what information is needed
    - Act by calling appropriate tools
    - Observe the results
    - Reason about next steps
    - Continue until the query is fully answered
    
    The node follows the standard LangGraph node pattern:
    1. Extract state (user_message, owner_profile_id, bot_memory, flow_state)
    2. Detect attribute change requests (reversibility)
    3. If attribute change detected, clear specific field and route to booking
    4. Create LangChain tools from INFORMATION_TOOLS registry
    5. Build context-aware prompt with bot_memory and fuzzy search guidance
    6. Create ChatOpenAI LLM using create_langchain_llm()
    7. Create agent using create_react_agent()
    8. Execute AgentExecutor with automatic tool calling
    9. Apply fuzzy search logic for sports and court names
    10. Update bot_memory with results
    11. Return updated state with response and next_node decision
    
    Implements Requirements:
    - 7.5: User can change booking attributes without restarting flow
    - 7.6: System continues from where left off after attribute change
    - 9.2: Information_Handler processes all non-booking informational queries
    - 9.3: Information_Handler uses existing search tools to retrieve information
    - 9.4: LLM decides when to use search tools versus answering from context
    - 9.5: Property details queries handled by Information_Handler
    - 9.6: Court availability queries handled by Information_Handler
    - 16.1: Clear only property_id and property_name when property changes
    - 16.2: Clear only court_id and court_name when court changes
    - 16.3: Clear only date field when date changes
    - 16.4: Clear only time_slot field when time slot changes
    - 16.5: Preserve all other Flow_State fields when changing specific detail
    - 16.6: Save new value in appropriate Flow_State field
    
    Args:
        state: ConversationState containing user message and context
        llm_provider: LLMProvider instance for creating ChatOpenAI
        
    Returns:
        ConversationState: Updated state with response_content, bot_memory, and next_node
        
    Example:
        # Information query
        state = {
            "user_message": "Show me football courts in New York",
            "owner_profile_id": "1",
            "bot_memory": {},
            ...
        }
        
        result = await information_handler(state, llm_provider=provider)
        # result["response_content"] contains the agent's response
        # result["bot_memory"] contains updated context
        # Fuzzy search: "football" → "futsal" with confirmation
        
        # Attribute change (reversibility)
        state = {
            "user_message": "I want to change to a different property",
            "flow_state": {
                "property_id": 1,
                "court_id": 2,
                "date": "2024-01-15"
            },
            ...
        }
        
        result = await information_handler(state, llm_provider=provider)
        # result["flow_state"]["property_id"] is None
        # result["flow_state"]["court_id"] is None (downstream cleared)
        # result["flow_state"]["date"] is None (downstream cleared)
        # result["next_node"] is "booking" (continue from where left off)
    """
    # 1. Extract state
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    owner_profile_id = state["owner_profile_id"]
    bot_memory = state.get("bot_memory", {})
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Processing information query for chat {chat_id} - "
        f"message_preview={user_message[:50]}..."
    )
    
    try:
        # 2. Check for attribute change requests (reversibility)
        field_to_clear, new_value = _detect_attribute_change(user_message, flow_state)
        
        if field_to_clear:
            logger.info(
                f"Detected attribute change request for field '{field_to_clear}' "
                f"in chat {chat_id}"
            )
            
            # Clear the specific field and downstream fields
            flow_state = clear_booking_field(flow_state, field_to_clear)
            state["flow_state"] = flow_state
            
            # Update context to indicate change was processed
            flow_state["context"]["last_change"] = {
                "field": field_to_clear,
                "message": user_message
            }
            
            # Build response acknowledging the change
            field_display_names = {
                "property": "property",
                "court": "court",
                "date": "date",
                "time_slot": "time slot"
            }
            
            response_content = (
                f"I've cleared your {field_display_names.get(field_to_clear, field_to_clear)} "
                f"selection. Let me help you choose a new one."
            )
            
            state["response_content"] = response_content
            state["response_type"] = "text"
            state["response_metadata"] = {
                "attribute_changed": True,
                "field_cleared": field_to_clear
            }
            
            # Route back to booking to continue from where left off
            state["next_node"] = "booking"
            
            logger.info(
                f"Attribute change processed for chat {chat_id} - "
                f"field={field_to_clear}, routing to booking"
            )
            
            return state
        
        # 3. Apply fuzzy search logic for sports and court names
        fuzzy_message, fuzzy_context = _apply_fuzzy_search(user_message)
        
        # 4. Fetch owner profile to get business_name for personalization
        logger.debug(f"Fetching owner profile for personalization - owner_profile_id={owner_profile_id}")
        owner_profile = await _fetch_owner_profile(owner_profile_id, chat_id)
        business_name = owner_profile.get("business_name") if owner_profile else None
        
        if business_name:
            logger.info(f"Using business_name '{business_name}' for personalization in chat {chat_id}")
        else:
            logger.warning(f"No business_name found for owner_profile_id={owner_profile_id}, using default")
        
        # 5. Convert tools to LangChain format
        logger.debug("Converting information tools to LangChain format")
        langchain_tools = create_langchain_tools(INFORMATION_TOOLS)
        logger.info(f"Created {len(langchain_tools)} LangChain tools")
        
        # 6. Create ChatOpenAI LLM using wrapper
        if not llm_provider:
            raise ValueError("llm_provider is required for information node")
        
        logger.debug("Creating ChatOpenAI LLM instance")
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.7,  # Balanced creativity for natural responses
            max_tokens=1000   # Allow longer responses for detailed information
        )
        
        # 7. Build context-aware prompt with business_name and fuzzy search guidance
        logger.debug("Building context-aware prompt with bot_memory and business_name")
        system_message = _build_system_message(
            owner_profile_id=int(owner_profile_id),
            bot_memory=bot_memory,
            business_name=business_name,
            fuzzy_context=fuzzy_context
        )
        
        # Create prompt for OpenAI tools agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # 8. Bind tools to LLM
        logger.debug("Binding tools to LLM")
        llm_with_tools = llm.bind_tools(langchain_tools)
        
        # 9. Create agent manually (OpenAI tools pattern)
        logger.debug("Creating OpenAI tools agent")
        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                    x["intermediate_steps"]
                ),
                "chat_history": lambda x: x.get("chat_history", []),
            }
            | prompt
            | llm_with_tools
            | OpenAIToolsAgentOutputParser()
        )
        
        # 10. Create AgentExecutor with agent and tools
        logger.debug("Creating AgentExecutor")
        agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,  # Enable verbose logging for debugging
            max_iterations=5,  # Limit iterations to prevent infinite loops
            handle_parsing_errors=True,  # Gracefully handle parsing errors
            return_intermediate_steps=True  # Return tool calls for debugging
        )
        
        # 11. Execute agent with ainvoke() passing fuzzy-corrected message
        logger.info(f"Executing OpenAI tools agent for chat {chat_id}")
        result = await agent_executor.ainvoke({
            "input": fuzzy_message,
            "chat_history": [],  # Could be populated from bot_memory if needed
        })
        
        # 12. Update state with response_content from agent result
        response_content = result.get("output", "")
        
        # 12. Add fuzzy search confirmation if applicable
        if fuzzy_context.get("fuzzy_match"):
            confirmation = fuzzy_context["confirmation_message"]
            response_content = f"{confirmation}\n\n{response_content}"
        
        state["response_content"] = response_content
        state["response_type"] = "text"
        state["response_metadata"] = {
            "fuzzy_match": fuzzy_context.get("fuzzy_match", False),
            "original_term": fuzzy_context.get("original_term"),
            "corrected_term": fuzzy_context.get("corrected_term")
        }
        
        logger.info(
            f"Agent execution completed for chat {chat_id} - "
            f"response_length={len(response_content)}"
        )
        
        # 13. Update bot_memory using update_bot_memory()
        logger.debug("Updating bot_memory with agent results")
        updated_bot_memory = update_bot_memory(bot_memory, result)
        state["bot_memory"] = updated_bot_memory
        
        # Log tools used for debugging
        tools_used = updated_bot_memory.get("context", {}).get("last_tools_used", [])
        if tools_used:
            logger.info(f"Tools used in this interaction: {', '.join(tools_used)}")
        
        # 14. Determine next_node based on conversation flow
        # Information handler typically stays in information mode unless user switches intent
        next_node = _determine_next_node(user_message, response_content, flow_state)
        state["next_node"] = next_node
        
        logger.info(
            f"Information node completed successfully for chat {chat_id} - "
            f"next_node={next_node}"
        )
        
    except Exception as e:
        # 15. Handle exceptions and return error message on failure
        logger.error(
            f"Error in information node for chat {chat_id}: {e}",
            exc_info=True
        )
        
        state["response_content"] = (
            "I'm sorry, I encountered an error while processing your request. "
            "Please try again or rephrase your question."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
        state["next_node"] = "information"  # Stay in information mode
    
    return state


def _apply_fuzzy_search(user_message: str) -> tuple[str, dict]:
    """
    Apply fuzzy search logic for sports and court names.
    
    This function detects common variations and typos in sport names and
    suggests corrections. For example:
    - "football" → "futsal"
    - "soccer" → "futsal"
    - "hoops" → "basketball"
    
    Args:
        user_message: Original user message
        
    Returns:
        Tuple of (corrected_message, fuzzy_context)
        - corrected_message: Message with fuzzy corrections applied
        - fuzzy_context: Dict with fuzzy match information
    """
    # Sport name mappings (common variations → standard names)
    sport_mappings = {
        "football": "futsal",
        "soccer": "futsal",
        "hoops": "basketball",
        "b-ball": "basketball",
        "ping pong": "table tennis",
        "pingpong": "table tennis",
    }
    
    fuzzy_context = {
        "fuzzy_match": False,
        "original_term": None,
        "corrected_term": None,
        "confirmation_message": ""
    }
    
    # Check for fuzzy matches (case-insensitive)
    message_lower = user_message.lower()
    corrected_message = user_message
    
    for original, corrected in sport_mappings.items():
        if original in message_lower:
            # Replace the term in the message
            corrected_message = user_message.replace(original, corrected)
            corrected_message = corrected_message.replace(original.title(), corrected.title())
            corrected_message = corrected_message.replace(original.upper(), corrected.upper())
            
            # Build confirmation message
            fuzzy_context["fuzzy_match"] = True
            fuzzy_context["original_term"] = original
            fuzzy_context["corrected_term"] = corrected
            fuzzy_context["confirmation_message"] = (
                f"I understood you're looking for {corrected} "
                f"(you mentioned {original})."
            )
            
            logger.info(
                f"Fuzzy search applied: '{original}' → '{corrected}'"
            )
            break
    
    return corrected_message, fuzzy_context


def _detect_attribute_change(user_message: str, flow_state: dict) -> tuple[Optional[str], Optional[Any]]:
    """
    Detect when user wants to change a booking attribute.
    
    This function analyzes the user message to determine if they want to
    change a specific booking detail (property, court, date, or time slot).
    It returns the field name to clear and the new value if detected.
    
    Implements Requirements:
    - 7.5: User can change booking attributes without restarting flow
    - 7.6: System continues from where left off after attribute change
    - 16.1: Clear only property_id and property_name when property changes
    - 16.2: Clear only court_id and court_name when court changes
    - 16.3: Clear only date field when date changes
    - 16.4: Clear only time_slot field when time slot changes
    - 16.5: Preserve all other Flow_State fields when changing specific detail
    - 16.6: Save new value in appropriate Flow_State field
    
    Args:
        user_message: User's message
        flow_state: Current flow state
        
    Returns:
        Tuple of (field_to_clear, new_value)
        - field_to_clear: "property", "court", "date", "time_slot", or None
        - new_value: The new value mentioned by user, or None
        
    Example:
        field, value = _detect_attribute_change(
            "I want to change to a different property",
            flow_state
        )
        # Returns: ("property", None)
        
        field, value = _detect_attribute_change(
            "Actually, let's book for tomorrow instead",
            flow_state
        )
        # Returns: ("date", "tomorrow")
    """
    if not flow_state or not isinstance(flow_state, dict):
        return None, None
    
    message_lower = user_message.lower()
    
    # Keywords for detecting change intent
    change_keywords = [
        "change", "switch", "different", "another", "modify",
        "update", "instead", "actually", "rather", "prefer"
    ]
    
    # Check if user wants to make a change
    has_change_intent = any(keyword in message_lower for keyword in change_keywords)
    
    if not has_change_intent:
        return None, None
    
    # Detect which attribute they want to change
    
    # Property change detection
    property_keywords = ["property", "location", "venue", "place", "facility"]
    if any(keyword in message_lower for keyword in property_keywords):
        if flow_state.get("property_id"):
            logger.info("Detected property change request")
            return "property", None
    
    # Court change detection
    court_keywords = ["court", "field", "pitch"]
    if any(keyword in message_lower for keyword in court_keywords):
        if flow_state.get("court_id"):
            logger.info("Detected court change request")
            return "court", None
    
    # Date change detection
    date_keywords = [
        "date", "day", "tomorrow", "today", "monday", "tuesday",
        "wednesday", "thursday", "friday", "saturday", "sunday",
        "next week", "this week"
    ]
    if any(keyword in message_lower for keyword in date_keywords):
        if flow_state.get("date"):
            logger.info("Detected date change request")
            # Extract the new date from message (will be parsed by date selection node)
            return "date", user_message
    
    # Time slot change detection
    time_keywords = [
        "time", "slot", "hour", "morning", "afternoon", "evening",
        "am", "pm", "o'clock", "earlier", "later"
    ]
    if any(keyword in message_lower for keyword in time_keywords):
        if flow_state.get("time_slot"):
            logger.info("Detected time slot change request")
            # Extract the new time from message (will be parsed by time selection node)
            return "time_slot", user_message
    
    return None, None


def _determine_next_node(
    user_message: str,
    response_content: str,
    flow_state: dict
) -> str:
    """
    Determine the next node based on conversation context.
    
    This function analyzes the user message and response to decide if the
    conversation should stay in information mode or transition to booking.
    
    Args:
        user_message: User's message
        response_content: Agent's response
        flow_state: Current flow state
        
    Returns:
        Next node name: "information", "booking", or "greeting"
    """
    # Check for booking intent keywords
    booking_keywords = [
        "book", "reserve", "reservation", "schedule",
        "book it", "i want to book", "make a booking"
    ]
    
    message_lower = user_message.lower()
    
    # If user explicitly wants to book, transition to booking
    for keyword in booking_keywords:
        if keyword in message_lower:
            logger.info("Detected booking intent, transitioning to booking node")
            return "booking"
    
    # Check if already in booking flow
    if flow_state.get("current_intent") == "booking":
        return "booking"
    
    # Default: stay in information mode
    return "information"


async def _fetch_owner_profile(owner_profile_id: str, chat_id: str) -> dict:
    """
    Fetch owner profile to get business_name and other details for personalization.
    
    This function retrieves the owner profile from the database to extract
    the business_name field, which is used to personalize the assistant's
    identity in the information prompts.
    
    Args:
        owner_profile_id: Owner profile ID
        chat_id: Chat ID for logging
        
    Returns:
        Dictionary with owner profile data including business_name
        Returns empty dict if profile not found or error occurs
        
    Example:
        >>> profile = await _fetch_owner_profile("1", "chat_123")
        >>> print(profile["business_name"])
        "ABC Sports Center"
    """
    try:
        from sqlalchemy.orm import Session
        from shared.models import OwnerProfile
        from app.agent.tools.sync_bridge import call_sync_service
        
        def get_owner_profile_sync(db: Session, profile_id: int) -> dict:
            """Sync function to fetch owner profile"""
            profile = db.query(OwnerProfile).filter(OwnerProfile.id == profile_id).first()
            if profile:
                return {
                    "id": profile.id,
                    "business_name": profile.business_name,
                    "phone": profile.phone,
                    "address": profile.address,
                    "verified": profile.verified
                }
            return {}
        
        # Call sync service using the bridge
        profile_data = await call_sync_service(
            get_owner_profile_sync,
            db=None,  # Auto-managed by sync bridge
            profile_id=int(owner_profile_id)
        )
        
        logger.info(
            f"Fetched owner profile for personalization - "
            f"owner_profile_id={owner_profile_id}, chat={chat_id}"
        )
        return profile_data
        
    except Exception as e:
        logger.error(
            f"Error fetching owner profile for information node in chat {chat_id}: {e}",
            exc_info=True
        )
        return {}


def _build_system_message(
    owner_profile_id: int,
    bot_memory: dict,
    business_name: Optional[str] = None,
    fuzzy_context: Optional[dict] = None
) -> str:
    """Build system message for information agent."""
    business_name_str = business_name or "our facility"
    
    # Extract context
    context_parts = []
    if bot_memory.get("context", {}).get("last_search_results"):
        results = bot_memory["context"]["last_search_results"]
        context_parts.append(f"Last search returned property IDs: {', '.join(results)}")
    
    if bot_memory.get("user_preferences", {}).get("preferred_sport"):
        sport = bot_memory["user_preferences"]["preferred_sport"]
        context_parts.append(f"User prefers: {sport}")
    
    context = "\n".join(context_parts) if context_parts else "No previous context"
    
    # Fuzzy context
    fuzzy_context = fuzzy_context or {}
    if fuzzy_context.get("fuzzy_match"):
        fuzzy_str = (
            f"Sport name correction applied: '{fuzzy_context.get('original_term')}' "
            f"→ '{fuzzy_context.get('corrected_term')}'"
        )
    else:
        fuzzy_str = "No fuzzy corrections applied"
    
    return f"""You are a helpful sports facility information assistant for {business_name_str}.

Owner Profile ID: {owner_profile_id}

Context from previous conversation:
{context}

Fuzzy Search Context:
{fuzzy_str}

Your role is to help users find and learn about sports facilities, courts, availability, and pricing.

Guidelines:
- Use the available tools to get accurate, up-to-date information
- Be conversational and helpful
- Present information in a clear, organized way
- When showing multiple results, present them in a numbered list
- If you don't have enough information, ask clarifying questions
- Always pass owner_profile_id parameter when calling search_properties tool
"""
