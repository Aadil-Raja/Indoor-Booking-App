# Indoor Search Handler Node Usage Guide

## Overview

The `indoor_search_handler` node processes facility search requests in the chatbot conversation flow. It extracts search parameters from user messages, calls property and court search tools, formats results as list messages, and stores results in bot_memory for later reference.

## Requirements Implemented

- **9.1-9.7**: Property and court search integration with result formatting
- **21.2**: Route facility/sports questions to Indoor_Search node
- **23.1-23.6**: Support text and list message types

## Node Function

```python
async def indoor_search_handler(
    state: ConversationState,
    tools: Optional[Dict[str, Any]] = None
) -> ConversationState
```

### Parameters

- `state`: ConversationState containing user message and context
- `tools`: Optional tool registry (defaults to TOOL_REGISTRY if not provided)

### Returns

ConversationState with:
- `response_content`: Text introducing the search results
- `response_type`: "list" for results, "text" for no results
- `response_metadata`: Contains `list_items` array for list messages
- `bot_memory`: Updated with search results and parameters

## Usage Examples

### Example 1: Tennis Court Search

```python
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user-uuid",
    "owner_id": "owner-uuid",
    "user_message": "I'm looking for tennis courts downtown",
    "bot_memory": {},
    "flow_state": {},
    ...
}

result = await indoor_search_handler(state)

# Result:
# result["response_type"] = "list"
# result["response_content"] = "Here are the available tennis in downtown facilities:"
# result["response_metadata"]["list_items"] = [
#     {
#         "id": "1",
#         "title": "Downtown Sports Center",
#         "description": "New York - 3 courts available"
#     },
#     ...
# ]
# result["bot_memory"]["context"]["last_search_results"] = ["1", "2", "3"]
# result["bot_memory"]["user_preferences"]["preferred_sport"] = "tennis"
```

### Example 2: Generic Search

```python
state = {
    "user_message": "show me available facilities",
    ...
}

result = await indoor_search_handler(state)

# Result:
# result["response_type"] = "list"
# result["response_content"] = "Here are the available facilities:"
# result["response_metadata"]["list_items"] = [...]
```

### Example 3: No Results

```python
state = {
    "user_message": "find squash courts in antarctica",
    ...
}

result = await indoor_search_handler(state)

# Result:
# result["response_type"] = "text"
# result["response_content"] = "I couldn't find any squash facilities in antarctica..."
# result["response_metadata"] = {}
```

## Search Parameter Extraction

The node automatically extracts search parameters from natural language:

### Sport Types Detected

- **Tennis**: "tennis", "tennis court"
- **Basketball**: "basketball", "basket ball", "hoops"
- **Badminton**: "badminton", "bad minton"
- **Squash**: "squash"
- **Volleyball**: "volleyball", "volley ball", "volley"

### Location Keywords

- **Downtown**: "downtown", "down town", "city center"
- **Westside**: "westside", "west side", "west"
- **Eastside**: "eastside", "east side", "east"
- **Northside**: "northside", "north side", "north"
- **Southside**: "southside", "south side", "south"

## Tool Integration

The node uses the following tools from the tool registry:

### search_properties

```python
properties = await tools["search_properties"](
    owner_id=owner_id,
    city=location,
    sport_type=sport_type,
    limit=10
)
```

### get_property_courts (optional enrichment)

```python
courts = await tools["get_property_courts"](
    property_id=property_id
)
```

## Bot Memory Updates

The node updates bot_memory with:

### Context

```json
{
  "context": {
    "last_search_results": ["property_id_1", "property_id_2", ...],
    "last_search_params": {
      "sport_type": "tennis",
      "location": "downtown"
    }
  }
}
```

### User Preferences

```json
{
  "user_preferences": {
    "preferred_sport": "tennis"
  }
}
```

## Response Format

### List Message (with results)

```json
{
  "response_content": "Here are the available tennis in downtown facilities:",
  "response_type": "list",
  "response_metadata": {
    "list_items": [
      {
        "id": "1",
        "title": "Downtown Sports Center",
        "description": "New York - 3 courts available"
      },
      {
        "id": "2",
        "title": "Tennis Club",
        "description": "Brooklyn - 4 courts"
      }
    ]
  }
}
```

### Text Message (no results)

```json
{
  "response_content": "I couldn't find any tennis facilities in downtown matching your search. Would you like to try a different search or browse all available facilities?",
  "response_type": "text",
  "response_metadata": {}
}
```

## Error Handling

The node handles errors gracefully:

1. **Tool not found**: Returns empty results
2. **Search fails**: Logs error and returns no results message
3. **Enrichment fails**: Includes property without enrichment
4. **Invalid property data**: Skips invalid entries

## Integration with LangGraph

The node is designed to be used in the main conversation graph:

```python
# In main_graph.py
graph.add_node("indoor_search", indoor_search_handler)

graph.add_conditional_edges(
    "intent_detection",
    route_by_intent,
    {
        "search": "indoor_search",
        ...
    }
)

graph.add_edge("indoor_search", END)
```

## Testing

Comprehensive unit tests are provided in `test_indoor_search.py`:

- Parameter extraction tests
- Result formatting tests
- Response generation tests
- Bot memory update tests
- Integration tests with mocked tools
- Error handling tests

Run tests:

```bash
python -m pytest apps/chatbot/app/agent/nodes/test_indoor_search.py -v
```

## Best Practices

1. **Always provide tools**: Pass the tool registry to ensure proper functionality
2. **Preserve bot_memory**: The node preserves existing bot_memory while adding new data
3. **Limit results**: Results are automatically limited to 5 items for better UX
4. **Handle typos**: The extraction logic handles common typos and variations
5. **Contextual responses**: Messages adapt based on search parameters

## Future Enhancements

Potential improvements:

1. Add more sport types and location patterns
2. Support date/time filtering in search
3. Add distance-based search with user location
4. Support price range filtering
5. Add sorting options (by price, distance, rating)
6. Implement fuzzy matching for location names
7. Add multi-language support for search terms
