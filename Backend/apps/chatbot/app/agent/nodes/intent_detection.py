"""
Intent detection node for LangGraph conversation management.

This module implements the intent_detection node that uses LLM to make explicit
routing decisions. The LLM analyzes the user message and returns a next_node
decision, eliminating rule-based transitions.

The next_node decision is used to route the conversation to the appropriate handler
node in the LangGraph flow.

Requirements: 2.1, 2.2, 2.3, 2.4
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
from app.agent.state.llm_response_parser import parse_llm_response

logger = logging.getLogger(__name__)


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Determine next_node using LLM-based routing decision.
    
    This node analyzes the user's message using the LLM to determine which
    handler node should process the message next. It uses the LLM to make
    an explicit routing decision, eliminating rule-based transitions.
    
    Implements Requirements:
    - 2.1: LLM SHALL return next_node field in response
    - 2.2: Remove rule-based logic for intent determination
    - 2.3: LLM makes routing decisions
    - 2.4: Route to node specified by LLM's next_node decision
    
    Args:
        state: ConversationState containing the user message
        llm_provider: Optional LLMProvider for routing decision
        
    Returns:
        ConversationState: State with next_node decision and updated flow_state
        
    Example:
        state = {
            "user_message": "I want to book a tennis court",
            "flow_state": {},
            ...
        }
        
        result = await intent_detection(state, llm_provider=provider)
        # result["next_node"] = "booking"
        # result["flow_state"]["current_intent"] = "booking"
    """
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
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
    
    # Store next_node in state for routing (this is what the graph will use)
    state["next_node"] = next_node
    
    # Apply state updates to flow_state
    if "flow_state" in state_updates:
        flow_state.update(state_updates["flow_state"])
        state["flow_state"] = flow_state
    
    # Apply state updates to bot_memory
    if "bot_memory" in state_updates:
        bot_memory = state.get("bot_memory", {})
        bot_memory.update(state_updates["bot_memory"])
        state["bot_memory"] = bot_memory
    
    # Store the LLM's message (optional, for debugging or transition messages)
    if message:
        state["response_content"] = message
    
    logger.info(
        f"Routing decision for chat {state['chat_id']}: next_node={next_node}"
    )
    
    return state


async def _llm_routing_decision(
    message: str, 
    llm_provider: LLMProvider,
    chat_id: str
) -> tuple[str, str, dict]:
    """
    Use LLM to make routing decision.
    
    This function uses the INTENT_ROUTING_PROMPT template to get the LLM's
    routing decision. The LLM returns a structured JSON response containing
    next_node, message, and state_updates.
    
    Implements Requirements:
    - 2.1: LLM SHALL return next_node field
    - 2.2: Remove rule-based logic for intent determination
    - 2.3: LLM makes routing decisions
    - 2.4: Route to node specified by LLM's next_node decision
    
    Args:
        message: Original user message
        llm_provider: LLMProvider instance for creating ChatOpenAI
        chat_id: Chat ID for logging
        
    Returns:
        Tuple of (next_node, message, state_updates)
        
    Note:
        If LLM routing fails or returns invalid response, defaults to "greeting"
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
