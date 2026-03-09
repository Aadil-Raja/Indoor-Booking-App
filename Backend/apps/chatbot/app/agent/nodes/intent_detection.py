"""
Intent detection node - uses LLM to decide routing.

Simple routing only:
- "greeting" for greetings
- "information" for questions
- "booking" for reservations
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

logger = logging.getLogger(__name__)


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Use LLM to decide routing (greeting/information/booking).
    
    Uses conversation context for better routing of ambiguous messages.
    Falls back to "greeting" if LLM fails.
    
    New users (owner_properties not initialized) are forced to greeting.
    """
    user_message = state["user_message"]
    recent_messages = state.get("messages", [])
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Determining routing for chat {state['chat_id']} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Check if owner_properties have been initialized
    owner_properties_initialized = flow_state.get("owner_properties_initialized", False)
    
    if not owner_properties_initialized:
        # New user - force to greeting to initialize properties
        logger.info(
            f"New user detected (owner_properties not initialized) for chat {state['chat_id']}, "
            f"forcing route to greeting"
        )
        state["next_node"] = "greeting"
        state["is_first_message"] = True
        return state
    
    # Returning user - use LLM for routing decision
    if llm_provider:
        next_node = await _llm_routing_decision(
            user_message=user_message,
            recent_messages=recent_messages,
            last_node=flow_state.get("last_node"),
            llm_provider=llm_provider,
            chat_id=state['chat_id']
        )
    else:
        logger.warning(
            f"No LLM provider, defaulting to greeting for chat {state['chat_id']}"
        )
        next_node = "greeting"
    
    # Store next_node for graph routing
    state["next_node"] = next_node
    
    logger.info(f"Routing decision for chat {state['chat_id']}: next_node={next_node}")
    
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
