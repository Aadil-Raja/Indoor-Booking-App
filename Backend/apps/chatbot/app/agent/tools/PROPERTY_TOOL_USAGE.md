# Property Tool Usage Guide

## Overview

The property tool provides three main functions for searching and retrieving property information from the main database. These tools integrate with the sync property_service and public_service through the sync bridge.

## Available Tools

### 1. `search_properties_tool`

Search for properties with optional filters.

**Parameters:**
- `owner_id` (str): Owner ID (required but can be used for filtering)
- `city` (Optional[str]): City name to filter by
- `sport_type` (Optional[str]): Sport type to filter courts by (e.g., "tennis", "basketball")
- `min_price` (Optional[float]): Minimum price per hour
- `max_price` (Optional[float]): Maximum price per hour
- `limit` (int): Maximum number of results (default: 10)

**Returns:** List[Dict[str, Any]] - List of property dictionaries

**Example:**
```python
from app.agent.tools.property_tool import search_properties_tool

# Search for tennis courts in New York
properties = await search_properties_tool(
    owner_id="123",
    city="New York",
    sport_type="tennis"
)

# Search with price range
properties = await search_properties_tool(
    owner_id="123",
    sport_type="basketball",
    min_price=30.0,
    max_price=100.0,
    limit=5
)
```

**Response Format:**
```json
[
    {
        "id": 1,
        "name": "Downtown Sports Center",
        "city": "New York",
        "state": "NY",
        "address": "123 Main St",
        "amenities": ["parking", "wifi"],
        "maps_link": "https://maps.example.com/1"
    }
]
```

### 2. `get_property_details_tool`

Get detailed information about a specific property.

**Parameters:**
- `property_id` (int): ID of the property to retrieve (required)
- `owner_id` (Optional[str]): Owner ID for ownership verification

**Returns:** Optional[Dict[str, Any]] - Property details or None if not found

**Example:**
```python
from app.agent.tools.property_tool import get_property_details_tool

# Get property details (public access)
details = await get_property_details_tool(property_id=123)

# Get property details with owner verification
details = await get_property_details_tool(
    property_id=123,
    owner_id="456"
)
```

**Response Format:**
```json
{
    "id": 1,
    "name": "Downtown Sports Center",
    "description": "Premier sports facility",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "phone": "555-1234",
    "email": "info@downtown.com",
    "amenities": ["parking", "wifi", "locker rooms"],
    "is_active": true,
    "courts": [
        {
            "id": 1,
            "name": "Court A",
            "sport_type": "tennis",
            "is_active": true
        }
    ]
}
```

### 3. `get_owner_properties_tool`

Get all properties owned by a specific owner.

**Parameters:**
- `owner_id` (str): Owner ID from OwnerProfile (required)

**Returns:** List[Dict[str, Any]] - List of properties owned by the owner

**Example:**
```python
from app.agent.tools.property_tool import get_owner_properties_tool

# Get all properties for an owner
properties = await get_owner_properties_tool(owner_id="123")
```

**Response Format:**
```json
[
    {
        "id": 1,
        "name": "Property 1",
        "city": "New York",
        "state": "NY",
        "is_active": true
    },
    {
        "id": 2,
        "name": "Property 2",
        "city": "Boston",
        "state": "MA",
        "is_active": true
    }
]
```

## Using the Tool Registry

All tools are registered in the `PROPERTY_TOOLS` dictionary for easy access:

```python
from app.agent.tools.property_tool import PROPERTY_TOOLS

# Access tools by name
search_tool = PROPERTY_TOOLS['search_properties']
details_tool = PROPERTY_TOOLS['get_property_details']
owner_tool = PROPERTY_TOOLS['get_owner_properties']

# Use the tools
properties = await search_tool(owner_id="123", city="Boston")
```

## Integration with LangGraph Agent

When integrating with LangGraph nodes, use the tools like this:

```python
from app.agent.tools.property_tool import PROPERTY_TOOLS

async def indoor_search_handler(state: ConversationState, tools) -> ConversationState:
    """Handle facility search requests"""
    
    user_message = state["user_message"]
    owner_id = state["owner_id"]
    
    # Search for properties
    properties = await tools["search_properties"](
        owner_id=owner_id,
        sport_type="tennis",
        city="New York"
    )
    
    # Format results for user
    if properties:
        response = f"Found {len(properties)} properties:\n"
        for prop in properties:
            response += f"- {prop['name']} in {prop['city']}\n"
    else:
        response = "No properties found matching your criteria."
    
    state["response_content"] = response
    return state
```

## Error Handling

All tools handle errors gracefully and return empty results on failure:

```python
# If service fails, returns empty list
properties = await search_properties_tool(owner_id="invalid")
# properties = []

# If property not found, returns None
details = await get_property_details_tool(property_id=999999)
# details = None
```

## Logging

All tools log their operations for debugging:

```python
# Logs include:
# - Search parameters
# - Number of results found
# - Errors and exceptions
# - Service call details
```

Check logs for detailed information about tool execution.

## Notes

1. **Properties are linked to OwnerProfile**: Properties belong to owners (OwnerProfile), not directly to users.

2. **Sync Bridge Integration**: All tools use the sync bridge to call sync services from async code.

3. **Database Sessions**: Database sessions are automatically managed by the sync bridge.

4. **Response Format**: All services return responses in the format:
   ```python
   {
       'success': bool,
       'message': str,
       'data': Any
   }
   ```

5. **Performance**: Tools use connection pooling and efficient queries for optimal performance.

## Testing

For testing, mock the `call_sync_service` function:

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_search_properties():
    mock_result = {
        'success': True,
        'data': {
            'items': [{'id': 1, 'name': 'Test Property'}]
        }
    }
    
    with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock:
        mock.return_value = mock_result
        
        result = await search_properties_tool(owner_id="123")
        assert len(result) == 1
```

## Next Steps

After implementing the property tool, proceed with:
- Task 7.3: Implement court search tool
- Task 7.4: Implement availability tool
- Task 7.5: Implement pricing tool
- Task 7.6: Implement booking tool

Each tool follows the same pattern as the property tool.
