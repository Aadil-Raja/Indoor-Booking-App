# Intent Detection Node Usage Guide

## Overview

The `intent_detection` node classifies user messages into one of four intents:
- **greeting**: Welcome messages, hellos, general greetings
- **search**: Facility/court search requests
- **booking**: Booking-related requests
- **faq**: General questions, help requests

The node uses rule-based pattern matching for common intents and falls back to LLM for complex or ambiguous messages.

## Requirements Implemented

- **6.2**: Intent_Detection node that classifies user intent and routes to appropriate handler
- **21.1**: Route greeting messages to Greeting node
- **21.2**: Route facility/sports questions to Indoor_Search node
- **21.3**: Route booking intent to Booking_Subgraph
- **21.4**: Route general questions to FAQ node
- **21.5**: Use LLM_Provider for intent classification when rule-based matching fails
- **21.6**: Handle typos and informal language

## Function Signature

```python
async def intent_detection(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState
```

### Parameters

- `state` (ConversationState): The conversation state containing:
  - `user_message`: The user's message to classify
  - `flow_state`: Current flow state (will be updated with detected intent)
  - `chat_id`: Chat ID for logging
  
- `llm_provider` (Optional[LLMProvider]): LLM provider for fallback classification when rule-based matching is uncertain

### Returns

- `ConversationState`: Updated state with:
  - `intent`: Detected intent string ("greeting", "search", "booking", or "faq")
  - `flow_state["intent"]`: Same intent stored in flow_state for persistence

## Usage Examples

### Basic Usage in LangGraph

```python
from app.agent.nodes import intent_detection
from app.agent.state.conversation_state import ConversationState
from app.services.llm.openai_provider import OpenAIProvider

# Initialize LLM provider
llm_provider = OpenAIProvider(api_key="your-api-key")

# Create conversation state
state: ConversationState = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "flow_state": {},
    "bot_memory": {},
    "messages": [],
    # ... other fields
}

# Execute intent detection
result = await intent_detection(state, llm_provider)

print(result["intent"])  # Output: "booking"
print(result["flow_state"]["intent"])  # Output: "booking"
```

### Integration with LangGraph Flow

```python
from langgraph.graph import StateGraph
from app.agent.nodes import intent_detection, receive_message, load_chat

# Create graph
graph = StateGraph(ConversationState)

# Add nodes
graph.add_node("receive_message", receive_message)
graph.add_node("load_chat", load_chat)
graph.add_node("intent_detection", lambda state: intent_detection(state, llm_provider))

# Define edges
graph.set_entry_point("receive_message")
graph.add_edge("receive_message", "load_chat")
graph.add_edge("load_chat", "intent_detection")

# Add conditional routing based on intent
graph.add_conditional_edges(
    "intent_detection",
    lambda state: state["intent"],
    {
        "greeting": "greeting_handler",
        "search": "search_handler",
        "booking": "booking_handler",
        "faq": "faq_handler",
    }
)
```

### Without LLM Provider (Rule-Based Only)

```python
# If no LLM provider is available, the node will use rule-based classification only
# and default to "faq" for ambiguous messages
state["user_message"] = "Hello!"
result = await intent_detection(state, llm_provider=None)
print(result["intent"])  # Output: "greeting" (detected by rules)

state["user_message"] = "I need something for tomorrow"
result = await intent_detection(state, llm_provider=None)
print(result["intent"])  # Output: "faq" (ambiguous, no LLM, defaults to faq)
```

## Intent Classification Rules

### Greeting Intent

Detected when message contains:
- Simple greetings: "hi", "hello", "hey"
- Formal greetings: "good morning", "good afternoon", "good evening"
- Informal greetings: "howdy", "hiya", "sup", "yo"
- Variations: "heyyy", "hello!"

**Examples:**
- "Hello!" → greeting
- "Good morning" → greeting
- "Hey there" → greeting

### Search Intent

Detected when message contains:
- Search keywords: "search", "find", "looking for", "show me", "available"
- Questions about facilities: "what facilities", "which courts", "where can i find"
- Sport-specific searches: "tennis court", "basketball facility"
- Location-based: "indoor sports near me"

**Examples:**
- "Show me tennis courts" → search
- "Find basketball facilities" → search
- "What courts are available?" → search

### Booking Intent

Detected when message contains:
- Booking keywords: "book", "reserve", "schedule", "make a booking"
- Natural language: "i want to book", "i'd like to reserve", "can i book"
- Related terms: "appointment", "reservation"

**Examples:**
- "I want to book a court" → booking
- "Reserve a tennis court" → booking
- "Can I make a booking?" → booking

**Note:** Booking intent is checked before search intent to prioritize booking when both keywords are present.

### FAQ Intent

Detected when message contains:
- Help requests: "help", "explain", "tell me about"
- Information requests: "question", "info", "information", "details"
- Pricing questions: "price", "cost", "how much", "payment", "refund"
- Process questions: "what is", "how do i"

**Examples:**
- "How much does it cost?" → faq
- "Tell me about pricing" → faq
- "I have a question" → faq

### Unknown Intent (LLM Fallback)

When no rule-based patterns match, the node uses the LLM provider to classify the intent:

1. Constructs a classification prompt with the user message
2. Calls LLM with low temperature (0.0) for consistent results
3. Validates the LLM response is a valid intent
4. Defaults to "faq" if LLM fails or returns invalid intent

**Examples requiring LLM:**
- "I need something for tomorrow" → LLM determines intent
- "Can you help me with that thing?" → LLM determines intent
- "What about next week?" → LLM determines intent

## Pattern Matching Priority

The node checks patterns in this order:

1. **Greeting** - Checked first as greetings are usually short and distinct
2. **Booking** - Checked before search to prioritize booking intent
3. **Search** - Checked after booking to avoid false positives
4. **FAQ** - Checked last as it's the most general category
5. **LLM Fallback** - Used when no patterns match

This ordering ensures that more specific intents (booking) take priority over general ones (search).

## Error Handling

The node handles errors gracefully:

- **LLM Provider Error**: If LLM call fails, defaults to "faq" intent
- **Invalid LLM Response**: If LLM returns invalid intent, defaults to "faq"
- **No LLM Provider**: If no provider available and no rule match, defaults to "faq"
- **Empty Message**: Defaults to "faq"

All errors are logged with full context for debugging.

## State Updates

The node updates the conversation state as follows:

1. Sets `state["intent"]` with the detected intent
2. Updates `state["flow_state"]["intent"]` for persistence
3. Preserves all other fields in `flow_state`
4. Logs the detection for observability

## Testing

Comprehensive unit tests are available in `test_intent_detection.py`:

```bash
# Run all intent detection tests
pytest apps/chatbot/app/agent/nodes/test_intent_detection.py -v

# Run specific test class
pytest apps/chatbot/app/agent/nodes/test_intent_detection.py::TestRuleBasedClassification -v

# Run specific test
pytest apps/chatbot/app/agent/nodes/test_intent_detection.py::TestIntentDetectionNode::test_greeting_detection -v
```

Test coverage includes:
- Rule-based classification for all intents
- LLM fallback scenarios
- Error handling
- Edge cases (empty messages, mixed intents, special characters)
- State preservation

## Performance Considerations

- **Rule-based classification** is fast (regex matching) and handles 90%+ of common cases
- **LLM fallback** adds latency (typically 100-500ms) but handles complex cases
- **Caching**: Consider caching common message patterns to reduce LLM calls
- **Logging**: All classifications are logged for monitoring and optimization

## Future Enhancements

Potential improvements:
- Add more sophisticated pattern matching (e.g., NER for locations, dates)
- Implement intent confidence scores
- Support multi-intent detection (e.g., "search and book")
- Add user preference learning (e.g., frequent booking users)
- Implement A/B testing for pattern optimization
