# Greeting Handler Node Usage Guide

## Overview

The `greeting_handler` node responds to greeting intents with contextual, friendly messages. It differentiates between new users (first interaction) and returning users (continuing conversation) by examining the bot_memory for conversation history and context.

## Requirements

- **6.1**: LangGraph high-level graph with Greeting handler node
- **21.1**: Route greeting messages to Greeting node

## Node Signature

```python
async def greeting_handler(
    state: ConversationState,
    chat_service: Optional[ChatService] = None,
    message_service: Optional[MessageService] = None
) -> ConversationState
```

## Input State

The node expects the following fields in `ConversationState`:

- `chat_id` (str): UUID of the chat session
- `user_message` (str): The user's greeting message
- `bot_memory` (dict): Contains conversation history and context
  - `conversation_history` (list): Previous messages in the conversation
  - `user_preferences` (dict): User's sport preferences and settings
  - `context` (dict): Previous search results and mentioned properties
  - `session_metadata` (dict): Session statistics like total_messages

## Output State

The node sets the following fields in the returned state:

- `response_content` (str): The greeting message text
- `response_type` (str): Always set to "text"
- `response_metadata` (dict): Always set to empty dict {}

All other state fields are preserved unchanged.

## Behavior

### New User Detection

A user is considered **new** if their `bot_memory` has:
- Empty or single-message conversation history
- No session metadata
- No user preferences
- No previous search context

**New user greeting:**
```
"Hello! I'm your sports booking assistant. I can help you find and book indoor sports facilities. What would you like to do today?"
```

### Returning User Detection

A user is considered **returning** if their `bot_memory` has any of:
- Multiple messages in conversation history (> 1)
- Session metadata with total_messages > 0
- User preferences (e.g., preferred_sport)
- Previous search results or mentioned properties

**Returning user greetings:**

1. **With sport preferences:**
   ```
   "Welcome back! Looking for more tennis facilities, or can I help you with something else?"
   ```

2. **With previous search results:**
   ```
   "Welcome back! Would you like to continue with your previous search, or start something new?"
   ```

3. **Generic returning user:**
   ```
   "Welcome back! How can I help you today? I can help you search for sports facilities or make a booking."
   ```

## Usage Examples

### Example 1: New User Greeting

```python
from apps.chatbot.app.agent.nodes.greeting import greeting_handler

state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "Hello",
    "flow_state": {},
    "bot_memory": {},
    "messages": [],
    "intent": "greeting",
    "response_content": "",
    "response_type": "",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None,
}

result = await greeting_handler(state)

print(result["response_content"])
# Output: "Hello! I'm your sports booking assistant. I can help you find and book indoor sports facilities. What would you like to do today?"
```

### Example 2: Returning User with Preferences

```python
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "Hi again",
    "flow_state": {},
    "bot_memory": {
        "conversation_history": [
            {"role": "user", "content": "I want to book a tennis court", "timestamp": "2024-01-10T10:00:00Z"},
            {"role": "assistant", "content": "Great! Let me show you available properties.", "timestamp": "2024-01-10T10:00:02Z"}
        ],
        "user_preferences": {
            "preferred_sport": "tennis",
            "preferred_time_of_day": "afternoon"
        }
    },
    "messages": [],
    "intent": "greeting",
    "response_content": "",
    "response_type": "",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None,
}

result = await greeting_handler(state)

print(result["response_content"])
# Output: "Welcome back! Looking for more tennis facilities, or can I help you with something else?"
```

### Example 3: Returning User with Search Context

```python
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "Hey",
    "flow_state": {},
    "bot_memory": {
        "conversation_history": [
            {"role": "user", "content": "Show me tennis courts", "timestamp": "2024-01-10T10:00:00Z"}
        ],
        "context": {
            "last_search_results": [
                "123e4567-e89b-12d3-a456-426614174000",
                "223e4567-e89b-12d3-a456-426614174001"
            ]
        }
    },
    "messages": [],
    "intent": "greeting",
    "response_content": "",
    "response_type": "",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None,
}

result = await greeting_handler(state)

print(result["response_content"])
# Output: "Welcome back! Would you like to continue with your previous search, or start something new?"
```

## Integration with LangGraph

The greeting handler is integrated into the main conversation graph as follows:

```python
from langgraph.graph import StateGraph, END
from apps.chatbot.app.agent.nodes.greeting import greeting_handler

# Add node to graph
graph.add_node("greeting", greeting_handler)

# Route from intent_detection to greeting
graph.add_conditional_edges(
    "intent_detection",
    route_by_intent,
    {
        "greeting": "greeting",
        # ... other routes
    }
)

# Greeting returns to END
graph.add_edge("greeting", END)
```

## Helper Functions

### `_is_returning_user(bot_memory: dict) -> bool`

Determines if the user is returning based on bot_memory contents.

**Returns True if:**
- Conversation history has > 1 message
- Session metadata shows total_messages > 0
- User preferences exist
- Previous search results or mentioned properties exist

**Returns False if:**
- bot_memory is empty or minimal

### `_generate_new_user_greeting() -> str`

Generates a welcoming greeting for first-time users that introduces the bot's capabilities.

### `_generate_returning_user_greeting(bot_memory: dict) -> str`

Generates a contextual greeting for returning users, optionally referencing:
- Preferred sports from user_preferences
- Previous search results from context
- Generic welcome back message

## Testing

Run the test suite:

```bash
cd Backend
python -m pytest apps/chatbot/app/agent/nodes/test_greeting.py -v
```

Test coverage includes:
- New user greeting generation
- Returning user greeting with conversation history
- Returning user greeting with sport preferences
- Returning user greeting with search context
- State field preservation
- Helper function behavior

## Logging

The node logs the following events:

- **INFO**: Processing greeting for chat (with chat_id)
- **DEBUG**: Generated new/returning user greeting (with chat_id)
- **INFO**: Greeting handler completed (with chat_id and is_returning flag)

Example log output:
```
INFO: Processing greeting for chat 123e4567-e89b-12d3-a456-426614174000
DEBUG: Generated returning user greeting for chat 123e4567-e89b-12d3-a456-426614174000
INFO: Greeting handler completed for chat 123e4567-e89b-12d3-a456-426614174000 - is_returning=True
```

## Error Handling

The greeting handler is designed to be robust:
- Handles missing or empty bot_memory gracefully
- Defaults to new user greeting if detection is uncertain
- Never raises exceptions - always returns a valid greeting
- Preserves all input state fields unchanged

## Design Decisions

1. **Simple Rule-Based Detection**: Uses bot_memory inspection rather than database queries for performance
2. **Contextual Greetings**: References user preferences and search history when available
3. **No LLM Required**: Generates greetings using templates, avoiding LLM costs for simple greetings
4. **Stateless Operation**: Doesn't modify flow_state or bot_memory, only reads them
5. **Text-Only Responses**: Always returns plain text, no buttons or lists needed for greetings
