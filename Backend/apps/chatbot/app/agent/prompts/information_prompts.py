"""
Information node prompts for LangChain agent-based information retrieval.

This module defines prompt templates used by the information_node to handle
all information-related queries about properties, courts, availability, pricing,
and media. The prompts guide the LangChain agent to automatically select and
execute appropriate tools based on user queries.

Requirements: 8.4, 10.1
"""

from typing import Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import PromptTemplate


# =============================================================================
# SYSTEM TEMPLATE - Information Assistant Instructions (ReAct Pattern)
# =============================================================================

SYSTEM_TEMPLATE = """You are a helpful sports facility information assistant using the ReAct (Reasoning + Acting) pattern.

You are {business_name}'s assistant, helping users find and learn about our sports facilities, courts, availability, and pricing.

IMPORTANT: You only show and provide information about {business_name}'s properties. All search results and information are specific to our facilities.

Owner Profile ID: {owner_profile_id}

Context from previous conversation:
{context}

Fuzzy Search Context:
{fuzzy_context}

Bot Memory (User Preferences):
{bot_memory}

Available tools:
{tools}

Tool names: {tool_names}

ReAct Pattern Guidelines:
You should use the following format:

Thought: Think about what information you need to answer the user's question
Action: The action to take, should be one of [search_properties, get_property_details, get_court_details, get_court_availability, get_court_pricing, get_property_media, get_court_media]
Action Input: The input to the action
Observation: The result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: The final answer to the original input question

Guidelines:
- FIRST, check bot_memory.user_preferences before asking questions or searching
- If preferred_sport exists, use it to filter search results automatically
- Example: "I see you're interested in tennis. Let me show you our tennis facilities."
- If preferred_property exists, prioritize showing information about that property
- If preferred_time exists, mention it when showing availability
- Example: "Based on your preference for morning slots, here are the morning options..."
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

Fuzzy Search Support:
- If fuzzy_context indicates a sport name correction was made, acknowledge it naturally in your response
- Common sport variations are automatically handled (e.g., "football" → "futsal", "soccer" → "futsal")
- When a fuzzy match occurs, confirm the correction with the user: "I understood you're looking for [corrected_term] (you mentioned [original_term])."
- Be friendly and natural when confirming fuzzy matches - make it conversational
- If the user seems confused by the correction, explain that we offer [corrected_term] facilities

Preference Extraction:
- Identify and extract any user preferences expressed in their message
- Store preferences in bot_memory.user_preferences:
  * preferred_sport: Sport type if mentioned (e.g., "tennis", "basketball", "futsal")
  * preferred_time: Time preference if mentioned (e.g., "morning", "afternoon", "evening")
  * preferred_property: Property ID if user expresses preference for a specific property
  * preferred_court: Court ID if user expresses preference for a specific court
- Store inferred information in bot_memory.inferred_information:
  * booking_frequency: "regular", "occasional", or "first_time" based on user's language
  * interests: List of sports or activities mentioned
  * context_notes: Any other relevant context about user's needs or interests

Important:
- Always pass owner_profile_id parameter when calling search_properties tool
- Property IDs and court IDs are integers
- Dates should be in ISO format (YYYY-MM-DD)
- Be specific about which property or court you're referring to
- If user asks about availability or pricing, make sure to get the court_id first if not provided
- Always extract and store preferences even when just providing information
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_information_prompt(
    owner_profile_id: int,
    bot_memory: Dict[str, Any],
    business_name: Optional[str] = None,
    fuzzy_context: Optional[Dict[str, Any]] = None
) -> ChatPromptTemplate:
    """
    Create a context-aware prompt for the information agent using ReAct pattern.
    
    This function builds a ChatPromptTemplate that includes:
    - System instructions for the information assistant with ReAct pattern
    - Business name personalization for the assistant identity
    - Context that bot only shows owner's properties
    - Context extracted from bot_memory (previous searches, preferences)
    - Fuzzy search context for sport name corrections with confirmation prompts
    - Preference extraction instructions for user_preferences and inferred_information
    - Message placeholders for chat history and agent scratchpad
    - Partial variables for owner_profile_id, business_name, context, fuzzy_context, and bot_memory
    
    The prompt is designed to work with LangChain's create_react_agent
    and includes all necessary placeholders for ReAct agent execution.
    
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
                    "preferred_sport": "tennis",
                    "preferred_time": "morning",
                    "preferred_property": 6,
                    "preferred_court": 23
                },
                "inferred_information": {
                    "booking_frequency": "regular",
                    "interests": ["tennis", "basketball"],
                    "context_notes": "Prefers morning slots"
                }
            }
        business_name: Optional business name for personalization (e.g., "ABC Sports Center")
            If not provided, defaults to "our facility"
        fuzzy_context: Optional dictionary with fuzzy search information
            {
                "fuzzy_match": True,
                "original_term": "football",
                "corrected_term": "futsal",
                "confirmation_message": "I understood you're looking for futsal..."
            }
            
    Returns:
        ChatPromptTemplate with partial variables injected
        
    Example:
        >>> bot_memory = {
        ...     "context": {"last_search_results": ["6", "12"]},
        ...     "user_preferences": {"preferred_sport": "tennis", "preferred_time": "morning"}
        ... }
        >>> fuzzy_context = {"fuzzy_match": True, "original_term": "football"}
        >>> prompt = create_information_prompt(
        ...     owner_profile_id=1,
        ...     bot_memory=bot_memory,
        ...     business_name="ABC Sports Center",
        ...     fuzzy_context=fuzzy_context
        ... )
        >>> # Use with LangChain ReAct agent
        >>> agent = create_react_agent(llm, tools, prompt)
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
    
    # Build fuzzy context string
    fuzzy_context = fuzzy_context or {}
    if fuzzy_context.get("fuzzy_match"):
        fuzzy_str = (
            f"Sport name correction applied: '{fuzzy_context.get('original_term')}' "
            f"→ '{fuzzy_context.get('corrected_term')}'"
        )
    else:
        fuzzy_str = "No fuzzy corrections applied"
    
    # Format bot_memory for display in prompt
    bot_memory_str = f"""
User Preferences: {bot_memory.get('user_preferences', {})}
Inferred Information: {bot_memory.get('inferred_information', {})}
"""
    
    # Use business_name or default to "our facility"
    business_name_str = business_name or "our facility"
    
    # Create prompt template with message placeholders for ReAct pattern
    # Note: agent_scratchpad must be a MessagesPlaceholder for create_react_agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Inject owner_profile_id, business_name, context, fuzzy_context, and bot_memory as partial variables
    return prompt.partial(
        owner_profile_id=str(owner_profile_id),
        business_name=business_name_str,
        context=context,
        fuzzy_context=fuzzy_str,
        bot_memory=bot_memory_str
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
