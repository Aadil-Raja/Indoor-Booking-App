"""
Intent classification prompts for LLM-based routing decisions.

This module defines prompt templates used by the intent_detection node to make
explicit routing decisions. The LLM determines the next_node to route to based
on the user's message, eliminating rule-based transitions.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

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

- If the message contains booking-related words (book, reserve, schedule, appointment, reservation), route to **booking**
- If the message is about finding, searching, browsing facilities, or asking questions (pricing, hours, policies, availability), route to **information**
- If the message is a simple greeting or conversation starter, route to **greeting**
- When in doubt between information and booking, prefer **booking** if there's clear intent to make a reservation
- Handle typos, informal language, and abbreviations gracefully

**User Message:**
"{message}"

**Instructions:**
Respond with a JSON object containing:
- next_node: The handler to route to ("greeting", "information", or "booking")
- message: A brief acknowledgment or transition message for the user
- state_updates: Any updates to flow_state (set current_intent to match the routing decision)

**Response Format:**
{{
  "next_node": "greeting" | "information" | "booking",
  "message": "Brief acknowledgment message",
  "state_updates": {{
    "flow_state": {{
      "current_intent": "greeting" | "information" | "booking"
    }}
  }}
}}

**Your Response:**"""


def get_routing_prompt(message: str) -> str:
    """
    Get the routing prompt for LLM-driven next_node decision.
    
    This function formats the routing prompt template with the user's message.
    The LLM will analyze the message and return a structured JSON response
    containing the next_node decision, a message for the user, and state updates.
    
    Args:
        message: The user message to analyze for routing
        
    Returns:
        Formatted prompt string ready for LLM
        
    Requirements:
        - 2.1: LLM SHALL return next_node field
        - 2.2: Remove rule-based logic for intent determination
        - 2.3: LLM makes routing decisions
        - 2.4: Route to node specified by LLM's next_node decision
        
    Example:
        >>> prompt = get_routing_prompt("I want to book a court")
        >>> # Returns formatted INTENT_ROUTING_PROMPT with message
    """
    return INTENT_ROUTING_PROMPT.format(message=message)
