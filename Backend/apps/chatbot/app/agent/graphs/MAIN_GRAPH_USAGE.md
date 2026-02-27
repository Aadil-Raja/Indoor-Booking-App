# Main Conversation Graph Usage Guide

## Overview

The main conversation graph (`main_graph.py`) is the top-level orchestrator for the WhatsApp-style chatbot. It wires together all conversation nodes with conditional routing based on user intent.

## Graph Structure

### Nodes

The main graph includes the following nodes:

1. **receive_message**: Entry point that validates incoming messages
2. **load_chat**: Loads chat history and context from the database
3. **append_user_message**: Adds user message to bot_memory
4. **intent_detection**: Classifies user intent (greeting, search, booking, faq)
5. **greeting**: Handles greeting intents
6. **indoor_search**: Handles facility search requests
7. **booking**: Booking subgraph (multi-step booking flow)
8. **faq**: Handles general questions and unknown intents

### Flow

```
receive_message
    ↓
load_chat
    ↓
append_user_message
    ↓
intent_detection
    ↓
    ├─→ greeting → END
    ├─→ indoor_search → END
    ├─→ booking → END
    └─→ faq → END
```

### Routing Logic

The `route_by_intent` function examines the `intent` field in the ConversationState and routes to the appropriate handler:

- **greeting** → greeting handler
- **search** → indoor_search handler
- **booking** → booking subgraph
- **faq** → faq handler
- **unknown** → faq handler (default)

## Usage

### Creating the Graph

```python
from app.agent.graphs.main_graph import create_main_graph
from app.services.llm.openai_provider import OpenAIProvider
from app.agent.tools import TOOL_REGISTRY

# Initialize dependencies
llm_provider = OpenAIProvider(api_key="your-api-key")
tools = TOOL_REGISTRY

# Create the graph
main_graph = create_main_graph(
    llm_provider=llm_provider,
    tools=tools,
    chat_service=chat_service,  # Optional
    message_service=message_service  # Optional
)
```

### Executing the Graph

```python
# Prepare the conversation state
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "flow_state": {},
    "bot_memory": {},
    "messages": [],
    "intent": None,
    "response_content": "",
    "response_type": "text",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None
}

# Execute the graph
result = await main_graph.ainvoke(state)

# Access the response
response_content = result["response_content"]
response_type = result["response_type"]
response_metadata = result["response_metadata"]
updated_flow_state = result["flow_state"]
updated_bot_memory = result["bot_memory"]
```

## Integration with AgentService

The main graph is typically invoked by the `AgentService`, which handles:
- Preparing the conversation state from the Chat model
- Executing the graph
- Storing the bot response in the database
- Updating the chat's flow_state and bot_memory

Example from AgentService:

```python
async def process_message(self, chat: Chat, user_message: str) -> Dict[str, Any]:
    # Prepare state
    state = {
        "chat_id": str(chat.id),
        "user_id": str(chat.user_id),
        "owner_id": str(chat.owner_id),
        "user_message": user_message,
        "flow_state": chat.flow_state,
        "bot_memory": chat.bot_memory,
        "messages": []
    }
    
    # Execute main graph
    result = await self.main_graph.ainvoke(state)
    
    # Update chat state
    await self.chat_service.update_chat_state(
        chat,
        flow_state=result["flow_state"],
        bot_memory=result["bot_memory"]
    )
    
    # Store bot response
    bot_message = await self.message_service.create_message(
        chat_id=chat.id,
        sender_type="bot",
        content=result["response_content"],
        message_type=result["response_type"],
        metadata=result["response_metadata"],
        token_usage=result.get("token_usage")
    )
    
    return {
        "content": result["response_content"],
        "message_type": result["response_type"],
        "metadata": result["response_metadata"],
        "message_id": bot_message.id
    }
```

## Requirements Implemented

The main graph implements the following requirements:

- **6.1**: LangGraph high-level graph with all required nodes
- **6.2**: Intent_Detection node routes to appropriate handler
- **6.3**: Booking_Subgraph integrated as a node
- **6.4**: Read current flow_state and bot_memory when executing nodes
- **6.5**: Update flow_state and bot_memory when nodes complete
- **6.6**: Call tools to interact with existing services
- **6.7**: Invoke LLM_Provider for natural language generation
- **6.8**: Maintain state persistence between node transitions

## Node Responsibilities

### receive_message
- Validates required fields in state
- Logs incoming message for observability
- Passes state unchanged to next node

### load_chat
- Loads message history from database
- Initializes flow_state and bot_memory if empty
- Formats messages for LLM context

### append_user_message
- Adds user message to bot_memory.conversation_history
- Adds user message to ephemeral messages list
- Maintains conversation context

### intent_detection
- Classifies user intent using rule-based patterns
- Falls back to LLM for complex intents
- Updates flow_state.intent

### greeting
- Generates contextual greetings
- Differentiates between new and returning users
- Sets response_content, response_type, response_metadata

### indoor_search
- Extracts search parameters from user message
- Calls property and court search tools
- Formats results as list message
- Stores results in bot_memory

### booking
- Executes the booking subgraph
- Handles multi-step booking flow
- Supports back navigation and cancellation

### faq
- Handles general questions
- Uses LLM to generate contextual responses
- Provides fallback responses when LLM unavailable

## Error Handling

The graph handles errors gracefully:
- Missing fields in state raise ValueError in receive_message
- LLM failures fall back to rule-based responses
- Tool failures are logged and handled by individual nodes
- All errors are logged with full context

## Logging

The graph provides comprehensive logging:
- Node transitions are logged at INFO level
- Routing decisions are logged at DEBUG level
- Errors are logged at ERROR level with full context
- All logs include chat_id for traceability

## Testing

To test the graph structure without running it:

```python
from app.agent.graphs.main_graph import route_by_intent

# Test routing logic
test_cases = [
    ({"intent": "greeting"}, "greeting"),
    ({"intent": "search"}, "search"),
    ({"intent": "booking"}, "booking"),
    ({"intent": "faq"}, "faq"),
    ({"intent": "unknown"}, "unknown"),
]

for state, expected in test_cases:
    result = route_by_intent(state)
    assert result == expected, f"Expected {expected}, got {result}"
```

## Next Steps

After the main graph is created, the next task is to:
1. Create the graph runtime wrapper (Task 10.3)
2. Implement AgentService to orchestrate graph execution (Task 11.1)
3. Wire everything together in the API endpoints (Task 14.1)
