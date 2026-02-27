# Booking Subgraph Usage Guide

## Overview

The booking subgraph is a LangGraph StateGraph that manages the multi-step booking process for the WhatsApp-style chatbot. It wires together all booking nodes with conditional routing logic to support sequential booking steps, back navigation, and cancellation.

## Architecture

### Nodes

The subgraph contains 6 nodes that handle different steps of the booking process:

1. **select_property**: Present properties and handle property selection
2. **select_service**: Present courts/services and handle service selection
3. **select_date**: Present calendar and handle date selection
4. **select_time**: Present available time slots and handle time selection
5. **confirm**: Present booking summary and handle confirmation
6. **create_booking**: Create the booking in the system

### Flow

```
select_property → select_service → select_date → select_time → confirm → create_booking → END
     ↓                ↓                ↓              ↓            ↓
   cancel           back            back           back        modify
     ↓                ↓                ↓              ↓            ↓
    END          select_property  select_service  select_date  select_property
```

### Routing Functions

Each node has a routing function that determines the next step based on:
- User message content (back, cancel, confirmation keywords)
- Flow state (whether required data is present)

#### route_property_selection
- **continue**: Property ID is present in flow_state
- **cancel**: User says "cancel" or no property selected

#### route_service_selection
- **continue**: Service ID is present in flow_state
- **back**: User says "back" or "previous"
- **cancel**: User says "cancel" or no service selected

#### route_date_selection
- **continue**: Date is present in flow_state
- **back**: User says "back"
- **cancel**: User says "cancel" or no date selected

#### route_time_selection
- **continue**: Time is present in flow_state
- **back**: User says "back"
- **cancel**: User says "cancel" or no time selected

#### route_confirmation
- **confirmed**: User says "yes", "confirm", "book", "proceed"
- **modify**: User says "change", "modify", "edit"
- **cancel**: Any other response

## Usage

### Creating the Subgraph

```python
from app.agent.graphs import create_booking_subgraph
from app.agent.tools import TOOL_REGISTRY

# Create the booking subgraph
booking_graph = create_booking_subgraph(TOOL_REGISTRY)
```

### Executing the Subgraph

```python
# Prepare the state
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "223e4567-e89b-12d3-a456-426614174000",
    "owner_id": "323e4567-e89b-12d3-a456-426614174000",
    "user_message": "I want to book a tennis court",
    "flow_state": {
        "intent": "booking",
        "step": "initial"
    },
    "bot_memory": {
        "context": {
            "last_search_results": ["1", "2", "3"]
        }
    },
    "messages": [],
    "intent": "booking",
    "response_content": "",
    "response_type": "text",
    "response_metadata": {},
    "token_usage": None,
    "search_results": None,
    "availability_data": None,
    "pricing_data": None
}

# Execute the graph
result = await booking_graph.ainvoke(state)

# Access the result
print(result["response_content"])
print(result["response_type"])
print(result["flow_state"])
```

### Integration with Main Graph

The booking subgraph is designed to be integrated as a node in the main conversation graph:

```python
from langgraph.graph import StateGraph, END
from app.agent.graphs import create_booking_subgraph

# Create main graph
main_graph = StateGraph(ConversationState)

# Add booking subgraph as a node
booking_subgraph = create_booking_subgraph(tools)
main_graph.add_node("booking", booking_subgraph)

# Add conditional routing from intent detection
main_graph.add_conditional_edges(
    "intent_detection",
    route_by_intent,
    {
        "greeting": "greeting",
        "search": "indoor_search",
        "booking": "booking",  # Routes to booking subgraph
        "faq": "faq"
    }
)

# Booking subgraph returns to END
main_graph.add_edge("booking", END)
```

## State Management

### Flow State

The subgraph updates `flow_state` as the user progresses through the booking:

```python
{
    "intent": "booking",
    "step": "select_time",  # Current step
    "property_id": "1",
    "property_name": "Downtown Sports Center",
    "service_id": "5",
    "service_name": "Tennis Court A",
    "sport_type": "tennis",
    "date": "2024-01-15",
    "time": "14:00",
    "duration": 60,
    "price": 50.00,
    "booking_id": None  # Set after booking is created
}
```

### Bot Memory

The subgraph reads from `bot_memory` to access search results:

```python
{
    "context": {
        "last_search_results": ["1", "2", "3"],
        "property_details": [
            {"id": 1, "name": "Downtown Sports Center", ...},
            {"id": 2, "name": "Westside Arena", ...}
        ]
    }
}
```

## Navigation Support

### Back Navigation

Users can go back to previous steps by saying:
- "back"
- "previous"
- "go back"
- "return"

Example:
```
Bot: "Which time slot would you like?"
User: "Actually, I want to go back and choose a different date"
→ Routes back to select_date node
```

### Cancellation

Users can cancel the booking at any step by saying:
- "cancel"
- "nevermind"
- "never mind"
- "stop"
- "quit"
- "exit"

Example:
```
Bot: "Which facility would you like to book?"
User: "cancel"
→ Routes to END, booking cancelled
```

### Modification

At the confirmation step, users can request modifications:
- "change"
- "modify"
- "edit"
- "different"
- "another"

Example:
```
Bot: "Please confirm your booking: Downtown Sports Center, Tennis Court A, 2024-01-15 at 14:00"
User: "I want to change the time"
→ Routes back to select_property (allows full modification)
```

## Error Handling

The routing functions handle edge cases gracefully:

1. **Missing data**: If required data is not in flow_state, routes to cancel
2. **Invalid selections**: Nodes handle invalid selections and prompt user to retry
3. **Unexpected states**: Logs warnings and routes to safe fallback (usually cancel)

## Logging

The subgraph includes comprehensive logging:

```python
logger.info(f"Property selected for chat {chat_id}: property_id={property_id}")
logger.warning(f"No service selected for chat {chat_id}, routing to cancel")
logger.debug(f"Date selected for chat {chat_id}: date={date}")
```

## Requirements Implemented

- **6.3**: Booking_Subgraph with nested nodes for booking flow
- **6.8**: Maintain state persistence between node transitions
- **22.1**: Present properties from search results
- **22.2**: Present booking summary including all details
- **22.3**: Ask for explicit user confirmation
- **22.4**: Create booking when user confirms
- **22.5**: Clear flow_state when user cancels
- **22.6**: Return to appropriate step when user requests changes

## Testing

To test the booking subgraph:

1. **Unit tests**: Test individual routing functions
2. **Integration tests**: Test full booking flow with mock tools
3. **End-to-end tests**: Test with real database and services

Example unit test:

```python
def test_route_property_selection():
    state = {
        "chat_id": "test-123",
        "user_message": "I selected property 1",
        "flow_state": {"property_id": "1"}
    }
    result = route_property_selection(state)
    assert result == "continue"
```

## Future Enhancements

Potential improvements to the booking subgraph:

1. **Smart routing**: Use LLM to understand complex modification requests
2. **Partial modifications**: Allow users to modify specific fields without restarting
3. **Validation**: Add more sophisticated validation at each step
4. **Retry logic**: Implement retry mechanisms for failed tool calls
5. **Timeout handling**: Add timeout logic for inactive sessions
