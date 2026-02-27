# Availability Tool Usage Guide

## Overview

The availability tool provides functions for checking court availability and retrieving available time slots for booking. It integrates with the management app's availability_service and public_service through the sync bridge.

## Available Functions

### 1. check_availability_tool

Check blocked time slots for a specific court.

**Purpose**: Retrieve all blocked time slots for a court, optionally filtering from a specific date onwards.

**Parameters**:
- `court_id` (int): ID of the court to check
- `owner_id` (int): Owner ID for ownership verification
- `from_date` (Optional[date]): Start date to filter blocked slots (defaults to today if not provided)

**Returns**: List[Dict[str, Any]]
- List of blocked slot dictionaries, each containing:
  - `id`: Blocked slot ID
  - `date`: Date of the blocked slot (ISO format string)
  - `start_time`: Start time of the block (ISO format string)
  - `end_time`: End time of the block (ISO format string)
  - `reason`: Reason for blocking (optional)

**Example Usage**:
```python
from datetime import date
from app.agent.tools.availability_tool import check_availability_tool

# Check blocked slots from today onwards
blocked_slots = await check_availability_tool(
    court_id=123,
    owner_id=456
)

# Check blocked slots from a specific date
blocked_slots = await check_availability_tool(
    court_id=123,
    owner_id=456,
    from_date=date(2024, 1, 15)
)

# Process results
for slot in blocked_slots:
    print(f"Blocked: {slot['date']} {slot['start_time']}-{slot['end_time']}")
    print(f"Reason: {slot['reason']}")
```

**Error Handling**:
- Returns empty list `[]` if court not found
- Returns empty list `[]` if owner doesn't have access
- Returns empty list `[]` on any exception
- Logs all errors for debugging

---

### 2. get_available_slots_tool

Get available time slots for a court on a specific date.

**Purpose**: Retrieve all available time slots for booking, excluding blocked slots and existing bookings, with pricing information.

**Parameters**:
- `court_id` (int): ID of the court
- `date_val` (date): Date to check availability for

**Returns**: Optional[Dict[str, Any]]
- Dictionary containing availability information:
  - `date`: The requested date (ISO format string)
  - `court_id`: The court ID
  - `court_name`: Name of the court
  - `available_slots`: List of available time slots, each containing:
    - `start_time`: Slot start time (ISO format string)
    - `end_time`: Slot end time (ISO format string)
    - `price_per_hour`: Price for this time slot
    - `label`: Pricing label (e.g., "Morning Rate", "Peak Hours")
- Returns `None` if court not found or not available on the date

**Example Usage**:
```python
from datetime import date
from app.agent.tools.availability_tool import get_available_slots_tool

# Get available slots for a specific date
availability = await get_available_slots_tool(
    court_id=123,
    date_val=date(2024, 1, 15)
)

if availability:
    print(f"Court: {availability['court_name']}")
    print(f"Date: {availability['date']}")
    print(f"Available slots: {len(availability['available_slots'])}")
    
    for slot in availability['available_slots']:
        print(f"{slot['start_time']}-{slot['end_time']}: ${slot['price_per_hour']}/hour ({slot['label']})")
else:
    print("No availability found")
```

**Error Handling**:
- Returns `None` if court not found
- Returns `None` if court not available on the specified date
- Returns `None` on any exception
- Logs all errors for debugging

---

## Tool Registry

Both tools are registered in the `AVAILABILITY_TOOLS` dictionary for easy access:

```python
from app.agent.tools.availability_tool import AVAILABILITY_TOOLS

# Access tools from registry
check_availability = AVAILABILITY_TOOLS['check_availability']
get_available_slots = AVAILABILITY_TOOLS['get_available_slots']

# Use the tools
blocked = await check_availability(court_id=123, owner_id=456)
slots = await get_available_slots(court_id=123, date_val=date.today())
```

---

## Integration with Chatbot Agent

### Use Case 1: Booking Flow - Select Time

When a user is booking a court and needs to select a time slot:

```python
from datetime import date
from app.agent.tools.availability_tool import get_available_slots_tool

async def select_time_node(state: ConversationState) -> ConversationState:
    """Present available time slots to user"""
    flow_state = state.get("flow_state", {})
    court_id = flow_state.get("service_id")  # Court ID from previous selection
    selected_date = flow_state.get("date")  # Date from previous selection
    
    # Get available slots
    availability = await get_available_slots_tool(
        court_id=court_id,
        date_val=date.fromisoformat(selected_date)
    )
    
    if not availability or not availability['available_slots']:
        state["response_content"] = "Sorry, no time slots are available on this date."
        state["response_type"] = "text"
        return state
    
    # Format as list message for user selection
    list_items = []
    for slot in availability['available_slots']:
        list_items.append({
            "id": slot['start_time'],
            "title": f"{slot['start_time']} - {slot['end_time']}",
            "description": f"${slot['price_per_hour']}/hour - {slot['label']}"
        })
    
    state["response_content"] = "Please select a time slot:"
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    return state
```

### Use Case 2: Owner Dashboard - View Blocked Slots

When an owner wants to see their blocked time slots:

```python
from datetime import date
from app.agent.tools.availability_tool import check_availability_tool

async def show_blocked_slots(court_id: int, owner_id: int):
    """Show blocked slots for a court"""
    blocked_slots = await check_availability_tool(
        court_id=court_id,
        owner_id=owner_id,
        from_date=date.today()
    )
    
    if not blocked_slots:
        return "No blocked time slots found."
    
    # Format response
    response = f"Blocked time slots for court {court_id}:\n\n"
    for slot in blocked_slots:
        response += f"• {slot['date']} {slot['start_time']}-{slot['end_time']}\n"
        if slot['reason']:
            response += f"  Reason: {slot['reason']}\n"
    
    return response
```

---

## Technical Details

### Sync Bridge Integration

Both tools use the sync bridge to call synchronous management services from async code:

```python
from app.agent.tools.sync_bridge import call_sync_service

# The tools automatically handle:
# - Thread pool execution
# - Database session management
# - Error handling and cleanup
result = await call_sync_service(
    availability_service.get_blocked_slots,
    db=None,  # Auto-managed by sync bridge
    court_id=court_id,
    owner_id=owner_id,
    from_date=from_date
)
```

### Service Integration

The tools integrate with two management services:

1. **availability_service**: For checking blocked slots (owner-specific)
   - `get_blocked_slots()`: Returns blocked time slots for a court

2. **public_service**: For getting available slots (public access)
   - `get_available_slots()`: Returns available time slots with pricing

### Error Handling

All tools implement comprehensive error handling:

- Catch and log all exceptions
- Return safe default values (empty list or None)
- Log errors with full context for debugging
- Never expose internal errors to users

### Logging

All operations are logged for monitoring and debugging:

```python
import logging
logger = logging.getLogger(__name__)

# Logs include:
# - Function entry with parameters
# - Success with result counts
# - Warnings for service failures
# - Errors with full stack traces
```

---

## Testing

Comprehensive unit tests are available in `test_availability_tool.py`:

```bash
# Run all availability tool tests
pytest app/agent/tools/test_availability_tool.py -v

# Run specific test class
pytest app/agent/tools/test_availability_tool.py::TestCheckAvailabilityTool -v

# Run specific test
pytest app/agent/tools/test_availability_tool.py::TestCheckAvailabilityTool::test_check_availability_success -v
```

---

## Best Practices

1. **Always handle None/empty returns**: Check if results are None or empty before processing

2. **Use appropriate date types**: Pass `date` objects, not strings

3. **Verify ownership**: The `check_availability_tool` requires owner_id for access control

4. **Cache results when appropriate**: Available slots don't change frequently within a short time

5. **Provide user feedback**: Always inform users when no slots are available

6. **Log important operations**: Use the logger for debugging and monitoring

---

## Common Patterns

### Pattern 1: Check if any slots available before showing details

```python
availability = await get_available_slots_tool(court_id, date_val)
if availability and availability['available_slots']:
    # Show slots to user
    pass
else:
    # Suggest alternative dates
    pass
```

### Pattern 2: Filter slots by time of day

```python
from datetime import time

availability = await get_available_slots_tool(court_id, date_val)
if availability:
    morning_slots = [
        slot for slot in availability['available_slots']
        if time.fromisoformat(slot['start_time']) < time(12, 0)
    ]
```

### Pattern 3: Find cheapest available slot

```python
availability = await get_available_slots_tool(court_id, date_val)
if availability and availability['available_slots']:
    cheapest = min(
        availability['available_slots'],
        key=lambda s: s['price_per_hour']
    )
    print(f"Cheapest slot: {cheapest['start_time']} at ${cheapest['price_per_hour']}/hour")
```

---

## Troubleshooting

### Issue: Empty results when slots should exist

**Possible causes**:
- Court ID is incorrect
- Owner ID doesn't match court's property owner
- Date is in the past
- Court is not active

**Solution**: Check logs for specific error messages

### Issue: None returned from get_available_slots_tool

**Possible causes**:
- Court doesn't exist
- No pricing rules defined for the date
- Court not available on that day of week

**Solution**: Verify court configuration and pricing rules

### Issue: Blocked slots not showing

**Possible causes**:
- from_date is after the blocked slots
- Owner ID doesn't have access to the court
- Blocked slots were deleted

**Solution**: Check from_date parameter and ownership

---

## Related Documentation

- [Sync Bridge Usage](./SYNC_BRIDGE_USAGE.md)
- [Property Tool Usage](./PROPERTY_TOOL_USAGE.md)
- [Court Tool Usage](./COURT_TOOL_USAGE.md)
- [Booking Flow Design](../../../../../../.kiro/specs/whatsapp-chatbot/design.md)
