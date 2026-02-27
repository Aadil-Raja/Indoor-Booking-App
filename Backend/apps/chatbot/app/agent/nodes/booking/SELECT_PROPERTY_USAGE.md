# Select Property Node Usage Guide

## Overview

The `select_property` node is the first step in the booking subgraph. It handles property selection by presenting available properties from search results as button options, parsing user selections, and storing the selected property in flow_state.

## Requirements

Implements the following requirements:
- **6.3**: Booking_Subgraph with Select_Property node
- **20.2**: Store selected property_id when user chooses a property
- **22.1-22.6**: Booking confirmation flow
- **23.2**: Support button message type for quick reply options

## Node Behavior

### First Call - Present Options

When the node is first entered (step is not "select_property"):

1. **Check for search results** in `bot_memory.context.last_search_results`
2. **If no search results exist**:
   - Prompt user to search for facilities first
   - Set `flow_state.step = "awaiting_search"`
   - Return text response

3. **If search results exist**:
   - Retrieve property details using `get_property_details` tool
   - Format properties as button options (limit to 5)
   - Store property details in `bot_memory.context.property_details`
   - Set `flow_state.step = "select_property"`
   - Return button response

### Second Call - Process Selection

When the node is called with `flow_state.step = "select_property"`:

1. **Parse user selection** from message:
   - Try exact property ID match
   - Try exact property name match (case-insensitive)
   - Try partial property name match
   - Try word overlap matching

2. **If selection is valid**:
   - Store `property_id` in flow_state
   - Store `property_name` in flow_state
   - Set `flow_state.step = "property_selected"`
   - Return confirmation text response

3. **If selection is invalid**:
   - Return error message with available options
   - Keep `flow_state.step = "select_property"` to allow retry

### Skip Condition

If `flow_state.property_id` already exists, the node returns the state unchanged, allowing the flow to continue to the next step.

## State Management

### Input State

```python
{
    "chat_id": "uuid",
    "user_id": "uuid",
    "owner_id": "uuid",
    "user_message": "user's message",
    "flow_state": {
        "intent": "booking",
        "step": "select_property" | None
    },
    "bot_memory": {
        "context": {
            "last_search_results": ["1", "2", "3"],
            "property_details": [...]  # Optional, populated by node
        }
    }
}
```

### Output State

```python
{
    "flow_state": {
        "intent": "booking",
        "step": "property_selected",
        "property_id": "1",
        "property_name": "Downtown Sports Center"
    },
    "bot_memory": {
        "context": {
            "last_search_results": ["1", "2", "3"],
            "property_details": [...]  # Populated with full property data
        }
    },
    "response_content": "Great! You've selected Downtown Sports Center. Now let's choose a court.",
    "response_type": "text",
    "response_metadata": {}
}
```

## Response Types

### Button Response (Presenting Options)

```python
{
    "response_content": "Which facility would you like to book?",
    "response_type": "button",
    "response_metadata": {
        "buttons": [
            {"id": "1", "text": "Downtown Sports Center"},
            {"id": "2", "text": "Westside Arena"},
            {"id": "3", "text": "Eastside Tennis Club"}
        ]
    }
}
```

### Text Response (Confirmation)

```python
{
    "response_content": "Great! You've selected Downtown Sports Center. Now let's choose a court.",
    "response_type": "text",
    "response_metadata": {}
}
```

### Text Response (No Search Results)

```python
{
    "response_content": "To make a booking, I first need to know which facility you're interested in. Would you like me to search for available facilities?",
    "response_type": "text",
    "response_metadata": {}
}
```

### Text Response (Invalid Selection)

```python
{
    "response_content": "I couldn't find that facility. Please select from the available options: Downtown Sports Center, Westside Arena, Eastside Tennis Club",
    "response_type": "text",
    "response_metadata": {}
}
```

## Selection Parsing

The node supports multiple selection formats:

1. **Property ID**: "1", "property 2", "I want 3"
2. **Exact name**: "Downtown Sports Center"
3. **Case-insensitive**: "downtown sports center"
4. **Partial name**: "Downtown Sports", "Sports Center"
5. **Word overlap**: "Tennis Club" matches "Eastside Tennis Club"

## Tools Used

- **get_property_details**: Retrieves full property information by ID
  - Called for each property in `last_search_results`
  - Returns property data including name, city, address, courts

## Error Handling

### No Search Results

If `bot_memory.context.last_search_results` is empty:
- Prompt user to search first
- Set step to "awaiting_search"
- User should be routed back to indoor_search node

### Failed Property Retrieval

If `get_property_details` fails for all properties:
- Return error message
- Suggest searching again
- Keep current step

### Invalid Selection

If user's message doesn't match any property:
- Return helpful error with available options
- Keep step as "select_property" to allow retry
- User can try again with different input

## Integration with Booking Flow

### Previous Step

The select_property node expects:
- User has performed a search (indoor_search node)
- `bot_memory.context.last_search_results` contains property IDs

### Next Step

After successful property selection:
- `flow_state.property_id` is set
- `flow_state.step = "property_selected"`
- Flow continues to `select_service` node

## Example Usage

```python
from app.agent.nodes.booking import select_property
from app.agent.tools import TOOL_REGISTRY

# First call - present options
state = {
    "chat_id": "123",
    "user_id": "456",
    "owner_id": "789",
    "user_message": "I want to book a court",
    "flow_state": {"intent": "booking"},
    "bot_memory": {
        "context": {
            "last_search_results": ["1", "2", "3"]
        }
    }
}

result = await select_property(state, tools=TOOL_REGISTRY)
# result["response_type"] == "button"
# result["flow_state"]["step"] == "select_property"

# Second call - process selection
state["user_message"] = "Downtown Sports Center"
state["flow_state"]["step"] = "select_property"

result = await select_property(state, tools=TOOL_REGISTRY)
# result["flow_state"]["property_id"] == "1"
# result["flow_state"]["step"] == "property_selected"
```

## Testing

The node includes comprehensive unit tests covering:
- Presenting options with/without search results
- Processing selection by ID, name, partial name
- Handling invalid selections
- Skipping when property already selected
- Button formatting
- Selection parsing
- Bot memory updates

Run tests with:
```bash
pytest Backend/apps/chatbot/app/agent/nodes/booking/test_select_property.py -v
```

## Logging

The node logs the following events:
- **INFO**: Processing property selection (with step and message preview)
- **INFO**: Presented property options (with count)
- **INFO**: Property selected (with ID and name)
- **INFO**: Retrieved properties (with count)
- **DEBUG**: Property already selected
- **DEBUG**: Selection matching details
- **WARNING**: Invalid property selection
- **WARNING**: Failed to retrieve property details
- **ERROR**: Error retrieving property

## Future Enhancements

Potential improvements:
1. Support for filtering properties by additional criteria
2. Pagination for more than 5 properties
3. Property preview with images
4. Recent property suggestions based on user history
5. Location-based sorting
