"""
Conversation state schema for LangGraph agent.

This module defines the ConversationState TypedDict that flows through all nodes
in the LangGraph conversation flow. The state contains all information needed for
the agent to process messages and generate responses.

Updated for LLM-driven conversation flow with structured flow_state and bot_memory.
"""

from typing import TypedDict, List, Dict, Any, Optional


class FlowState(TypedDict, total=False):
    """
    Temporary conversation state containing current intent, booking progress, and cached data.
    
    This state is cleared after booking completion or cancellation.
    All fields are optional to support incremental population during conversation.
    """
    current_intent: str  # "booking" | "information" | "greeting"
    property_id: Optional[int]  # Selected property ID
    property_name: Optional[str]  # Selected property name
    court_id: Optional[int]  # Selected court ID (previously service_id)
    court_name: Optional[str]  # Selected court name
    date: Optional[str]  # Booking date in YYYY-MM-DD format
    time_slot: Optional[str]  # Time slot in HH:MM-HH:MM format
    booking_step: Optional[str]  # "property_selected" | "court_selected" | "date_selected" | "time_selected" | "confirming"
    owner_properties: Optional[List[Dict[str, Any]]]  # Cached list of owner's properties
    context: Dict[str, Any]  # Additional contextual information


class BotMemory(TypedDict, total=False):
    """
    Persistent storage for user preferences and inferred information across conversations.
    
    This memory persists across conversation sessions and is used to avoid redundant questions.
    """
    conversation_history: List[Dict[str, str]]  # Historical messages for context
    user_preferences: Dict[str, Any]  # User preferences (preferred_time, preferred_sport, preferred_property, preferred_court)
    inferred_information: Dict[str, Any]  # Inferred data (booking_frequency, interests, context_notes)


class ConversationState(TypedDict):
    """
    State object that flows through LangGraph nodes during conversation processing.
    
    This TypedDict defines all fields used by the agent to manage conversation flow,
    track booking progress, maintain context, and generate responses.
    
    Updated for LLM-driven conversation flow with explicit next_node routing.
    """
    
    # Identifiers
    chat_id: str  # UUID of the chat session
    user_id: str  # Integer user ID
    owner_profile_id: str  # Integer owner profile ID
    
    # Current message
    user_message: str  # The current user message being processed
    
    # Persistent state (stored in database)
    flow_state: FlowState  # Structured temporary state (current_intent, property_id, court_id, date, time_slot, booking_step, owner_properties, context)
    bot_memory: BotMemory  # Persistent AI memory (conversation_history, user_preferences, inferred_information)
    
    # Processing state (ephemeral, used during graph execution)
    messages: List[Dict[str, str]]  # Message history for LLM context (role, content)
    intent: Optional[str]  # Current detected intent (greeting, search, booking, faq) - DEPRECATED: use flow_state.current_intent
    
    # Response building
    response_content: str  # The text content of the bot's response
    response_type: str  # Message type: text, button, list, media
    response_metadata: Dict[str, Any]  # Structured data for responses (buttons, list_items, media_url, properties, courts, slots)
    
    # Metrics
    token_usage: Optional[int]  # Number of LLM tokens consumed for this message
    
    # Tool results (ephemeral, used during graph execution)
    search_results: Optional[List[Dict[str, Any]]]  # Results from property/court search tools
    availability_data: Optional[Dict[str, Any]]  # Available time slots from availability tool
    pricing_data: Optional[Dict[str, Any]]  # Pricing information from pricing tool
