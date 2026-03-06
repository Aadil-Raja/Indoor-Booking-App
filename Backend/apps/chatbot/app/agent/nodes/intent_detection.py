"""
Intent detection node - uses LLM to decide routing.

LLM analyzes user message and returns next_node decision:
- "greeting" for greetings
- "information" for questions
- "booking" for reservations
"""

from typing import Optional
import logging
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.intent_prompts import get_routing_prompt
from app.agent.state.llm_response_parser import parse_llm_response, apply_state_updates

logger = logging.getLogger(__name__)


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Use LLM to decide routing (greeting/information/booking).
    
    LLM analyzes message and returns:
    - next_node: which handler to route to
    - state_updates: any state changes to apply
    
    Falls back to "greeting" if LLM fails.
    """
    user_message = state["user_message"]

    
    logger.info(
        f"Determining routing for chat {state['chat_id']} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Use LLM for routing decision
    if llm_provider:
        next_node, message, state_updates = await _llm_routing_decision(
            user_message, 
            llm_provider,
            state['chat_id']
        )
    else:
        # No LLM provider available, default to greeting
        logger.warning(
            f"No LLM provider available for routing decision, "
            f"defaulting to greeting for chat {state['chat_id']}"
        )
        next_node = "greeting"
        message = "Hello! How can I help you today?"
        state_updates = {}
    
    # Apply state updates before routing
    state = apply_state_updates(state, state_updates)
    
    # Store next_node for graph routing
    state["next_node"] = next_node
    
    # Store LLM message if provided
    if message:
        state["response_content"] = message
    
    logger.info(
        f"Routing decision for chat {state['chat_id']}: next_node={next_node}, "
        f"state_updates_applied={bool(state_updates)}"
    )
    
    return state


async def _llm_routing_decision(
    message: str, 
    llm_provider: LLMProvider,
    chat_id: str
) -> tuple[str, str, dict]:
    """
    Call LLM to get routing decision.
    
    Returns: (next_node, message, state_updates)
    Defaults to "greeting" if LLM fails.
    """
    # Get formatted prompt from template
    prompt = get_routing_prompt(message)
    
    try:
        # Create LangChain ChatOpenAI instance using wrapper
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.0,  # Low temperature for consistent routing
            max_tokens=200    # Enough for JSON response
        )
        
        # Call LLM using LangChain's ainvoke method
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Parse JSON response
        try:
            llm_response = json.loads(response.content.strip())
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse LLM JSON response for chat {chat_id}: {e}. "
                f"Response content: {response.content[:200]}"
            )
            # Return safe defaults
            return "greeting", "Hello! How can I help you?", {}
        
        # Parse and validate LLM response using parser utility
        next_node, msg, state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        logger.info(
            f"LLM routing decision for chat {chat_id}: next_node={next_node}"
        )
        
        return next_node, msg, state_updates
            
    except LLMProviderError as e:
        logger.error(
            f"LLM routing decision failed for chat {chat_id}: {e}",
            exc_info=True
        )
        return "greeting", "Hello! How can I help you?", {}
    except Exception as e:
        logger.error(
            f"Unexpected error during LLM routing decision for chat {chat_id}: {e}",
            exc_info=True
        )
        return "greeting", "Hello! How can I help you?", {}
