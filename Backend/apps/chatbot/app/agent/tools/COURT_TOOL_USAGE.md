# Court Tool Usage Guide

## Overview

The court tool provides functions for searching courts by sport type and retrieving court details. It integrates with the sync management services through the sync bridge to access court data from the main database.

## Available Tools

### 1. search_courts_tool

Search for courts with optional filters.

**Parameters:**
- `sport_type` (Optional[str]): Sport type to filter by (e.g., "tennis", "basketball")
- `city` (Optional[str]): City name to filter properties by
- `property_id` (Optional[int]): Specific property ID to get courts from
- `limit` (int): Maximum number of results (default: 20)

**Returns:** List[Dict[str, Any]] - List of court dictionaries

**Example:**
```python
# Search for tennis courts in New York
courts = await search_courts_tool(
    sport_type="tennis",
    city="New York"
)

# Get all courts for a specific property
courts = await search_courts_tool(property_id=123)

# Get tennis courts for a specific property
courts = await search_courts_tool(
    property_id=123,
    sport_type="tennis"
)
```

### 2. get_court_details_tool

Get detailed information about a specific court.

**Parameters:**
- `court_id` (int): ID of the court to retrieve

**Returns:** Optional[Dict[str, Any]] - Court details or None if not found

**Example:**
```python
# Get court details
details = await get_court_details_tool(court_id=101)

# Access court information
if details:
    print(f"Court: {details['name']}")
    print(f"Sport: {details['sport_type']}")
    print(f"Property: {details['property']['name']}")
    print(f"Pricing: {details['pricing_rules']}")
```

### 3. get_property_courts_tool

Get all courts for a specific property.

**Parameters:**
- `property_id` (int): ID of the property
- `owner_id` (Optional[int]): Owner ID for ownership verification

**Returns:** List[Dict[str, Any]] - List of court dictionaries

**Example:**
```python
# Get courts for a property (public access)
courts = await get_property_courts_tool(property_id=123)

# Get courts with owner verification
courts = await get_property_courts_tool(
    property_id=123,
    owner_id=456
)
```

## Tool Registry

All tools are registered in the `COURT_TOOLS` dictionary for easy access:

```python
from app.agent.tools.court_tool import COURT_TOOLS

# Access tools from registry
search_courts = COURT_TOOLS['search_courts']
get_court_details = COURT_TOOLS['get_court_details']
get_property_courts = COURT_TOOLS['get_property_courts']
```

## Integration with LangGraph

The court tools can be used in LangGraph nodes to enable court search functionality:

```python
from app.agent.tools.court_tool import search_courts_tool, get_court_details_tool

async def indoor_search_handler(state: ConversationState, tools) -> ConversationState:
    """Handle facility search requests"""
    
    # Extract sport type from user message
    sport_type = extract_sport_type(state["user_message"])
    
    # Search for courts
    courts = await search_courts_tool(
        sport_type=sport_type,
        city=state.get("city")
    )
    
    # Format results for user
    if courts:
        state["response_content"] = format_court_results(courts)
        state["search_results"] = courts
    else:
        state["response_content"] = "No courts found matching your criteria."
    
    return state
```

## Error Handling

All court tool functions handle errors gracefully:

- **Service errors**: Return empty list or None
- **Network errors**: Return empty list or None
- **Invalid parameters**: Return empty list or None

Errors are logged with full context for debugging.

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 9.3**: Integrate court_service.search_courts_by_sport_type as a tool
- **Requirement 9.4**: Enable court search by sport type
- **Requirement 19.1-19.5**: Read-only access to main database through service interfaces

## Testing

Comprehensive unit tests are available in `test_court_tool.py`:

```bash
# Run court tool tests
python -m pytest app/agent/tools/test_court_tool.py -v

# Run verification script
python verify_court_tool.py
```

## Notes

- Court tools use the sync bridge to call sync services from async code
- All database operations are read-only
- The `_get_management_services()` helper handles dynamic import of management services
- Court search integrates with property search for comprehensive results
