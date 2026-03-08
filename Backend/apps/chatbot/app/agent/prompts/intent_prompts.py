"""
Intent routing prompts - simple routing only.

LLM decides which handler to route to:
- greeting
- information  
- booking
"""

from typing import Dict, Any

INTENT_ROUTING_PROMPT = """You are a routing assistant for a sports facility booking chatbot.

Analyze the user's message and decide which handler should process it.

**Available Handlers:**

1. **greeting** - Greetings and conversation starters
   Examples: "hi", "hello", "good morning", "hey"

2. **information** - Questions about facilities, courts, availability, pricing
   Examples: "show me tennis courts", "what's available", "how much does it cost"

3. **booking** - Booking or reserving facilities
   Examples: "I want to book a court", "reserve a tennis court", "make a reservation"

**Recent Conversation:**
{conversation_context}

**Current Context:**
- Last action: {last_node}

**User Message:**
"{message}"

**Instructions:**
Use the conversation history to understand context for ambiguous messages like "book it", "yes", "that one".
Respond with ONLY a JSON object:
{{
  "next_node": "greeting" | "information" | "booking"
}}

**Your Response:**"""


def get_routing_prompt(
    message: str,
    recent_messages: list = None,
    last_node: str = None
) -> str:
    """
    Get the routing prompt for LLM decision.
    
    Includes conversation context for better routing of ambiguous messages.
    """
    # Format recent messages
    if recent_messages and len(recent_messages) > 0:
        formatted_messages = []
        for msg in recent_messages[-5:]:  # Last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append(f"- {role.title()}: {content[:100]}")
        conversation_context = "\n".join(formatted_messages)
    else:
        conversation_context = "No previous messages (new conversation)"
    
    # Format context
    last_node_str = last_node if last_node else "None (new conversation)"
    
    return INTENT_ROUTING_PROMPT.format(
        message=message,
        conversation_context=conversation_context,
        last_node=last_node_str
    )
