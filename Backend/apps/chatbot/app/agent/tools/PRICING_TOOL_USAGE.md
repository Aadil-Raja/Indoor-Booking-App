# Pricing Tool Usage Guide

## Overview

The pricing tool provides functions for retrieving pricing information and calculating total booking costs. It integrates with the management app's public_service through the sync bridge to access court pricing rules.

## Available Functions

### 1. get_pricing_tool

Get pricing information for a court on a specific date.

**Purpose**: Retrieve all pricing rules applicable to a specific court on a given date based on the day of week.

**Parameters**:
- `court_id` (int): ID of the court
- `date_val` (date): Date to get pricing for

**Returns**: Optional[Dict[str, Any]]
- Dictionary containing pricing information:
  - `date`: The requested date (ISO format string)
  - `day_of_week`: Day of week (0=Monday, 6=Sunday)
  - `pricing`: List of pricing rules, each containing:
    - `start_time`: Start time of pricing period (ISO format string)
    - `end_time`: End time of pricing period (ISO format string)
    - `price_per_hour`: Price per hour for this period
    - `label`: Pricing label (e.g., "Daytime Rate", "Evening Rate")
- Returns `None` if court not found or no pricing available

**Example Usage**:
```python
from datetime import date
from app.agent.tools.pricing_tool import get_pricing_tool

# Get pricing for a specific date
pricing = await get_pricing_tool(
    court_id=123,
    date_val=date(2024, 1, 15)
)

if pricing:
    print(f"Date: {pricing['date']}")
    print(f"Day of week: {pricing['day_of_week']}")
    print(f"Pricing rules: {len(pricing['pricing'])}")
    
    for rule in pricing['pricing']:
        print(f"{rule['start_time']}-{rule['end_time']}: ${rule['price_per_hour']}/hour ({rule['label']})")
else:
    print("No pricing information available")
```

**Error Handling**:
- Returns `None` if court not found
- Returns `None` if no pricing rules exist for the date
- Returns `None` on any exception
- Logs all errors for debugging

---

### 2. calculate_total_price

Calculate total price for a booking based on duration.

**Purpose**: Calculate the total cost for booking a court for a specific duration by applying the appropriate pricing rule.

**Parameters**:
- `court_id` (int): ID of the court
- `date_val` (date): Date of the booking
- `start_time` (time): Start time of the booking
- `duration_minutes` (int): Duration of the booking in minutes

**Returns**: Optional[float]
- Total price as a float rounded to 2 decimal places
- Returns `None` if pricing cannot be calculated

**Example Usage**:
```python
from datetime import date, time
from app.agent.tools.pricing_tool import calculate_total_price

# Calculate price for 1.5 hour booking
total = await calculate_total_price(
    court_id=123,
    date_val=date(2024, 1, 15),
    start_time=time(16, 0),  # 4:00 PM
    duration_minutes=90  # 1.5 hours
)

if total:
    print(f"Total price: ${total:.2f}")
else:
    print("Unable to calculate price")
```

**Calculation Logic**:
1. Retrieves pricing data for the specified date
2. Finds the pricing rule that applies to the start_time
3. Converts duration from minutes to hours (as float)
4. Multiplies duration by the applicable hourly rate
5. Rounds result to 2 decimal places

**Error Handling**:
- Returns `None` if no pricing data available
- Returns `None` if start_time doesn't fall within any pricing rule
- Returns `None` on any exception
- Logs all errors for debugging

**Important Notes**:
- Currently assumes the booking falls within a single pricing period
- Does not handle bookings that span multiple pricing periods
- Uses the rate applicable at the start_time for the entire duration

---

## Tool Registry

Both tools are registered in the `PRICING_TOOLS` dictionary for easy access:

```python
from app.agent.tools.pricing_tool import PRICING_TOOLS

# Access tools from registry
get_pricing = PRICING_TOOLS['get_pricing']
calculate_total = PRICING_TOOLS['calculate_total_price']

# Use the tools
pricing = await get_pricing(court_id=123, date_val=date.today())
total = await calculate_total(court_id=123, date_val=date.today(), start_time=time(14, 0), duration_minutes=60)
```

---

## Integration with Chatbot Agent

### Use Case 1: Booking Flow - Display Time Slots with Pricing

When presenting available time slots to users, include pricing information:

```python
from datetime import date, time
from app.agent.tools.availability_tool import get_available_slots_tool
from app.agent.tools.pricing_tool import get_pricing_tool

async def select_time_node(state: ConversationState) -> ConversationState:
    """Present available time slots with pricing to user"""
    flow_state = state.get("flow_state", {})
    court_id = flow_state.get("service_id")
    selected_date = flow_state.get("date")
    
    # Get available slots (already includes pricing)
    availability = await get_available_slots_tool(
        court_id=court_id,
        date_val=date.fromisoformat(selected_date)
    )
    
    if not availability or not availability['available_slots']:
        state["response_content"] = "Sorry, no time slots are available on this date."
        state["response_type"] = "text"
        return state
    
    # Format slots with pricing
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

### Use Case 2: Booking Confirmation - Calculate Total Cost

When confirming a booking, calculate and display the total cost:

```python
from datetime import date, time
from app.agent.tools.pricing_tool import calculate_total_price

async def confirm_booking_node(state: ConversationState) -> ConversationState:
    """Generate booking summary with total price"""
    flow_state = state.get("flow_state", {})
    
    court_id = flow_state.get("service_id")
    booking_date = date.fromisoformat(flow_state.get("date"))
    booking_time = time.fromisoformat(flow_state.get("time"))
    duration = flow_state.get("duration", 60)  # Default 60 minutes
    
    # Calculate total price
    total_price = await calculate_total_price(
        court_id=court_id,
        date_val=booking_date,
        start_time=booking_time,
        duration_minutes=duration
    )
    
    if not total_price:
        state["response_content"] = "Unable to calculate price. Please try again."
        state["response_type"] = "text"
        return state
    
    # Store price in flow_state
    flow_state["price"] = total_price
    state["flow_state"] = flow_state
    
    # Generate confirmation message
    property_name = flow_state.get("property_name")
    service_name = flow_state.get("service_name")
    
    response = f"""
Please confirm your booking:

Property: {property_name}
Court: {service_name}
Date: {booking_date.strftime('%B %d, %Y')}
Time: {booking_time.strftime('%I:%M %p')}
Duration: {duration} minutes
Total Price: ${total_price:.2f}

Reply 'confirm' to proceed or 'cancel' to cancel.
"""
    
    state["response_content"] = response.strip()
    state["response_type"] = "text"
    
    return state
```

### Use Case 3: Show Pricing Information

When a user asks about pricing for a specific date:

```python
from datetime import date
from app.agent.tools.pricing_tool import get_pricing_tool

async def show_pricing_info(court_id: int, date_val: date) -> str:
    """Show pricing information for a court on a specific date"""
    pricing = await get_pricing_tool(
        court_id=court_id,
        date_val=date_val
    )
    
    if not pricing:
        return "Pricing information is not available for this date."
    
    # Format response
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[pricing['day_of_week']]
    
    response = f"Pricing for {date_val.strftime('%B %d, %Y')} ({day_name}):\n\n"
    
    for rule in pricing['pricing']:
        response += f"• {rule['start_time']} - {rule['end_time']}: "
        response += f"${rule['price_per_hour']:.2f}/hour"
        if rule['label']:
            response += f" ({rule['label']})"
        response += "\n"
    
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
    public_service.get_court_pricing_for_date,
    db=None,  # Auto-managed by sync bridge
    court_id=court_id,
    date_val=date_val
)
```

### Service Integration

The tools integrate with the management app's public_service:

- **public_service.get_court_pricing_for_date()**: Returns pricing rules for a court on a specific date based on day of week

### Pricing Rule Matching

The `calculate_total_price` function matches the start_time to pricing rules:

```python
# Find applicable pricing rule
for rule in pricing_rules:
    rule_start = time.fromisoformat(rule['start_time'])
    rule_end = time.fromisoformat(rule['end_time'])
    
    # Check if start_time falls within this pricing rule
    if rule_start <= start_time < rule_end:
        applicable_rate = rule['price_per_hour']
        break
```

### Error Handling

All tools implement comprehensive error handling:

- Catch and log all exceptions
- Return safe default values (None)
- Log errors with full context for debugging
- Never expose internal errors to users

### Logging

All operations are logged for monitoring and debugging:

```python
import logging
logger = logging.getLogger(__name__)

# Logs include:
# - Function entry with parameters
# - Success with result details
# - Warnings for service failures
# - Errors with full stack traces
```

---

## Testing

Comprehensive unit tests are available in `test_pricing_tool.py`:

```bash
# Run all pricing tool tests
pytest app/agent/tools/test_pricing_tool.py -v

# Run specific test class
pytest app/agent/tools/test_pricing_tool.py::TestGetPricingTool -v

# Run specific test
pytest app/agent/tools/test_pricing_tool.py::TestCalculateTotalPrice::test_calculate_total_price_one_hour -v
```

---

## Best Practices

1. **Always handle None returns**: Check if results are None before processing

2. **Use appropriate date/time types**: Pass `date` and `time` objects, not strings

3. **Display prices clearly**: Always format prices with 2 decimal places

4. **Validate duration**: Ensure duration_minutes is positive and reasonable

5. **Cache pricing data**: Pricing rules don't change frequently, consider caching

6. **Provide context**: Show pricing labels to help users understand rate variations

7. **Handle edge cases**: Consider bookings at pricing period boundaries

---

## Common Patterns

### Pattern 1: Find cheapest time slot

```python
from datetime import date, time

pricing = await get_pricing_tool(court_id, date_val)
if pricing and pricing['pricing']:
    cheapest = min(pricing['pricing'], key=lambda r: r['price_per_hour'])
    print(f"Cheapest rate: ${cheapest['price_per_hour']}/hour ({cheapest['label']})")
    print(f"Available: {cheapest['start_time']} - {cheapest['end_time']}")
```

### Pattern 2: Calculate price for different durations

```python
from datetime import date, time

durations = [30, 60, 90, 120]  # minutes
start = time(14, 0)

for duration in durations:
    total = await calculate_total_price(court_id, date_val, start, duration)
    if total:
        hours = duration / 60
        print(f"{hours}h: ${total:.2f}")
```

### Pattern 3: Compare weekday vs weekend pricing

```python
from datetime import date, timedelta

# Get Monday pricing
monday = date(2024, 1, 15)
monday_pricing = await get_pricing_tool(court_id, monday)

# Get Saturday pricing
saturday = monday + timedelta(days=5)
saturday_pricing = await get_pricing_tool(court_id, saturday)

# Compare rates
if monday_pricing and saturday_pricing:
    weekday_avg = sum(r['price_per_hour'] for r in monday_pricing['pricing']) / len(monday_pricing['pricing'])
    weekend_avg = sum(r['price_per_hour'] for r in saturday_pricing['pricing']) / len(saturday_pricing['pricing'])
    
    print(f"Average weekday rate: ${weekday_avg:.2f}/hour")
    print(f"Average weekend rate: ${weekend_avg:.2f}/hour")
```

---

## Limitations and Future Enhancements

### Current Limitations

1. **Single pricing period assumption**: `calculate_total_price` assumes the entire booking falls within one pricing period. Bookings that span multiple periods (e.g., starting at 4:30 PM when rates change at 5:00 PM) use only the starting period's rate.

2. **No duration validation**: The tool doesn't validate if the booking duration extends beyond the pricing period's end time.

3. **No minimum duration enforcement**: Some facilities may have minimum booking durations (e.g., 30 minutes), which is not enforced.

### Potential Enhancements

1. **Multi-period pricing**: Calculate prices for bookings that span multiple pricing periods:
   ```python
   # Future enhancement
   total = calculate_price_across_periods(
       court_id=123,
       date_val=date(2024, 1, 15),
       start_time=time(16, 30),  # 4:30 PM
       end_time=time(18, 30)     # 6:30 PM (spans two periods)
   )
   ```

2. **Discount calculation**: Support for promotional discounts or loyalty programs

3. **Dynamic pricing**: Support for demand-based pricing adjustments

4. **Package deals**: Calculate prices for multi-session packages

---

## Troubleshooting

### Issue: None returned from get_pricing_tool

**Possible causes**:
- Court doesn't exist
- No pricing rules defined for the day of week
- Court is not active

**Solution**: Verify court exists and has pricing rules configured

### Issue: calculate_total_price returns None

**Possible causes**:
- No pricing data available for the date
- start_time doesn't fall within any pricing rule
- Pricing rules have gaps in coverage

**Solution**: Check pricing rules cover the desired time range

### Issue: Unexpected price calculation

**Possible causes**:
- Booking spans multiple pricing periods
- Duration calculation error
- Rounding differences

**Solution**: Verify the pricing rule being applied and check logs

---

## Related Documentation

- [Sync Bridge Usage](./SYNC_BRIDGE_USAGE.md)
- [Availability Tool Usage](./AVAILABILITY_TOOL_USAGE.md)
- [Court Tool Usage](./COURT_TOOL_USAGE.md)
- [Booking Flow Design](../../../../../../.kiro/specs/whatsapp-chatbot/design.md)

---

## Requirements Validation

This tool implements the following requirements:

- **Requirement 10.2**: Integrate pricing_service.get_pricing_for_time_slot as a tool
- **Requirement 10.4**: Display pricing information with time slots
- **Requirement 10.5**: Calculate total price for selected duration
- **Requirement 19.1-19.5**: Read-only access to main database through service interfaces
