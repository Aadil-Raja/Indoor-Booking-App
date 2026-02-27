# Select Service Node Usage Guide

## Overview

The `select_service` node is the second step in the booking subgraph. It handles court (service) selection by retrieving courts for the selected property, presenting them as list options with sport type information, parsing user selections, and storing the selected service in flow_state.

## Requirements

Implements the following requirements:
- **6.3**: Booking_Subgraph with Select_Service node
- **20.3**: Store selected service_id when user chooses a court
- **22.1-22.6**: Booking confirmation flow
- **23.3**: Support list message type for multiple choice selections

## Node Behavior

### First Call - Present Options

When the node is first entered (step is not "select_service"):

1. **Check for property selection** in `flow_state.property_id`
2. **If no property selected**:
   - Return error message prompting to select facility first
   - Return text response

3. **If property is selected**:
   - Retrieve courts using `get_property_courts` tool
   - Format courts as list items with sport type information
   - Store court details in `bot_memory.context.court_details`
   - Set `flow_state.step = "select_service"`
   - Return list response

4. **If no courts available**:
   - Return error message suggesting different facility
   - Return text response

### Second Call - Process Selection

When the node is called with `flow_state.step = "select_service"`:

1. **Parse user selection** from message:
   - Try exact court ID match
   - Try exact court name match (case-insensitive)
   - Try partial court name match
   - Try sport type match (if only one court of that type)
   - Try word overlap matching (requires at least 2 matching words)

2. **If selection is valid**:
   - Store `service_id` in flow_state
   - Store `service_name` in flow_state
   - Store `sport_type` in flow_state
   - Set `flow_state.step = "service_selected"`
   - Return confirmation text response

3. **If selection is invalid**:
   - Return error message with available options
   - Keep `flow_state.step = "select_service"` to allow retry

### Skip Condition

If `flow_state.service_id` already exists, the node returns the state unchanged, allowing the flow to continue to the next step.

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
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "step": "select_service" | "property_selected"
    },
    "bot_memory": {
        "context": {
            "court_details": [...]  # Optional, populated by node
        }
    }
}
```

### Output State

```python
{
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "step": "service_selected",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis"
    },
    "bot_memory": {
        "context": {
            "court_details": [...]  # Populated with full court data
        }
    },
    "response_content": "Perfect! You've selected Tennis Court A (tennis). Now let's choose a date for your booking.",
    "response_type": "text",
    "response_metadata": {}
}
```

## Response Types

### List Response (Presenting Options)

```python
{
    "response_content": "Great! Here are the available courts at Downtown Sports Center:",
    "response_type": "list",
    "response_metadata": {
        "list_items": [
            {
                "id": "10",
                "title": "Tennis Court A",
                "description": "Sport: tennis"
            },
            {
                "id": "11",
                "title": "Tennis Court B",
                "description": "Sport: tennis"
            },
            {
                "id": "12",
                "title": "Basketball Court",
                "description": "Sport: basketball"
            }
        ]
    }
}
```

### Text Response (Confirmation)

```python
{
    "response_content": "Perfect! You've selected Tennis Court A (tennis). Now let's choose a date for your booking.",
    "response_type": "text",
    "response_metadata": {}
}
```

### Text Response (No Property Selected)

```python
{
    "response_content": "Please select a facility first before choosing a court.",
    "response_type": "text",
    "response_metadata": {}
}
```

### Text Response (No Courts Available)

```python
{
    "response_content": "I couldn't find any courts available at Downtown Sports Center. Would you like to select a different facility?",
    "response_type": "text",
    "response_metadata": {}
}
```

### Text Response (Invalid Selection)

```python
{
    "response_content": "I couldn't find that court. Please select from the available options: Tennis Court A (tennis), Tennis Court B (tennis), Basketball Court (basketball)",
    "response_type": "text",
    "response_metadata": {}
}
```

## Selection Parsing

The node supports multiple selection formats:

1. **Court ID**: "10", "court 11", "I want 12"
2. **Exact name**: "Tennis Court A"
3. **Case-insensitive**: "tennis court a"
4. **Partial name**: "Tennis Court", "Court A"
5. **Sport type** (if only one court): "basketball"
6. **Word overlap**: "Tennis Court" matches "Tennis Court A" (requires at least 2 matching words)

## Tools Used

- **get_property_courts**: Retrieves all courts for a property
  - Called with property_id from flow_state
  - Returns list of court data including id, name, sport_type

## Error Handling

### No Property Selected

If `flow_state.property_id` is not set:
- Return error message
- Prompt user to select facility first
- User should be routed back to select_property node

### No Courts Available

If `get_property_courts` returns empty list:
- Return error message
- Suggest selecting different facility
- User can go back to property selection

### Failed Court Retrieval

If `get_property_courts` fails with exception:
- Log error with details
- Return empty list
- Show "no courts available" message

### Invalid Selection

If user's message doesn't match any court:
- Return helpful error with available options (including sport types)
- Keep step as "select_service" to allow retry
- User can try again with different input

## Integration with Booking Flow

### Previous Step

The select_service node expects:
- User has selected a property (select_property node)
- `flow_state.property_id` is set
- `flow_state.property_name` is set

### Next Step

After successful service selection:
- `flow_state.service_id` is set
- `flow_state.service_name` is set
- `flow_state.sport_type` is set
- `flow_state.step = "service_selected"`
- Flow continues to `select_date` node

## Example Usage

```python
from app.agent.nodes.booking import select_service
from app.agent.tools import TOOL_REGISTRY

# First call - present options
state = {
    "chat_id": "123",
    "user_id": "456",
    "owner_id": "789",
    "user_message": "Downtown Sports Center",
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "step": "property_selected"
    },
    "bot_memory": {}
}

result = await select_service(state, tools=TOOL_REGISTRY)
# result["response_type"] == "list"
# result["flow_state"]["step"] == "select_service"

# Second call - process selection
state["user_message"] = "Tennis Court A"
state["flow_state"]["step"] = "select_service"

result = await select_service(state, tools=TOOL_REGISTRY)
# result["flow_state"]["service_id"] == "10"
# result["flow_state"]["service_name"] == "Tennis Court A"
# result["flow_state"]["sport_type"] == "tennis"
# result["flow_state"]["step"] == "service_selected"
```

## Testing

The node includes comprehensive unit tests covering:
- Presenting options with/without property selected
- Processing selection by ID, name, partial name, sport type
- Handling invalid selections
- Handling no courts available
- Skipping when service already selected
- List formatting with sport type information
- Selection parsing
- Bot memory updates

Run tests with:
```bash
pytest Backend/apps/chatbot/app/agent/nodes/booking/test_select_service.py -v
```

## Logging

The node logs the following events:
- **INFO**: Processing service selection (with step and message preview)
- **INFO**: Presented court options (with count)
- **INFO**: Service selected (with ID, name, and sport type)
- **INFO**: Retrieved courts (with count)
- **DEBUG**: Service already selected
- **DEBUG**: Selection matching details
- **WARNING**: Invalid court selection
- **WARNING**: No courts found for property
- **ERROR**: Error retrieving courts

## Future Enhancements

Potential improvements:
1. Display court availability status in list
2. Show pricing information per court
3. Filter courts by sport type before presenting
4. Court images in list items
5. Court capacity and amenities information
6. Real-time availability indicators

