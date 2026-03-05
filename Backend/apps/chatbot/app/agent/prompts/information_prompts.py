"""
Information node prompts for LangChain agent-based information retrieval.

This module defines prompt templates used by the information_node to handle
all information-related queries about properties, courts, availability, pricing,
and media. The prompts guide the LangChain agent to automatically select and
execute appropriate tools based on user queries.

Requirements: 8.4, 10.1
"""

from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


# =============================================================================
# SYSTEM TEMPLATE - Information Assistant Instructions
# =============================================================================

SYSTEM_TEMPLATE = """You are a helpful sports facility information assistant.

You help users find and learn about sports facilities, courts, availability, and pricing.

Owner Profile ID: {owner_profile_id}

Context from previous conversation:
{context}

Available tools:
- search_properties: Search for facilities by location and sport type
- get_property_details: Get detailed information about a specific property
- get_court_details: Get details about a specific court
- get_court_availability: Check available time slots for a court
- get_court_pricing: Get pricing information for a court
- get_property_media: Get photos/videos of a property
- get_court_media: Get photos/videos of a court

Guidelines:
- Use tools to get accurate, up-to-date information
- You can call multiple tools if needed to answer the user's question
- Reference previous search results from context when user says "that property", "the last one", or "the first one"
- When user references results by position (first, second, etc.), use the property IDs from last_search_results
- Be conversational and helpful
- If you don't have enough information, ask clarifying questions
- Present information in a clear, organized way
- When showing multiple results, present them in a numbered list
- Include relevant details like property name, location, sport type, and pricing when available
- If a query requires multiple pieces of information, gather all data before responding

Important:
- Always pass owner_profile_id parameter when calling search_properties tool
- Property IDs and court IDs are integers
- Dates should be in ISO format (YYYY-MM-DD)
- Be specific about which property or court you're referring to
- If user asks about availability or pricing, make sure to get the court_id first if not provided
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_information_prompt(
    owner_profile_id: int,
    bot_memory: Dict[str, Any]
) -> ChatPromptTemplate:
    """
    Create a context-aware prompt for the information agent.
    
    This function builds a ChatPromptTemplate that includes:
    - System instructions for the information assistant
    - Context extracted from bot_memory (previous searches, preferences)
    - Message placeholders for chat history and agent scratchpad
    - Partial variables for owner_profile_id and context
    
    The prompt is designed to work with LangChain's create_openai_functions_agent
    and includes all necessary placeholders for agent execution.
    
    Args:
        owner_profile_id: The owner profile ID to filter properties by
        bot_memory: Dictionary containing conversation context and user preferences
            Expected structure:
            {
                "context": {
                    "last_search_results": ["6", "12", "15"],  # Property IDs
                    "last_search_params": {"sport_type": "tennis", "city": "NYC"},
                    "last_viewed_property": 6,
                    "last_viewed_court": 23,
                    "last_availability_check": {"court_id": 23, "date": "2026-03-10"}
                },
                "user_preferences": {
                    "preferred_sport": "tennis"
                }
            }
            
    Returns:
        ChatPromptTemplate with partial variables injected
        
    Example:
        >>> bot_memory = {
        ...     "context": {"last_search_results": ["6", "12"]},
        ...     "user_preferences": {"preferred_sport": "tennis"}
        ... }
        >>> prompt = create_information_prompt(
        ...     owner_profile_id=1,
        ...     bot_memory=bot_memory
        ... )
        >>> # Use with LangChain agent
        >>> agent = create_openai_functions_agent(llm, tools, prompt)
    """
    # Extract context from bot_memory
    context_parts = []
    
    # Add last search results
    if bot_memory.get("context", {}).get("last_search_results"):
        results = bot_memory["context"]["last_search_results"]
        context_parts.append(f"Last search returned property IDs: {', '.join(results)}")
    
    # Add last search parameters
    if bot_memory.get("context", {}).get("last_search_params"):
        params = bot_memory["context"]["last_search_params"]
        param_strs = []
        if params.get("sport_type"):
            param_strs.append(f"sport: {params['sport_type']}")
        if params.get("city"):
            param_strs.append(f"city: {params['city']}")
        if param_strs:
            context_parts.append(f"Last search was for: {', '.join(param_strs)}")
    
    # Add user preferences
    if bot_memory.get("user_preferences", {}).get("preferred_sport"):
        sport = bot_memory["user_preferences"]["preferred_sport"]
        context_parts.append(f"User prefers: {sport}")
    
    # Add last viewed property
    if bot_memory.get("context", {}).get("last_viewed_property"):
        prop_id = bot_memory["context"]["last_viewed_property"]
        context_parts.append(f"Last viewed property ID: {prop_id}")
    
    # Add last viewed court
    if bot_memory.get("context", {}).get("last_viewed_court"):
        court_id = bot_memory["context"]["last_viewed_court"]
        context_parts.append(f"Last viewed court ID: {court_id}")
    
    # Add last availability check
    if bot_memory.get("context", {}).get("last_availability_check"):
        avail = bot_memory["context"]["last_availability_check"]
        context_parts.append(
            f"Last availability check: court {avail.get('court_id')} on {avail.get('date')}"
        )
    
    # Build context string
    context = "\n".join(context_parts) if context_parts else "No previous context"
    
    # Create prompt template with message placeholders
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Inject owner_profile_id and context as partial variables
    return prompt.partial(
        owner_profile_id=str(owner_profile_id),
        context=context
    )


def extract_context_summary(bot_memory: Dict[str, Any]) -> str:
    """
    Extract a human-readable summary of context from bot_memory.
    
    This is a utility function that can be used for logging or debugging
    to understand what context is available in bot_memory.
    
    Args:
        bot_memory: Dictionary containing conversation context
        
    Returns:
        Human-readable string summarizing the context
        
    Example:
        >>> bot_memory = {
        ...     "context": {"last_search_results": ["6", "12"]},
        ...     "user_preferences": {"preferred_sport": "tennis"}
        ... }
        >>> summary = extract_context_summary(bot_memory)
        >>> print(summary)
        Context: 2 properties from last search, prefers tennis
    """
    parts = []
    
    # Search results
    if bot_memory.get("context", {}).get("last_search_results"):
        count = len(bot_memory["context"]["last_search_results"])
        parts.append(f"{count} properties from last search")
    
    # Preferences
    if bot_memory.get("user_preferences", {}).get("preferred_sport"):
        sport = bot_memory["user_preferences"]["preferred_sport"]
        parts.append(f"prefers {sport}")
    
    # Last viewed
    if bot_memory.get("context", {}).get("last_viewed_property"):
        parts.append("viewed a property")
    
    if not parts:
        return "No context available"
    
    return "Context: " + ", ".join(parts)
