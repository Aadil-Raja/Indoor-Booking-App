"""
FAQ handler node for LangGraph conversation management.

This module implements the faq_handler node that responds to general questions
and unknown intents. It uses the LLM provider to generate contextual, helpful
responses for questions about pricing, policies, general information, and
handles unknown intents gracefully.

Requirements: 6.1, 21.4
"""

from typing import Optional, Dict, Any
import logging

from ..state.conversation_state import ConversationState
from ...services.llm.base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


# FAQ prompt template for generating contextual responses
FAQ_RESPONSE_PROMPT = """You are a helpful sports booking assistant. A user has asked a question or made a statement that doesn't fit into specific categories like searching for facilities or making bookings.

User's message: "{user_message}"

Context about the conversation:
- This is a sports facility booking system
- Users can search for indoor sports facilities (tennis, basketball, badminton, squash, volleyball)
- Users can book courts and facilities
- The system handles pricing, availability, and reservations

Please provide a helpful, friendly, and concise response to the user's message. If the question is about:
- Pricing: Explain that pricing varies by facility and time slot, and they can see prices when searching for facilities
- Policies: Provide general information about booking policies (cancellation, refunds, etc.)
- How to use the system: Guide them on how to search for facilities or make bookings
- Unknown/unclear intent: Politely ask for clarification and suggest what you can help with

Keep your response conversational, friendly, and under 3 sentences. Do not make up specific prices or policies."""


async def faq_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle general questions and unknown intents with LLM-generated responses.
    
    This node processes FAQ-type questions and unknown intents by using the LLM
    provider to generate contextual, helpful responses. It handles:
    - Questions about pricing and policies
    - General information requests
    - How-to questions about using the system
    - Unknown or unclear intents
    
    The node uses the LLM to generate natural, conversational responses that
    guide users toward the system's capabilities. If the LLM is unavailable,
    it falls back to a generic helpful message.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with FAQ handler node
    - 21.4: Route general questions to FAQ node
    
    Args:
        state: ConversationState containing user message and context
        llm_provider: Optional LLMProvider for generating responses
        
    Returns:
        ConversationState: State with response_content, response_type, and
                          response_metadata set
        
    Example:
        # Pricing question
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "How much does it cost to book a tennis court?",
            "bot_memory": {},
            ...
        }
        result = await faq_handler(state, llm_provider)
        # result["response_content"] = "Pricing varies by facility and time slot..."
        
        # Unknown intent
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "What's the weather like?",
            "bot_memory": {},
            ...
        }
        result = await faq_handler(state, llm_provider)
        # result["response_content"] = "I'm a sports booking assistant..."
    """
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    
    logger.info(
        f"Processing FAQ for chat {chat_id} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Try to generate LLM response
    if llm_provider:
        response = await _generate_llm_response(
            user_message=user_message,
            llm_provider=llm_provider,
            chat_id=chat_id,
            bot_memory=state.get("bot_memory", {})
        )
        
        # Track token usage if available
        if response.get("token_usage"):
            state["token_usage"] = response["token_usage"]
    else:
        # Fallback to generic response if no LLM provider
        logger.warning(
            f"No LLM provider available for FAQ handler in chat {chat_id}, "
            f"using fallback response"
        )
        response = _generate_fallback_response(user_message)
    
    # Set response in state
    state["response_content"] = response["content"]
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(
        f"FAQ handler completed for chat {chat_id} - "
        f"response_length={len(response['content'])}"
    )
    
    return state


async def _generate_llm_response(
    user_message: str,
    llm_provider: LLMProvider,
    chat_id: str,
    bot_memory: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a contextual response using the LLM provider.
    
    This function constructs a prompt with context about the system and the
    user's message, then calls the LLM to generate a helpful response.
    
    Args:
        user_message: The user's question or message
        llm_provider: LLMProvider instance for generating responses
        chat_id: Chat ID for logging
        bot_memory: Bot memory containing conversation context
        
    Returns:
        Dictionary with 'content' (response text) and optional 'token_usage'
        
    Note:
        If LLM generation fails, falls back to generic response
    """
    try:
        # Construct prompt with user message
        prompt = FAQ_RESPONSE_PROMPT.format(user_message=user_message)
        
        logger.debug(f"Generating LLM response for FAQ in chat {chat_id}")
        
        # Call LLM with moderate temperature for natural responses
        response_text = await llm_provider.generate(
            prompt=prompt,
            max_tokens=150,
            temperature=0.7
        )
        
        # Count tokens for tracking
        try:
            prompt_tokens = llm_provider.count_tokens(prompt)
            response_tokens = llm_provider.count_tokens(response_text)
            total_tokens = prompt_tokens + response_tokens
        except Exception as e:
            logger.warning(f"Failed to count tokens for chat {chat_id}: {e}")
            total_tokens = None
        
        logger.info(
            f"LLM response generated for chat {chat_id} - "
            f"tokens={total_tokens}"
        )
        
        return {
            "content": response_text.strip(),
            "token_usage": total_tokens
        }
        
    except LLMProviderError as e:
        logger.error(
            f"LLM provider error generating FAQ response for chat {chat_id}: {e}",
            exc_info=True
        )
        return _generate_fallback_response(user_message)
        
    except Exception as e:
        logger.error(
            f"Unexpected error generating FAQ response for chat {chat_id}: {e}",
            exc_info=True
        )
        return _generate_fallback_response(user_message)


def _generate_fallback_response(user_message: str) -> Dict[str, Any]:
    """
    Generate a generic fallback response when LLM is unavailable.
    
    This function provides a helpful response that guides users toward the
    system's main capabilities without requiring LLM generation.
    
    Args:
        user_message: The user's message (used for basic keyword detection)
        
    Returns:
        Dictionary with 'content' (response text) and no token_usage
    """
    message_lower = user_message.lower()
    
    # Provide context-specific fallback based on keywords
    if any(word in message_lower for word in ["price", "cost", "how much", "payment"]):
        response = (
            "Pricing varies by facility and time slot. "
            "You can see specific prices when you search for facilities and select a time. "
            "Would you like me to help you search for available facilities?"
        )
    elif any(word in message_lower for word in ["cancel", "refund", "policy"]):
        response = (
            "For information about cancellation and refund policies, "
            "please contact the specific facility you're interested in. "
            "Can I help you search for facilities or make a booking?"
        )
    elif any(word in message_lower for word in ["help", "how", "what can"]):
        response = (
            "I can help you search for indoor sports facilities and make bookings. "
            "Just tell me what sport you're interested in or ask me to show available facilities!"
        )
    else:
        # Generic unknown intent response
        response = (
            "I'm here to help you find and book indoor sports facilities. "
            "I can search for tennis, basketball, badminton, squash, and volleyball courts. "
            "What would you like to do?"
        )
    
    logger.debug(f"Generated fallback response for message: {user_message[:50]}...")
    
    return {
        "content": response,
        "token_usage": None
    }
