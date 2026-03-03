"""
Agent prompts package.

This package contains prompt templates for LLM-based natural language generation
and intent classification.

Modules:
- intent_prompts: Prompts for intent classification
- conversation_prompts: Prompts for conversational responses
"""

from app.agent.prompts.intent_prompts import get_intent_prompt
from app.agent.prompts.conversation_prompts import (
    get_greeting_prompt,
    get_search_prompt,
    get_booking_prompt,
    get_error_prompt,
)

__all__ = [
    "get_intent_prompt",
    "get_greeting_prompt",
    "get_search_prompt",
    "get_booking_prompt",
    "get_error_prompt",
]
