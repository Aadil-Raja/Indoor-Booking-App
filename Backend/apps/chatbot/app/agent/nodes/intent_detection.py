"""
Intent detection node for LangGraph conversation management.

This module implements the intent_detection node that classifies user messages
into one of four intents: greeting, search, booking, or faq. It uses rule-based
pattern matching for common intents and falls back to LLM for complex cases.

The detected intent is used to route the conversation to the appropriate handler
node in the LangGraph flow.

Requirements: 6.2, 21.1-21.6
"""

from typing import Optional
import logging
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.prompts.intent_prompts import get_intent_prompt

logger = logging.getLogger(__name__)


# Intent classification patterns
GREETING_PATTERNS = [
    r'\b(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|day))\b',
    r'\b(howdy|hiya|sup|yo)\b',
    r'^(hi|hello|hey|heyyy?)[\s!.]*$',
]

SEARCH_PATTERNS = [
    # General search patterns
    r'\b(search|find|looking\s+for|show\s+me|available)\b',
    r'\b(what|which|where).*(facilities|courts|properties|venues)\b',
    r'\b(tennis|basketball|badminton|squash|volleyball).*(court|facility)\b',
    r'\b(indoor|sports).*(near|in|at)\b',
    
    # Availability patterns
    r'\b(when\s+is|check|see).*(available|availability|open|free)\b',
    r'\b(available|availability).*(slot|time|court|facility)\b',
    r'\b(is\s+there|are\s+there).*(available|open|free)\b',
    
    # Pricing patterns
    r'\b(how\s+much|what\'?s?\s+the\s+price|cost|pricing|rate)\b',
    r'\b(price|prices|pricing).*(court|facility|hour)\b',
    r'\b(hourly|per\s+hour).*(rate|price|cost)\b',
    
    # Media patterns
    r'\b(show\s+me|see|view).*(photo|picture|image|pic)\b',
    r'\b(photo|picture|image|pic).*(of|for)\b',
    r'\b(gallery|media|video)\b',
]

BOOKING_PATTERNS = [
    r'\b(book|reserve|schedule|make\s+a\s+booking)\b',
    r'\b(i\s+want\s+to|i\'d\s+like\s+to|can\s+i).*(book|reserve)\b',
    r'\b(appointment|reservation)\b',
]

FAQ_PATTERNS = [
    r'\b(help|what\s+is|explain|tell\s+me\s+about)\b',
    r'\b(question|info|information|details)\b',
    r'\b(payment|refund|policy|cancel)\b',
]


async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Classify user intent using rule-based matching and LLM fallback.
    
    This node analyzes the user's message to determine their intent, which is
    used to route the conversation to the appropriate handler node. It first
    attempts rule-based classification using keyword patterns, then falls back
    to LLM for complex or ambiguous messages.
    
    Implements Requirements:
    - 6.2: Intent_Detection node that classifies user intent
    - 21.1: Route greeting messages to Greeting node
    - 21.2: Route facility/sports questions to Information node (LangChain agent)
    - 21.3: Route booking intent to Booking_Subgraph
    - 21.4: Route general questions to FAQ node
    - 21.5: Use LLM_Provider for intent classification when rule-based matching fails
    - 21.6: Handle typos and informal language
    
    Args:
        state: ConversationState containing the user message
        llm_provider: Optional LLMProvider for fallback classification
        
    Returns:
        ConversationState: State with detected intent and updated flow_state
        
    Example:
        state = {
            "user_message": "I want to book a tennis court",
            "flow_state": {},
            ...
        }
        
        result = await intent_detection(state, llm_provider=provider)
        # result["intent"] = "booking"
        # result["flow_state"]["intent"] = "booking"
    """
    user_message = state["user_message"]
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Detecting intent for chat {state['chat_id']} - "
        f"message_preview={user_message[:50]}..."
    )
    
    # Normalize message for pattern matching
    normalized_message = user_message.lower().strip()
    
    # Rule-based intent detection
    intent = _rule_based_classification(normalized_message)
    
    # If rule-based classification is uncertain, use LLM fallback
    if intent == "unknown" and llm_provider:
        logger.debug(
            f"Rule-based classification uncertain for chat {state['chat_id']}, "
            f"using LLM fallback"
        )
        intent = await _llm_intent_classification(
            user_message, 
            llm_provider,
            state['chat_id']
        )
    elif intent == "unknown":
        # No LLM provider available, default to FAQ
        logger.warning(
            f"No LLM provider available for fallback classification, "
            f"defaulting to FAQ for chat {state['chat_id']}"
        )
        intent = "faq"
    
    # Update state with detected intent
    state["intent"] = intent
    
    # Update flow_state with detected intent (Requirement 6.2)
    flow_state["intent"] = intent
    state["flow_state"] = flow_state
    
    logger.info(
        f"Intent detected for chat {state['chat_id']}: {intent}"
    )
    
    return state


def _rule_based_classification(message: str) -> str:
    """
    Classify intent using rule-based pattern matching.
    
    This function checks the message against predefined patterns for each
    intent type. It returns the first matching intent or "unknown" if no
    patterns match.
    
    The order of checking is important:
    1. Greeting - checked first as greetings are usually short and distinct
    2. Booking - checked before search as booking implies search
    3. Search - checked after booking to avoid false positives
    4. FAQ - checked last as it's the most general category
    
    Args:
        message: Normalized (lowercase, stripped) user message
        
    Returns:
        Intent string: "greeting", "search", "booking", "faq", or "unknown"
    """
    # Check greeting patterns
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            logger.debug(f"Matched greeting pattern: {pattern}")
            return "greeting"
    
    # Check booking patterns (before search to prioritize booking intent)
    for pattern in BOOKING_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            logger.debug(f"Matched booking pattern: {pattern}")
            return "booking"
    
    # Check search patterns
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            logger.debug(f"Matched search pattern: {pattern}")
            return "search"
    
    # Check FAQ patterns
    for pattern in FAQ_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            logger.debug(f"Matched FAQ pattern: {pattern}")
            return "faq"
    
    # No patterns matched
    logger.debug("No rule-based patterns matched")
    return "unknown"


async def _llm_intent_classification(
    message: str, 
    llm_provider: LLMProvider,
    chat_id: str
) -> str:
    """
    Use LLM to classify intent when rule-based matching fails.
    
    This function uses the INTENT_CLASSIFICATION_PROMPT template to classify
    the user's intent into one of the four supported categories. It uses LangChain's
    ChatOpenAI wrapper with a low temperature for consistent classification and 
    validates the LLM's response.
    
    Implements Requirement 21.5: Use LLM_Provider for intent classification
    when rule-based matching fails.
    Implements Requirement 9.1: Use ChatOpenAI from langchain-openai
    Implements Requirement 9.2: Use LangChain agents instead of direct OpenAI calls
    Implements Requirement 9.3: No tools needed for intent detection
    
    Args:
        message: Original user message
        llm_provider: LLMProvider instance for creating ChatOpenAI
        chat_id: Chat ID for logging
        
    Returns:
        Intent string: "greeting", "search", "booking", or "faq"
        
    Note:
        If LLM classification fails or returns invalid intent, defaults to "faq"
    """
    # Get formatted prompt from template
    prompt = get_intent_prompt(message, prompt_type="default")
    
    try:
        # Create LangChain ChatOpenAI instance using wrapper
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.0,  # Low temperature for consistent classification
            max_tokens=10     # Only need a single word response
        )
        
        # Call LLM using LangChain's ainvoke method
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Extract and validate intent from response
        intent = response.content.strip().lower()
        
        # Validate intent is one of the supported types
        valid_intents = ["greeting", "search", "booking", "faq"]
        if intent in valid_intents:
            logger.info(
                f"LLM classified intent as '{intent}' for chat {chat_id}"
            )
            return intent
        else:
            logger.warning(
                f"LLM returned invalid intent '{intent}' for chat {chat_id}, "
                f"defaulting to 'faq'"
            )
            return "faq"
            
    except LLMProviderError as e:
        logger.error(
            f"LLM intent classification failed for chat {chat_id}: {e}",
            exc_info=True
        )
        return "faq"
    except Exception as e:
        logger.error(
            f"Unexpected error during LLM intent classification for chat {chat_id}: {e}",
            exc_info=True
        )
        return "faq"
