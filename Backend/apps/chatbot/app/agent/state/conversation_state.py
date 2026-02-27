"""
Conversation state schema for LangGraph agent.

This module defines the ConversationState TypedDict that flows through all nodes
in the LangGraph conversation flow. The state contains all information needed for
the agent to process messages and generate responses.
"""

from typing import TypedDict, List, Dict, Any, Optional


class ConversationState(TypedDict):
    """
    State object that flows through LangGraph nodes during conversation processing.
    
    This TypedDict defines all fields used by the agent to manage conversation flow,
    track booking progress, maintain context, and generate responses.
    """
    
    # Identifiers
    chat_id: str  # UUID of the chat session
    user_id: str  # UUID of the user
    owner_id: str  # UUID of the property owner
    
    # Current message
    user_message: str  # The current user message being processed
    
    # Persistent state (stored in database)
    flow_state: Dict[str, Any]  # Structured booking progress (property_id, service_id, date, time, intent, step)
    bot_memory: Dict[str, Any]  # Unstructured AI context (conversation_history, user_preferences, context)
    
    # Processing state (ephemeral, used during graph execution)
    messages: List[Dict[str, str]]  # Message history for LLM context (role, content)
    intent: Optional[str]  # Current detected intent (greeting, search, booking, faq)
    
    # Response building
    response_content: str  # The text content of the bot's response
    response_type: str  # Message type: text, button, list, media
    response_metadata: Dict[str, Any]  # Additional response data (buttons, list_items, media_url)
    
    # Metrics
    token_usage: Optional[int]  # Number of LLM tokens consumed for this message
    
    # Tool results (ephemeral, used during graph execution)
    search_results: Optional[List[Dict[str, Any]]]  # Results from property/court search tools
    availability_data: Optional[Dict[str, Any]]  # Available time slots from availability tool
    pricing_data: Optional[Dict[str, Any]]  # Pricing information from pricing tool
