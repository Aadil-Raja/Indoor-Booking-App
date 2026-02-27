# Tool Registry Usage Guide

## Overview

The tool registry provides a centralized dictionary of all available tools that the LangGraph agent can use to interact with external services. All tools are async functions that integrate with the main database services through the sync bridge.

## Available Tools

### Property Tools (3)
- `search_properties`: Search for properties with filters (city, sport_type, price range)
- `get_property_details`: Get detailed information about a specific property
- `get_owner_properties`: Get all properties owned by a specific owner

### Court Tools (3)
- `search_courts`: Search for courts by sport type and other filters
- `get_court_details`: Get detailed information about a specific court
- `get_property_courts`: Get all courts for a specific property

### Availability Tools (2)
- `check_availability`: Check blocked time slots for a court
- `get_available_slots`: Get available time slots for a court on a specific date

### Pricing Tools (2)
- `get_pricing`: Get pricing information for a court on a specific date
- `calculate_total_price`: Calculate total price for a booking based on duration

### Booking Tools (3)
- `create_booking`: Create a new booking with pending status
- `get_booking_details`: Get details of a specific booking
- `cancel_booking`: Cancel a booking (customer only)

## Basic Usage

### Initialize Tools

```python
from app.agent.tools import initialize_tools

# Initialize the tool registry
tools = initialize_tools()

# Access individual tools
properties = await tools["search_properties"](
    owner_id="123",
    city="New York",
    sport_type="tennis"
)
```

### Get a Specific Tool

```python
from app.agent.tools import get_tool

# Get a specific tool by name
search_tool = get_tool("search_properties")
results = await search_tool(owner_id="123", city="New York")
```

### List All Available Tools

```python
from app.agent.tools import list_tools

# Get list of all tool names
available_tools = list_tools()
print(f"Available tools: {', '.join(available_tools)}")
```

### Direct Import

```python
# Import specific tools directly
from app.agent.tools import (
    search_properties_tool,
    create_booking_tool,
    get_available_slots_tool,
)

# Use directly
properties = await search_properties_tool(
    owner_id="123",
    city="New York"
)
```

## Usage in LangGraph Nodes

### Example: Search Handler Node

```python
from app.agent.tools import initialize_tools

async def indoor_search_handler(state: ConversationState) -> ConversationState:
    """Handle facility search requests"""
    
    # Initialize tools
    tools = initialize_tools()
    
    # Extract parameters from state
    user_message = state["user_message"]
    owner_id = state["owner_id"]
    
    # Use search tool
    properties = await tools["search_properties"](
        owner_id=owner_id,
        sport_type="tennis",
        city="New York"
    )
    
    # Process results and update state
    state["search_results"] = properties
    state["response_content"] = f"Found {len(properties)} properties"
    
    return state
```

### Example: Booking Handler Node

```python
from app.agent.tools import initialize_tools
from datetime import date, time

async def create_booking_handler(state: ConversationState) -> ConversationState:
    """Handle booking creation"""
    
    # Initialize tools
    tools = initialize_tools()
    
    # Extract booking details from flow_state
    flow_state = state["flow_state"]
    
    # Create booking
    result = await tools["create_booking"](
        customer_id=int(state["user_id"]),
        court_id=flow_state["service_id"],
        booking_date=date.fromisoformat(flow_state["date"]),
        start_time=time.fromisoformat(flow_state["time"]),
        end_time=time.fromisoformat(flow_state["end_time"]),
        notes="Booking via chatbot"
    )
    
    # Handle result
    if result["success"]:
        booking_id = result["data"]["id"]
        flow_state["booking_id"] = booking_id
        state["response_content"] = "Booking created successfully!"
    else:
        state["response_content"] = f"Booking failed: {result['message']}"
    
    return state
```

## Tool Response Formats

### Success Response
```python
{
    "success": True,
    "message": "Operation completed successfully",
    "data": {
        # Result data
    }
}
```

### Error Response
```python
{
    "success": False,
    "message": "Error description"
}
```

### List Response
```python
[
    {
        "id": 123,
        "name": "Property Name",
        # ... other fields
    },
    # ... more items
]
```

## Dependency Injection (Future)

The `initialize_tools()` function supports dependency injection for future extensions:

```python
# Future: Initialize with custom dependencies
tools = initialize_tools(
    db_session=session,
    config=app_config,
    cache=redis_client
)
```

Currently, all tools use the sync bridge which manages its own database sessions, so no dependencies are required.

## Error Handling

All tools handle errors gracefully and return appropriate responses:

```python
try:
    result = await tools["create_booking"](
        customer_id=123,
        court_id=456,
        booking_date=date(2024, 1, 15),
        start_time=time(14, 0),
        end_time=time(15, 30)
    )
    
    if result["success"]:
        # Handle success
        booking_id = result["data"]["id"]
    else:
        # Handle business logic error
        error_message = result["message"]
        
except Exception as e:
    # Handle unexpected error
    logger.error(f"Unexpected error: {e}")
```

## Testing

The tool registry includes comprehensive tests:

```bash
# Run tool registry tests
cd Backend/apps/chatbot
python -m pytest app/agent/tools/test_tool_registry.py -v
```

## Best Practices

1. **Always initialize tools at the start of your handler**
   ```python
   tools = initialize_tools()
   ```

2. **Use descriptive variable names**
   ```python
   properties = await tools["search_properties"](...)
   booking_result = await tools["create_booking"](...)
   ```

3. **Check success status before accessing data**
   ```python
   if result["success"]:
       data = result["data"]
   ```

4. **Log tool usage for debugging**
   ```python
   logger.info(f"Calling search_properties with owner_id={owner_id}")
   result = await tools["search_properties"](owner_id=owner_id)
   logger.info(f"Found {len(result)} properties")
   ```

5. **Handle errors gracefully**
   ```python
   try:
       result = await tools["create_booking"](...)
   except Exception as e:
       logger.error(f"Booking failed: {e}")
       # Provide fallback response
   ```

## Integration with LangGraph

The tool registry is designed to work seamlessly with LangGraph:

```python
from langgraph.graph import StateGraph
from app.agent.tools import initialize_tools

def create_main_graph():
    """Create the main conversation flow graph"""
    
    # Initialize tools once
    tools = initialize_tools()
    
    # Create graph
    graph = StateGraph(ConversationState)
    
    # Add nodes with tools
    graph.add_node("search", lambda state: search_handler(state, tools))
    graph.add_node("booking", lambda state: booking_handler(state, tools))
    
    return graph.compile()
```

## Sync Bridge Integration

All tools use the sync bridge to safely call synchronous services from async code:

- Database sessions are automatically managed
- Thread pool execution ensures thread safety
- Proper error handling and rollback on failures
- No manual session management required

See `SYNC_BRIDGE_USAGE.md` for more details on the sync bridge.
