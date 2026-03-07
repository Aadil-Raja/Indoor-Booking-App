"""
Intent detection node - uses LLM to decide routing.

Simple routing only:
- "greeting" for greetings
- "information" for questions
- "booking" for reservations
"""

from typing import Optional
import logging
import json

from langchain_core.messages import HumanMessage

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.intent_prompts import get_routing_prompt

logger = logging.getLogger(__name__)


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Use LLM to decide routing (greeting/information/booking).
    
    Uses conversation context for better routing of ambiguous messages.
    Falls back to "greeting" if LLM fails.
    """
    user_message = state["user_message"]
    recent_messages = state.get("messages", [])
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Determining routing for chat {state['chat_id']} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Use LLM for routing decision
    if llm_provider:
        next_node = await _llm_routing_decision(
            user_message=user_message,
            recent_messages=recent_messages,
            last_node=flow_state.get("last_node"),
            current_intent=flow_state.get("current_intent"),
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
    current_intent: str,
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
        last_node=last_node,
        current_intent=current_intent
    )
    
    try:
        # Create LangChain ChatOpenAI instance
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.0,  # Consistent routing
            max_tokens=50     # Just need the node name
        )
        
        # Call LLM
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Parse JSON response
        try:
            llm_response = json.loads(response.content.strip())
            next_node = llm_response.get("next_node", "greeting")
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse LLM response for chat {chat_id}: {e}. "
                f"Response: {response.content[:200]}"
            )
            return "greeting"
        
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
