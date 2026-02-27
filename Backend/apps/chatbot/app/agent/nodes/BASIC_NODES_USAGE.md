# Basic Flow Nodes Usage Guide

This document explains how to use the basic flow nodes in the LangGraph conversation agent.

## Overview

The basic flow nodes are the foundational building blocks of the LangGraph conversation flow. They handle:

1. **receive_message**: Entry point that receives and validates user messages
2. **load_chat**: Loads chat history and context from the database
3. **append_user_message**: Adds user messages to conversation history in bot_memory

These nodes work with the `ConversationState` TypedDict and integrate with `ChatService` and `MessageService` for database operations.

## Node Descriptions

### receive_message

**Purpose**: Entry point node that receives and validates the user's message.

**Requirements**: 6.1, 12.1

**Input State Fields**:
- `chat_id` (required): UUID of the chat session
- `user_id` (required): UUID of the user
- `owner_id` (required): UUID of the property owner
- `user_message` (required): The user's message content

**Output**: Returns the same state after validation and logging.

**Example**:
```python
from apps.chatbot.app.agent.nodes import receive_message

state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "flow_state": {},
    "bot_memory": {},
    "messages": [],
}

result = await receive_message(state)
# State is validated and logged, returned unchanged
```

**Error Handling**:
- Raises `ValueError` if required fields are missing
- Logs warning for empty messages but allows them to pass through

---

### load_chat

**Purpose**: Load chat history and context from the database.

**Requirements**: 6.1, 6.4, 4.8, 20.1-20.8

**Input State Fields**:
- `chat_id` (required): UUID of the chat session
- `flow_state` (optional): Existing flow state (preserved if present)
- `bot_memory` (optional): Existing bot memory (preserved if present)

**Output State Fields**:
- `flow_state`: Initialized to `{}` if not present
- `bot_memory`: Initialized to `{}` if not present
- `messages`: List of formatted message history for LLM context

**Dependencies**:
- `message_service`: MessageService instance for loading chat history

**Example**:
```python
from apps.chatbot.app.agent.nodes import load_chat
from apps.chatbot.app.services.message_service import MessageService

# Create message service
message_service = MessageService(session, message_repo)

state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "Show me options",
    "flow_state": {"intent": "booking", "step": "select_property"},
    "bot_memory": {"conversation_history": [...]},
}

result = await load_chat(state, message_service=message_service)

# result["messages"] now contains:
# [
#   {"role": "user", "content": "Hello"},
#   {"role": "assistant", "content": "Hi! How can I help?"},
#   {"role": "user", "content": "I want to book a court"},
#   ...
# ]
```

**Message Format**:
Messages are formatted for LLM context with role mapping:
- `sender_type="user"` → `role="user"`
- `sender_type="bot"` → `role="assistant"`
- `sender_type="system"` → `role="system"`

**Error Handling**:
- Continues with empty messages list if MessageService fails
- Logs errors but doesn't fail the flow

---

### append_user_message

**Purpose**: Add the user's message to the conversation history in bot_memory.

**Requirements**: 6.1, 6.5, 20.1-20.8

**Input State Fields**:
- `chat_id` (required): UUID of the chat session
- `user_message` (required): The user's message content
- `bot_memory` (optional): Existing bot memory
- `messages` (optional): Existing messages list

**Output State Fields**:
- `bot_memory.conversation_history`: Updated with new user message entry
- `messages`: Updated with new user message for immediate LLM context

**Example**:
```python
from apps.chatbot.app.agent.nodes import append_user_message

state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "bot_memory": {
        "conversation_history": [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-10T10:00:00"},
            {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-10T10:00:01"}
        ]
    },
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"}
    ],
}

result = await append_user_message(state)

# result["bot_memory"]["conversation_history"] now contains:
# [
#   {"role": "user", "content": "Hello", "timestamp": "2024-01-10T10:00:00"},
#   {"role": "assistant", "content": "Hi!", "timestamp": "2024-01-10T10:00:01"},
#   {"role": "user", "content": "I want to book a tennis court", "timestamp": "2024-01-10T10:00:05"}
# ]

# result["messages"] now contains:
# [
#   {"role": "user", "content": "Hello"},
#   {"role": "assistant", "content": "Hi!"},
#   {"role": "user", "content": "I want to book a tennis court"}
# ]
```

**Message Entry Format**:
Each conversation history entry includes:
- `role`: "user" or "assistant"
- `content`: Message text
- `timestamp`: ISO format timestamp (UTC)

**Behavior**:
- Initializes `conversation_history` if not present in bot_memory
- Preserves other bot_memory fields (user_preferences, context, etc.)
- Appends to both persistent bot_memory and ephemeral messages list

---

## Integration with LangGraph

These nodes are designed to be used in a LangGraph StateGraph:

```python
from langgraph.graph import StateGraph, END
from apps.chatbot.app.agent.state.conversation_state import ConversationState
from apps.chatbot.app.agent.nodes import (
    receive_message,
    load_chat,
    append_user_message
)

# Create graph
graph = StateGraph(ConversationState)

# Add nodes
graph.add_node("receive_message", receive_message)
graph.add_node("load_chat", load_chat)
graph.add_node("append_user_message", append_user_message)

# Define flow
graph.set_entry_point("receive_message")
graph.add_edge("receive_message", "load_chat")
graph.add_edge("load_chat", "append_user_message")
graph.add_edge("append_user_message", "intent_detection")  # Next node

# Compile
compiled_graph = graph.compile()
```

## Dependency Injection

The nodes accept optional service dependencies for testing and flexibility:

```python
# In production (with real services)
result = await load_chat(
    state,
    message_service=message_service
)

# In tests (with mocks)
mock_service = AsyncMock()
mock_service.get_chat_history = AsyncMock(return_value=[...])

result = await load_chat(
    state,
    message_service=mock_service
)
```

## State Management

### Flow State vs Bot Memory

- **flow_state**: Structured data for booking progress (property_id, service_id, date, time, step)
- **bot_memory**: Unstructured data for AI context (conversation_history, user_preferences, context)

### Messages List

The `messages` list is ephemeral (not persisted to database) and used for:
- Immediate LLM context during graph execution
- Building prompts for intent detection and response generation

The persistent conversation history is stored in `bot_memory.conversation_history`.

## Logging

All nodes include structured logging:

- **receive_message**: Logs incoming messages with chat_id, user_id, owner_id
- **load_chat**: Logs chat history loading and current state
- **append_user_message**: Logs message appending and history length

Example log output:
```
INFO: Received message - chat_id=123e4567-..., user_id=223e4567-..., owner_id=323e4567-..., message_preview=I want to book a tennis court...
INFO: Loading chat history for chat 123e4567-...
INFO: Loaded 15 messages for chat 123e4567-...
DEBUG: Chat 123e4567-... state loaded - step=select_property, intent=booking, messages_count=15
INFO: Appended user message to bot_memory for chat 123e4567-... - conversation_history_length=16, messages_length=16
```

## Testing

See `test_basic_nodes.py` for comprehensive test examples covering:
- Field validation
- State initialization
- Message history loading
- Conversation history management
- Error handling

Run tests:
```bash
cd Backend
python -m pytest apps/chatbot/app/agent/nodes/test_basic_nodes.py -v
```

## Requirements Traceability

| Node | Requirements |
|------|-------------|
| receive_message | 6.1, 12.1 |
| load_chat | 6.1, 6.4, 4.8, 20.1-20.8 |
| append_user_message | 6.1, 6.5, 20.1-20.8 |

## Next Steps

After implementing these basic nodes, the next nodes to implement are:

1. **intent_detection**: Classify user intent (greeting, search, booking, FAQ)
2. **greeting_handler**: Handle greeting intents
3. **indoor_search_handler**: Handle facility search requests
4. **faq_handler**: Handle general questions
5. **Booking subgraph nodes**: Multi-step booking flow

These will be implemented in subsequent tasks (8.2-8.5 and 9.1-9.6).
