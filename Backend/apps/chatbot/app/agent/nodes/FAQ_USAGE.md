# FAQ Handler Node Usage Guide

## Overview

The FAQ handler node (`faq.py`) processes general questions and unknown intents in the chatbot conversation flow. It uses the LLM provider to generate contextual, helpful responses for questions about pricing, policies, general information, and handles unknown intents gracefully.

## Requirements

**Implements:**
- Requirement 6.1: LangGraph high-level graph with FAQ handler node
- Requirement 21.4: Route general questions to FAQ node

## Node Function

### `faq_handler(state, llm_provider=None)`

Handles general questions and unknown intents with LLM-generated responses.

**Parameters:**
- `state` (ConversationState): Current conversation state containing user message and context
- `llm_provider` (Optional[LLMProvider]): LLM provider for generating responses (optional)

**Returns:**
- `ConversationState`: Updated state with response_content, response_type, and response_metadata set

**State Fields Modified:**
- `response_content`: The generated response text
- `response_type`: Set to "text"
- `response_metadata`: Set to empty dict
- `token_usage`: Number of tokens used (if LLM provider available)

## Usage Examples

### Basic Usage with LLM Provider

```python
from ..state.conversation_state import ConversationState
from ...services.llm.openai_provider import OpenAIProvider
from .faq import faq_handler

# Initialize LLM provider
llm_provider = OpenAIProvider(api_key="your-api-key")

# Create state with user question
state: ConversationState = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user-uuid",
    "owner_id": "owner-uuid",
    "user_message": "How much does it cost to book a tennis court?",
    "flow_state": {},
    "bot_memory": {},
    "messages": [],
    "intent": "faq",
    "response_content": "",
    "response_type": "",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None,
}

# Process FAQ
result = await faq_handler(state, llm_provider=llm_provider)

print(result["response_content"])
# Output: "Pricing varies by facility and time slot. You can see specific 
#          prices when you search for facilities and select a time. Would 
#          you like me to help you search for available facilities?"

print(result["token_usage"])
# Output: 145 (example)
```

### Usage Without LLM Provider (Fallback)

```python
# Process FAQ without LLM provider
state: ConversationState = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "What's your cancellation policy?",
    # ... other fields
}

result = await faq_handler(state, llm_provider=None)

print(result["response_content"])
# Output: "For information about cancellation and refund policies, please 
#          contact the specific facility you're interested in. Can I help 
#          you search for facilities or make a booking?"
```

### Handling Unknown Intents

```python
# User message that doesn't fit any specific category
state: ConversationState = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "Tell me a joke",
    # ... other fields
}

result = await faq_handler(state, llm_provider=llm_provider)

print(result["response_content"])
# Output: "I'm here to help you find and book indoor sports facilities. 
#          I can search for tennis, basketball, badminton, squash, and 
#          volleyball courts. What would you like to do?"
```

## Question Types Handled

### 1. Pricing Questions

**Examples:**
- "How much does it cost?"
- "What are your prices?"
- "How much to book a tennis court?"

**Response Strategy:**
- Explains that pricing varies by facility and time slot
- Directs user to search for facilities to see specific prices
- Offers to help with facility search

### 2. Policy Questions

**Examples:**
- "What's your cancellation policy?"
- "Can I get a refund?"
- "What are your booking policies?"

**Response Strategy:**
- Provides general information about policies
- Suggests contacting specific facilities for detailed policies
- Offers to help with search or booking

### 3. Help/How-to Questions

**Examples:**
- "How do I use this?"
- "What can you do?"
- "Help me"

**Response Strategy:**
- Explains the system's capabilities (search and booking)
- Lists available sports types
- Invites user to start searching or booking

### 4. Unknown Intents

**Examples:**
- "What's the weather?"
- "Tell me a joke"
- Any off-topic message

**Response Strategy:**
- Politely redirects to system capabilities
- Explains what the bot can help with
- Invites user to search for facilities or make bookings

## LLM Integration

### Prompt Template

The FAQ handler uses a structured prompt template that:
- Identifies the bot as a sports booking assistant
- Provides context about the system's capabilities
- Includes the user's message
- Guides the LLM to generate helpful, concise responses
- Instructs the LLM not to make up specific prices or policies

### LLM Parameters

```python
response = await llm_provider.generate(
    prompt=FAQ_RESPONSE_PROMPT.format(user_message=user_message),
    max_tokens=150,      # Limit response length
    temperature=0.7      # Moderate creativity for natural responses
)
```

### Token Tracking

The handler tracks token usage for cost monitoring:
```python
prompt_tokens = llm_provider.count_tokens(prompt)
response_tokens = llm_provider.count_tokens(response_text)
total_tokens = prompt_tokens + response_tokens
```

## Error Handling

### LLM Provider Errors

When the LLM provider fails, the handler automatically falls back to rule-based responses:

```python
try:
    response = await llm_provider.generate(...)
except LLMProviderError as e:
    # Falls back to _generate_fallback_response()
    response = _generate_fallback_response(user_message)
```

### Token Counting Errors

If token counting fails, the handler continues without token tracking:

```python
try:
    total_tokens = prompt_tokens + response_tokens
except Exception as e:
    logger.warning(f"Failed to count tokens: {e}")
    total_tokens = None
```

## Fallback Response Logic

When LLM is unavailable, the handler uses keyword-based fallback responses:

| Keywords | Response Type |
|----------|---------------|
| price, cost, how much, payment | Pricing information |
| cancel, refund, policy | Policy information |
| help, how, what can | System capabilities |
| (other) | Generic help message |

## Integration with LangGraph

### In Main Graph

```python
from langgraph.graph import StateGraph, END
from .nodes.faq import faq_handler

graph = StateGraph(ConversationState)

# Add FAQ node
graph.add_node("faq", faq_handler)

# Route from intent detection
graph.add_conditional_edges(
    "intent_detection",
    route_by_intent,
    {
        "greeting": "greeting",
        "search": "indoor_search",
        "booking": "booking",
        "faq": "faq",
        "unknown": "faq"  # Default to FAQ for unknown intents
    }
)

# FAQ returns to END
graph.add_edge("faq", END)
```

### Routing Logic

The FAQ handler receives messages when:
1. Intent detection classifies message as "faq"
2. Intent detection returns "unknown" (defaults to FAQ)
3. User asks general questions about pricing, policies, or help

## Testing

### Unit Tests

The module includes comprehensive unit tests:

```bash
# Run FAQ handler tests
pytest Backend/apps/chatbot/app/agent/nodes/test_faq.py -v

# Run with coverage
pytest Backend/apps/chatbot/app/agent/nodes/test_faq.py --cov=.faq --cov-report=term-missing
```

### Test Coverage

- ✅ LLM response generation
- ✅ Fallback responses when LLM unavailable
- ✅ Error handling for LLM failures
- ✅ Pricing question handling
- ✅ Policy question handling
- ✅ Unknown intent handling
- ✅ Token usage tracking
- ✅ Token counting error handling
- ✅ State field preservation

### Mock LLM Provider

```python
from unittest.mock import AsyncMock
from ...services.llm.base import LLMProvider

# Create mock LLM provider
mock_llm = AsyncMock(spec=LLMProvider)
mock_llm.generate.return_value = "Test response"
mock_llm.count_tokens.side_effect = lambda text: len(text.split())

# Use in tests
result = await faq_handler(state, llm_provider=mock_llm)
```

## Best Practices

### 1. Always Provide LLM Provider

For best user experience, always provide an LLM provider:
```python
result = await faq_handler(state, llm_provider=llm_provider)
```

### 2. Monitor Token Usage

Track token usage for cost monitoring:
```python
if result["token_usage"]:
    logger.info(f"FAQ response used {result['token_usage']} tokens")
```

### 3. Handle Errors Gracefully

The handler automatically falls back to generic responses on errors, but you should monitor error logs:
```python
logger.error(f"LLM provider error: {e}")
```

### 4. Keep Responses Concise

The handler is configured to generate concise responses (max 150 tokens). This ensures:
- Fast response times
- Lower costs
- Better user experience

### 5. Don't Make Up Information

The prompt explicitly instructs the LLM not to make up specific prices or policies. Always verify that responses are accurate and helpful.

## Logging

The FAQ handler logs important events:

```python
# Info level
logger.info(f"Processing FAQ for chat {chat_id}")
logger.info(f"FAQ handler completed - response_length={len(response)}")

# Debug level
logger.debug(f"Generating LLM response for FAQ")
logger.debug(f"Generated fallback response")

# Warning level
logger.warning(f"No LLM provider available, using fallback")
logger.warning(f"Failed to count tokens: {e}")

# Error level
logger.error(f"LLM provider error: {e}", exc_info=True)
```

## Performance Considerations

### Response Time

- LLM generation: ~1-3 seconds
- Fallback response: <10ms
- Token counting: <50ms

### Cost Optimization

- Max tokens limited to 150 (reduces cost)
- Fallback responses used when appropriate (no LLM cost)
- Token usage tracked for monitoring

### Caching Opportunities

Consider caching common FAQ responses:
```python
# Example: Cache common questions
FAQ_CACHE = {
    "how much does it cost": "Pricing varies by facility...",
    "what's your policy": "For policies, please contact...",
}
```

## Troubleshooting

### Issue: LLM responses are too long

**Solution:** Reduce max_tokens parameter:
```python
response = await llm_provider.generate(
    prompt=prompt,
    max_tokens=100,  # Reduced from 150
    temperature=0.7
)
```

### Issue: Responses are too generic

**Solution:** Increase temperature for more creative responses:
```python
response = await llm_provider.generate(
    prompt=prompt,
    max_tokens=150,
    temperature=0.9  # Increased from 0.7
)
```

### Issue: LLM making up prices

**Solution:** The prompt already instructs against this. If it persists, strengthen the prompt:
```python
FAQ_RESPONSE_PROMPT = """...
IMPORTANT: Do not make up specific prices, dates, or policies. 
Only provide general information and direct users to search for details.
..."""
```

## Related Modules

- `intent_detection.py`: Routes messages to FAQ handler
- `greeting.py`: Handles greeting intents
- `indoor_search.py`: Handles facility search
- `conversation_state.py`: Defines state structure
- `llm/base.py`: LLM provider interface
- `llm/openai_provider.py`: OpenAI implementation

## Future Enhancements

1. **Response Caching**: Cache common FAQ responses to reduce LLM calls
2. **Context Awareness**: Use bot_memory to provide more contextual responses
3. **Multi-turn FAQ**: Support follow-up questions in FAQ conversations
4. **Structured FAQ Database**: Integrate with a FAQ knowledge base
5. **Sentiment Analysis**: Detect user frustration and adjust responses
6. **Language Support**: Support multiple languages for international users
