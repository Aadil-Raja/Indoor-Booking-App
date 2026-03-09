"""
Information router node - analyzes user message and extracts intent.

This node calls the LLM to understand:
- Whether user is replying to a pending question
- What information actions they want (pricing, media, property_details, code_details)
- Any property/court/date mentions in the message
"""

import logging
import json
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.prompts.information_prompts import get_information_router_prompt
from app.agent.utils.llm_logger import get_llm_logger
from app.agent.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


async def information_router(
    state: ConversationState,
    llm_provider: Any
) -> ConversationState:
    """
    Route and analyze user message for information requests.
    
    This node:
    1. Gets the router prompt with current state context
    2. Calls LLM to analyze user message
    3. Extracts structured intent (message_type, requested_actions, mentions)
    4. Stores result in flow_state["router_result"]
    
    Args:
        state: Current conversation state
        llm_provider: LLM provider for making the analysis call
        
    Returns:
        Updated state with router_result in flow_state
    """
    chat_id = state.get("chat_id")
    user_message = state.get("user_message", "")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Information router analyzing message for chat {chat_id}")
    
    try:
        # Get the router prompt with current context
        prompt = get_information_router_prompt(user_message, flow_state)
        
        logger.debug(f"Router prompt for chat {chat_id}: {prompt[:200]}...")
        
        # Call LLM to analyze the message
        llm_response = await llm_provider.generate(prompt)
        
        # Log the LLM call
        llm_logger = get_llm_logger()
        llm_logger.log_llm_call(
            node_name="information_router",
            prompt=prompt,
            response=llm_response,
            parameters=None
        )
        
        # Log full LLM response
        logger.info(f"[ROUTER LLM RESPONSE] Chat {chat_id}:\n{llm_response}")
        
        # Parse JSON response using utility function
        router_result = parse_llm_json_response(
            response=llm_response,
            fallback={
                "message_type": "unclear",
                "reply_target": None,
                "requested_actions": [],
                "mentioned_property_name": None,
                "mentioned_court_name": None,
                "unclear": True
            },
            context=f"information_router for chat {chat_id}"
        )
        
        # Log parsed result
        logger.info(f"[ROUTER PARSED RESULT] Chat {chat_id}: {json.dumps(router_result, indent=2)}")
        
        # Store router result in flow_state
        flow_state["router_result"] = router_result
        flow_state["last_node"] = "information-router"
        state["flow_state"] = flow_state
        
        logger.info(
            f"Router analysis complete for chat {chat_id}: "
            f"message_type={router_result.get('message_type')}, "
            f"actions={router_result.get('requested_actions')}"
        )
        
        return state
        
    except Exception as e:
        logger.error(f"Error in information_router for chat {chat_id}: {e}", exc_info=True)
        
        # Fallback: set unclear result
        flow_state["router_result"] = {
            "message_type": "unclear",
            "reply_target": None,
            "requested_actions": [],
            "mentioned_property_name": None,
            "mentioned_court_name": None,
            "unclear": True
        }
        flow_state["last_node"] = "information-router"
        state["flow_state"] = flow_state
        
        return state
