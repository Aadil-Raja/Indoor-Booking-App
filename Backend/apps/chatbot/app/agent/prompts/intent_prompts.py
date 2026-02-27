"""
Intent classification prompts for LLM-based intent detection.

This module defines prompt templates used by the intent_detection node when
rule-based classification is insufficient. The prompts guide the LLM to classify
user messages into one of four intent categories: greeting, search, booking, or faq.

Requirements: 21.5
"""

INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a sports facility booking chatbot. Your task is to classify the user's message into exactly ONE of the following intents:

**Intent Categories:**

1. **greeting** - User is greeting the bot or starting a conversation
   - Examples: "hi", "hello", "good morning", "hey there", "what's up"
   
2. **search** - User wants to search for, find, or browse sports facilities or courts
   - Examples: "show me tennis courts", "find basketball facilities", "what courts are available", "looking for badminton courts near downtown"
   
3. **booking** - User wants to book, reserve, or schedule a facility
   - Examples: "I want to book a court", "reserve a tennis court for tomorrow", "can I schedule a booking", "make a reservation"
   
4. **faq** - User has questions, needs help, or wants information about pricing, policies, or general topics
   - Examples: "how much does it cost", "what are your hours", "can I cancel a booking", "tell me about your facilities", "help"

**Classification Rules:**

- If the message contains booking-related words (book, reserve, schedule, appointment), classify as **booking**
- If the message is about finding or searching for facilities, classify as **search**
- If the message is a simple greeting or conversation starter, classify as **greeting**
- If the message asks questions about pricing, policies, or general information, classify as **faq**
- When in doubt between search and booking, prefer **booking** if there's any indication of wanting to make a reservation
- When in doubt between search and faq, prefer **search** if the user is looking for facilities
- Handle typos, informal language, and abbreviations gracefully

**User Message:**
"{message}"

**Instructions:**
Respond with ONLY the intent name (greeting, search, booking, or faq). Do not include any explanation, punctuation, or additional text.

**Your Classification:**"""


# Alternative prompt with few-shot examples for better accuracy
INTENT_CLASSIFICATION_PROMPT_FEW_SHOT = """You are an intent classifier for a sports facility booking chatbot. Classify the user's message into exactly ONE intent: greeting, search, booking, or faq.

**Examples:**

User: "hi there"
Intent: greeting

User: "show me available tennis courts"
Intent: search

User: "I want to book a basketball court for tomorrow"
Intent: booking

User: "how much does it cost to rent a court?"
Intent: faq

User: "good morning!"
Intent: greeting

User: "find badminton facilities near downtown"
Intent: search

User: "can I reserve a court for 3pm?"
Intent: booking

User: "what are your cancellation policies?"
Intent: faq

User: "looking for volleyball courts"
Intent: search

User: "schedule an appointment for tennis"
Intent: booking

User: "hey"
Intent: greeting

User: "tell me about your facilities"
Intent: faq

**Now classify this message:**

User: "{message}"
Intent:"""


# Structured prompt for JSON output (for future use with structured outputs)
INTENT_CLASSIFICATION_PROMPT_STRUCTURED = """Classify the user's message into one of these intents for a sports facility booking chatbot:

- greeting: User is greeting or starting conversation
- search: User wants to find/search for facilities or courts
- booking: User wants to book/reserve a facility
- faq: User has questions about pricing, policies, or general info

User message: "{message}"

Respond in JSON format:
{{
  "intent": "greeting|search|booking|faq",
  "confidence": "high|medium|low",
  "reasoning": "brief explanation"
}}"""


# Prompt for handling edge cases and ambiguous messages
INTENT_CLASSIFICATION_PROMPT_EDGE_CASES = """You are an intent classifier for a sports facility booking chatbot. Classify the user's message into exactly ONE intent: greeting, search, booking, or faq.

**Intent Definitions:**
- greeting: Greetings, conversation starters, casual hellos
- search: Looking for, finding, browsing facilities or courts
- booking: Making reservations, scheduling, booking facilities
- faq: Questions about pricing, policies, hours, general information

**Special Cases:**
- "I need a court" → booking (implies wanting to reserve)
- "Do you have tennis courts?" → search (asking about availability)
- "What courts do you have?" → search (browsing options)
- "Can I book?" → booking (asking about booking capability)
- "How do I book?" → faq (asking about process)
- "Show me prices" → faq (asking for information)
- "Available courts?" → search (looking for options)

**User Message:**
"{message}"

**Classification (respond with only the intent name):**"""


def get_intent_prompt(message: str, prompt_type: str = "default") -> str:
    """
    Get the appropriate intent classification prompt for a user message.
    
    This function selects and formats the appropriate prompt template based on
    the specified prompt type. Different prompt types can be used for different
    scenarios or to experiment with prompt engineering.
    
    Args:
        message: The user message to classify
        prompt_type: Type of prompt to use. Options:
            - "default": Standard prompt with clear instructions
            - "few_shot": Prompt with multiple examples for better accuracy
            - "structured": Prompt requesting JSON output (for future use)
            - "edge_cases": Prompt with special handling for ambiguous cases
            
    Returns:
        Formatted prompt string ready for LLM
        
    Example:
        >>> prompt = get_intent_prompt("I want to book a court", "default")
        >>> # Returns formatted INTENT_CLASSIFICATION_PROMPT
    """
    prompts = {
        "default": INTENT_CLASSIFICATION_PROMPT,
        "few_shot": INTENT_CLASSIFICATION_PROMPT_FEW_SHOT,
        "structured": INTENT_CLASSIFICATION_PROMPT_STRUCTURED,
        "edge_cases": INTENT_CLASSIFICATION_PROMPT_EDGE_CASES,
    }
    
    prompt_template = prompts.get(prompt_type, INTENT_CLASSIFICATION_PROMPT)
    return prompt_template.format(message=message)
