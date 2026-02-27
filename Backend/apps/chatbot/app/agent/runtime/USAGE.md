# Graph Runtime Usage Guide

## Overview

The Graph Runtime provides a clean, production-ready interface for executing the LangGraph conversation flow. It handles initialization, compilation, execution, error handling, and structured logging.

## Key Features

- **Dependency Injection**: Initialize with LLM provider, services, and tools
- **Structured Logging**: Automatic logging of node transitions and execution metrics
- **Error Handling**: Graceful degradation with fallback responses
- **State Management**: Validates and prepares state, preserves state on errors
- **Execution Metrics**: Tracks execution time and token usage

## Basic Usage

### 1. Create a Graph Runtime

```python
from app.agent.runtime import create_graph_runtime
from app.services.llm.openai_provider import OpenAIProvider

# Initialize LLM provider
llm_provider = OpenAIProvider(api_key="your-api-key")

# Create runtime
runtime = create_graph_runtime(llm_provider=llm_provider)
```

### 2. Execute the Graph

```python
# Prepare conversation state
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174000",
    "owner_id": "789e0123-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "flow_state": {},
    "bot_memory": {},
    "messages": []
}

# Execute graph
result = await runtime.execute(state)

# Access response
print(result["response_content"])
print(result["response_type"])
print(result["response_metadata"])
```

## Advanced Usage

### With Service Dependencies

```python
from app.agent.runtime import create_graph_runtime
from app.services.llm.openai_provider import OpenAIProvider
from app.services.chat_service import ChatService
from app.services.message_service import MessageService

# Initialize dependencies
llm_provider = OpenAIProvider(api_key="your-api-key")
chat_service = ChatService(session, chat_repo, message_repo)
message_service = MessageService(session, message_repo)

# Create runtime with services
runtime = create_graph_runtime(
    llm_provider=llm_provider,
    chat_service=chat_service,
    message_service=message_service
)
```

### With Tool Dependencies

```python
# Create runtime with custom tool dependencies
runtime = create_graph_runtime(
    llm_provider=llm_provider,
    tool_dependencies={
        "db_session": session,
        "config": app_config
    }
)
```

## Integration with AgentService

The Graph Runtime is designed to be used by AgentService:

```python
from app.agent.runtime import create_graph_runtime
from app.services.agent_service import AgentService

class AgentService:
    def __init__(
        self,
        session: AsyncSession,
        chat_service: ChatService,
        message_service: MessageService,
        llm_provider: LLMProvider
    ):
        self.session = session
        self.chat_service = chat_service
        self.message_service = message_service
        
        # Initialize graph runtime
        self.runtime = create_graph_runtime(
            llm_provider=llm_provider,
            chat_service=chat_service,
            message_service=message_service
        )
    
    async def process_message(
        self,
        chat: Chat,
        user_message: str
    ) -> Dict[str, Any]:
        # Store user message
        await self.message_service.create_message(
            chat_id=chat.id,
            sender_type="user",
            content=user_message
        )
        
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
        
        # Execute graph through runtime
        result = await self.runtime.execute(state)
        
        # Update chat state
        await self.chat_service.update_chat_state(
            chat,
            flow_state=result.get("flow_state"),
            bot_memory=result.get("bot_memory")
        )
        
        # Store bot response
        bot_message = await self.message_service.create_message(
            chat_id=chat.id,
            sender_type="bot",
            content=result["response_content"],
            message_type=result.get("response_type", "text"),
            metadata=result.get("response_metadata", {}),
            token_usage=result.get("token_usage")
        )
        
        return {
            "content": result["response_content"],
            "message_type": result.get("response_type", "text"),
            "metadata": result.get("response_metadata", {}),
            "message_id": bot_message.id
        }
```

## State Structure

### Input State (Required Fields)

```python
{
    "chat_id": str,        # UUID of the chat session
    "user_id": str,        # UUID of the user
    "owner_id": str,       # UUID of the property owner
    "user_message": str,   # The user's message
}
```

### Input State (Optional Fields)

```python
{
    "flow_state": dict,           # Current booking/conversation state
    "bot_memory": dict,           # Conversation context and history
    "messages": list,             # Message history for LLM context
    "intent": str,                # Current detected intent
    "response_content": str,      # Pre-filled response (rare)
    "response_type": str,         # Pre-filled response type (rare)
    "response_metadata": dict,    # Pre-filled response metadata (rare)
    "token_usage": int,           # Pre-filled token usage (rare)
    "search_results": list,       # Pre-filled search results (rare)
    "availability_data": dict,    # Pre-filled availability data (rare)
    "pricing_data": dict,         # Pre-filled pricing data (rare)
}
```

### Output State

```python
{
    # Input fields (preserved)
    "chat_id": str,
    "user_id": str,
    "owner_id": str,
    "user_message": str,
    
    # Updated conversation state
    "flow_state": dict,           # Updated booking/conversation state
    "bot_memory": dict,           # Updated conversation context
    "messages": list,             # Updated message history
    "intent": str,                # Detected intent
    
    # Response fields
    "response_content": str,      # Bot's response text
    "response_type": str,         # Message type (text, button, list, media)
    "response_metadata": dict,    # Additional response data
    
    # Metrics
    "token_usage": int,           # LLM tokens consumed (if applicable)
    
    # Tool results (may be populated)
    "search_results": list,       # Results from search tools
    "availability_data": dict,    # Available time slots
    "pricing_data": dict,         # Pricing information
}
```

## Error Handling

The runtime handles errors gracefully:

### LLM Provider Errors

When the LLM provider fails, the runtime returns a fallback response while preserving the conversation state:

```python
{
    "response_content": "I'm having trouble processing your request right now. Please try again in a moment.",
    "response_type": "text",
    "flow_state": {...},  # Preserved
    "bot_memory": {...},  # Preserved
    ...
}
```

### Unexpected Errors

For unexpected errors, the runtime logs the error and returns a user-friendly message:

```python
{
    "response_content": "I encountered an error processing your message. Your conversation state has been preserved. Please try again.",
    "response_type": "text",
    "flow_state": {...},  # Preserved
    "bot_memory": {...},  # Preserved
    ...
}
```

## Logging

The runtime provides structured logging at multiple levels:

### Execution Start

```json
{
    "level": "INFO",
    "message": "Starting graph execution",
    "chat_id": "123",
    "user_id": "456",
    "user_message": "I want to book a tennis court",
    "flow_state": {},
    "intent": null
}
```

### Execution Complete

```json
{
    "level": "INFO",
    "message": "Graph execution completed successfully",
    "chat_id": "123",
    "user_id": "456",
    "execution_time_ms": 1234.56,
    "response_type": "text",
    "token_usage": 150,
    "final_intent": "booking",
    "final_step": "select_property"
}
```

### Execution Error

```json
{
    "level": "ERROR",
    "message": "Graph execution failed with unexpected error: ...",
    "chat_id": "123",
    "user_id": "456",
    "execution_time_ms": 567.89,
    "error_type": "ValueError",
    "flow_state": {...}
}
```

## Best Practices

1. **Always use the factory function**: Use `create_graph_runtime()` instead of instantiating `GraphRuntime` directly
2. **Validate input state**: Ensure required fields are present before calling `execute()`
3. **Handle errors gracefully**: The runtime returns fallback responses, but you should still handle exceptions
4. **Monitor logs**: Use structured logging to monitor graph execution and debug issues
5. **Preserve state**: The runtime preserves `flow_state` and `bot_memory` on errors, ensuring conversation continuity

## Requirements Implemented

- **6.8**: Maintain state persistence between node transitions
- **12.3**: Log all node transitions in LangGraph_Agent with current state
- **14.3**: When database operation fails, preserve flow_state and bot_memory
- **14.4**: When tool invocation fails, log the error and inform the user
- **14.5**: When recovering from failure, resume from last known good state
- **16.11**: Place runtime utilities in app/agent/runtime directory
