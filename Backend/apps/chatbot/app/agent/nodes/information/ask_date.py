"""
Ask date node - prompts user to select a date for availability check.

This node is called when the user wants to check availability but hasn't
provided a date yet. It sets awaiting_input and provides a user-friendly
prompt with examples in multiple formats and languages.
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


# Date selection prompts
DATE_SELECTION_PROMPT = (
    "Which date would you like to check?\n\n"
    "📅 Relative dates: today, tomorrow, parso, next Monday\n"
    "📅 Exact date: 2026-03-16 or 16 March 2026\n"
    "📅 Urdu: aaj, kal, parso\n\n"
    "You can also specify time:\n"
    "🕐 Time period: morning, afternoon, evening, night\n"
    "🕐 Exact slot: 6 to 7 PM, 18:00 to 19:00"
)

DATE_INVALID_PROMPT = (
    "I couldn't understand that date. Please try again.\n\n"
    "📅 Relative dates: today, tomorrow, parso, next Monday\n"
    "📅 Exact date: 2026-03-16 or 16 March 2026\n\n"
    "You can also specify time:\n"
    "🕐 Time period: morning, afternoon, evening, night\n"
    "🕐 Exact slot: 6 to 7 PM, 18:00 to 19:00"
)


async def ask_date(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Ask user to select a date for availability check.
    
    This node:
    1. Checks if date is already selected
    2. If not, sets awaiting_input = "date_selection"
    3. Provides user-friendly prompt with examples
    4. Handles invalid date responses
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with awaiting_input set and bot_response
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Asking for date selection for chat {chat_id}")
    
    # Check if we're handling an invalid date response
    validation_error = flow_state.get("validation_error")
    
    if validation_error == "invalid_date":
        # User provided invalid date - show error prompt
        bot_response = DATE_INVALID_PROMPT
        logger.info(f"Showing invalid date prompt for chat {chat_id}")
    else:
        # First time asking for date - show normal prompt
        bot_response = DATE_SELECTION_PROMPT
        logger.info(f"Showing date selection prompt for chat {chat_id}")
    
    # Set awaiting_input
    flow_state["awaiting_input"] = "date_selection"
    flow_state["bot_response"] = bot_response
    flow_state["last_node"] = "information-ask_date"
    
    # Clear validation error after showing message
    flow_state["validation_error"] = None
    
    state["flow_state"] = flow_state
    
    # Log the prompt
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        node_name="ask_date",
        prompt="[No LLM call - prompts user for date selection]",
        response=bot_response,
        parameters=None
    )
    
    logger.info(f"Date selection prompt set for chat {chat_id}")
    
    return state
