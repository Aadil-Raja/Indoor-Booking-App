"""Agent state definitions for LangGraph conversation flow."""

from app.agent.state.conversation_state import ConversationState
from app.agent.state.memory_manager import update_bot_memory

__all__ = ["ConversationState", "update_bot_memory"]
