# Information Handler Node Usage Guide

## Overview

The `information_handler` node processes all information-related queries in the chatbot conversation flow using LangChain agents with automatic tool calling. It handles queries about properties, courts, availability, pricing, and media.

**Note:** This node replaces the deprecated `indoor_search_handler`. See migration guide below.

## Requirements Implemented

- **1.1-1.5**: Property search functionality
- **2.1-2.5**: Property details retrieval
- **3.1-3.5**: Court details retrieval
- **4.1-4.5**: Court availability checking
- **5.1-5.5**: Court pricing information
- **6.1-6.5**: Media retrieval for properties and courts
- **7.1-7.5**: Complex multi-tool queries
- **8.1-8.5**: Context-aware conversations with bot_memory
- **9.1-9.6**: LangChain agent with ChatOpenAI and automatic tool calling
- **10.1-10.5**: LangGraph integration and routing
- **11.1-11.5**: State management with bot_memory updates

## Node Function

```python
async def information_handler(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState
```

### Parameters

- `state`: ConversationState containing user message and context
- `llm_provider`: LLMProvider instance for creating ChatOpenAI

### Returns

ConversationState with:
- `response_content`: Text response from the LangChain agent
- `response_type`: "text" (agent handles formatting)
- `bot_memory`: Updated with conversation context

## Usage Examples

### Example 1: Property Search Query

```python
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user-uuid",
    "owner_profile_id": "1",
    "user_message": "Show me tennis courts in New York",
    "bot_memory": {},
    "flow_state": {},
    ...
}

result = await information_handler(state, llm_provider=provider)

# Result:
# {
#     "response_content": "I found 3 tennis courts in New York: ...",
#     "response_type": "text",
#     "bot_memory": {
#         "context": {
#             "last_query": "tennis courts in New York",
#             "last_results": [...]
#         }
#     }
# }
```

### Example 2: Availability Check

```python
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user-uuid",
    "owner_profile_id": "1",
    "user_message": "What's available at Sports Center tomorrow?",
    "bot_memory": {},
    ...
}

result = await information_handler(state, llm_provider=provider)

# The agent automatically:
# 1. Searches for "Sports Center" property
# 2. Gets courts for that property
# 3. Checks availability for tomorrow
# 4. Formats a natural language response
```

### Example 3: Pricing Query

```python
state = {
    "user_message": "How much does it cost to book Court 1 on Friday?",
    "owner_profile_id": "1",
    ...
}

result = await information_handler(state, llm_provider=provider)

# Agent automatically retrieves pricing and responds naturally
```

## How It Works

The information handler uses LangChain's `create_openai_functions_agent` to:

1. **Analyze the query**: Understands user intent from natural language
2. **Select tools**: Automatically chooses appropriate tools from INFORMATION_TOOLS
3. **Execute tools**: Calls tools in sequence as needed
4. **Format response**: Generates natural language response with results

### Available Tools

The agent has access to these tools:
- `search_properties`: Search properties by location and sport type
- `get_property_details`: Get detailed property information
- `get_property_courts`: Get courts for a property
- `get_court_details`: Get detailed court information
- `get_court_availability`: Check court availability for a date
- `get_court_pricing`: Get pricing for a court and time slot
- `get_property_media`: Get media (images/videos) for a property
- `get_court_media`: Get media for a court

## Integration with Main Graph

```python
# In main_graph.py
from app.agent.nodes.information import information_handler

async def information_handler_node(state):
    return await information_handler(state, llm_provider)

graph.add_node("information", information_handler_node)

# Routing from intent detection
graph.add_conditional_edges(
    "intent_detection",
    route_by_next_node,
    {
        "greeting": "greeting",
        "information": "information",  # Routes here for info queries
        "booking": "booking"
    }
)

graph.add_edge("information", END)
```

## Bot Memory Updates

The information handler automatically updates bot_memory with:
- Query context for conversation continuity
- Search results for reference in booking flow
- User preferences inferred from queries

```python
# Example bot_memory after query
{
    "context": {
        "last_query": "tennis courts downtown",
        "last_results": ["property_1", "property_2"],
        "last_search_params": {"sport_type": "tennis", "location": "downtown"}
    },
    "user_preferences": {
        "preferred_sport": "tennis"
    }
}
```

## Error Handling

The agent handles errors gracefully:
- Tool failures: Returns helpful error message
- No results: Suggests alternatives
- Invalid queries: Asks for clarification

## Testing

Tests are provided in `tests/integration/test_information_node.py`:

```bash
python -m pytest Backend/apps/chatbot/tests/integration/test_information_node.py -v
```

## Migration from indoor_search_handler

If you're migrating from the old `indoor_search_handler`:

### Code Changes

```python
# OLD
from app.agent.nodes.indoor_search import indoor_search_handler
result = await indoor_search_handler(state, tools=TOOL_REGISTRY)

# NEW
from app.agent.nodes.information import information_handler
result = await information_handler(state, llm_provider=provider)
```

### Graph Changes

```python
# OLD
graph.add_node("indoor_search", indoor_search_handler)
graph.add_conditional_edges(
    "intent_detection",
    route_by_intent,
    {"search": "indoor_search", ...}
)

# NEW
graph.add_node("information", information_handler_node)
graph.add_conditional_edges(
    "intent_detection",
    route_by_next_node,
    {"information": "information", ...}
)
```

### Key Differences

1. **Automatic tool calling**: No need to manually extract parameters or call tools
2. **Natural language**: Agent generates conversational responses
3. **Multi-step queries**: Agent can chain multiple tools automatically
4. **Context awareness**: Uses bot_memory for personalized responses
5. **LLM-driven routing**: Uses next_node field instead of intent field

## Best Practices

1. **Provide context**: Include bot_memory and flow_state for better responses
2. **Trust the agent**: Let it select and execute tools automatically
3. **Update bot_memory**: Agent updates are preserved for conversation continuity
4. **Handle errors**: Check response_content for error messages
5. **Monitor token usage**: Agent may use more tokens for complex queries

## Related Documentation

- `information.py`: Node implementation
- `information_tools.py`: Available tools
- `information_prompts.py`: Agent prompts
- `tests/integration/test_information_node.py`: Integration tests
