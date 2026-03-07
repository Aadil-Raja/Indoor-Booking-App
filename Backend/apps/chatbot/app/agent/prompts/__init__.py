"""
Agent prompts package.

This package contains prompt templates for LLM-based natural language generation
and intent classification.

Modules:
- intent_prompts: Prompts for intent classification
- conversation_prompts: Prompts for conversational responses
- information_prompts: Prompts for information node agent
"""

from app.agent.prompts.intent_prompts import get_routing_prompt
from app.agent.prompts.conversation_prompts import (
    get_greeting_prompt,
    get_search_prompt,
    get_booking_prompt,
    get_error_prompt,
)
from app.agent.prompts.information_prompts import (
    create_information_prompt,
    extract_context_summary,
)

__all__ = [
    "get_routing_prompt",
    "get_greeting_prompt",
    "get_search_prompt",
    "get_booking_prompt",
    "get_error_prompt",
    "create_information_prompt",
    "extract_context_summary",
]
