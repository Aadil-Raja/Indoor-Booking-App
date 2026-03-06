"""
Intent classification prompts for LLM-based routing decisions.

This module defines prompt templates used by the intent_detection node to make
explicit routing decisions. The LLM determines the next_node to route to based
on the user's message, eliminating rule-based transitions.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

from typing import Dict, Any

INTENT_ROUTING_PROMPT = """You are a routing assistant for a sports facility booking chatbot. Your task is to analyze the user's message and determine which conversation handler should process it next.

**Available Handlers (next_node options):**

1. **greeting** - For greetings and conversation starters
   - Examples: "hi", "hello", "good morning", "hey there", "what's up"
   - Use when: User is starting or restarting a conversation
   
2. **information** - For all informational queries about facilities, courts, availability, pricing, and general questions
   - Examples: "show me tennis courts", "what courts are available", "how much does it cost", "tell me about your facilities", "what are your hours"
   - Use when: User wants to search, browse, or learn about facilities, courts, pricing, or policies
   - Note: This handler uses a LangChain agent with access to all information tools
   
3. **booking** - For booking, reserving, or scheduling facilities
   - Examples: "I want to book a court", "reserve a tennis court for tomorrow", "can I schedule a booking", "make a reservation", "book it"
   - Use when: User explicitly wants to create a booking or reservation

**Routing Rules:**

- FIRST, check bot_memory.user_preferences and bot_memory.inferred_information
- If user has booking_frequency="regular" and message is vague, assume they want to book again
- If preferred_sport exists and user mentions that sport, route to booking if intent is unclear
- If the message contains booking-related words (book, reserve, schedule, appointment, reservation), route to **booking**
- If the message is about finding, searching, browsing facilities, or asking questions (pricing, hours, policies, availability), route to **information**
- If the message is a simple greeting or conversation starter, route to **greeting**
- When in doubt between information and booking, prefer **booking** if there's clear intent to make a reservation
- Handle typos, informal language, and abbreviations gracefully

**User Message:**
"{message}"

**Bot Memory (User Preferences):**
{bot_memory}

**Preference Extraction:**
While routing, identify and extract any user preferences expressed in their message:
- Store preferences in bot_memory.user_preferences:
  * preferred_sport: Sport type if mentioned (e.g., "tennis", "basketball", "futsal")
  * preferred_time: Time preference if mentioned (e.g., "morning", "afternoon", "evening")
  * preferred_property: Property ID if user expresses preference
  * preferred_court: Court ID if user expresses preference
- Store inferred information in bot_memory.inferred_information:
  * booking_frequency: "regular", "occasional", or "first_time" based on user's language
  * interests: List of sports or activities mentioned
  * context_notes: Any other relevant context about user's needs

**Instructions:**
Respond with a JSON object containing:
- next_node: The handler to route to ("greeting", "information", or "booking")
- message: A brief acknowledgment or transition message for the user
- state_updates: Any updates to flow_state and bot_memory (including extracted preferences)

**Response Format:**
{{
  "next_node": "greeting" | "information" | "booking",
  "message": "Brief acknowledgment message",
  "state_updates": {{
    "flow_state": {{
      "current_intent": "greeting" | "information" | "booking"
    }},
    "bot_memory": {{
      "user_preferences": {{
        "preferred_sport": "sport_name" | null,
        "preferred_time": "morning" | "afternoon" | "evening" | null,
        "preferred_property": property_id | null,
        "preferred_court": court_id | null
      }},
      "inferred_information": {{
        "booking_frequency": "regular" | "occasional" | "first_time" | null,
        "interests": ["sport1", "sport2"] | [],
        "context_notes": "relevant context" | ""
      }}
    }}
  }}
}}

**Your Response:**"""


def get_routing_prompt(message: str, bot_memory: Dict[str, Any] = None) -> str:
    """
    Get the routing prompt for LLM-driven next_node decision.
    
    This function formats the routing prompt template with the user's message
    and bot_memory context. The LLM will analyze the message and return a 
    structured JSON response containing the next_node decision, a message for 
    the user, and state updates including extracted preferences.
    
    Args:
        message: The user message to analyze for routing
        bot_memory: Bot memory containing user preferences and context
        
    Returns:
        Formatted prompt string ready for LLM
        
    Requirements:
        - 2.1: LLM SHALL return next_node field
        - 2.2: Remove rule-based logic for intent determination
        - 2.3: LLM makes routing decisions
        - 2.4: Route to node specified by LLM's next_node decision
        - 4.1: Store user preferences in bot_memory
        - 4.2: Store inferred information in bot_memory
        
    Example:
        >>> bot_memory = {"user_preferences": {"preferred_sport": "tennis"}}
        >>> prompt = get_routing_prompt("I want to book a court", bot_memory)
        >>> # Returns formatted INTENT_ROUTING_PROMPT with message and bot_memory
    """
    bot_memory = bot_memory or {}
    bot_memory_str = f"""
User Preferences: {bot_memory.get('user_preferences', {})}
Inferred Information: {bot_memory.get('inferred_information', {})}
"""
    return INTENT_ROUTING_PROMPT.format(message=message, bot_memory=bot_memory_str)
