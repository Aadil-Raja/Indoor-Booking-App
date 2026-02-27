# Select Date Node Usage Guide

## Overview

The `select_date` node handles date selection in the booking flow. It parses dates from user messages in various formats, validates that dates are in the future, and stores the selected date in `flow_state`.

## Requirements

**Implements:**
- Requirement 6.3: Booking_Subgraph with Select_Date node
- Requirement 20.4: Store selected date when user chooses a date
- Requirements 22.1-22.6: Booking confirmation flow

## Node Behavior

### Input State

The node expects:
- `flow_state.property_id` - Selected property ID (required)
- `flow_state.service_id` - Selected service/court ID (required)
- `flow_state.service_name` - Selected service name (for display)
- `flow_state.step` - Current step in booking flow

### Output State

The node updates:
- `flow_state.date` - Selected date in YYYY-MM-DD format
- `flow_state.step` - Updated to "select_date" or "date_selected"
- `response_content` - Message to display to user
- `response_type` - Message type (always "text")
- `response_metadata` - Empty dict

## Supported Date Formats

### Relative Dates
- `"today"` - Current date
- `"tomorrow"` - Next day
- `"in 3 days"` - 3 days from now
- `"in 1 day"` - Same as tomorrow

### Weekday Names
- `"next Monday"` - Next occurrence of Monday
- `"Monday"` - Next Monday (if today is Monday, gets next week)
- `"next Friday"` - Next occurrence of Friday
- Abbreviated: `"Mon"`, `"Tue"`, `"Wed"`, `"Thu"`, `"Fri"`, `"Sat"`, `"Sun"`

### ISO Format
- `"2024-12-25"` - Standard ISO format
- `"2024/12/25"` - Alternative separator

### Numeric Formats
- `"12/25/2024"` - MM/DD/YYYY
- `"12/25/24"` - MM/DD/YY (assumes 20XX)
- `"12/25"` - MM/DD (assumes current year, or next year if past)

### Natural Language
- `"December 25"` - Month name and day
- `"Dec 25"` - Abbreviated month
- `"25 December"` - Day first format
- `"December 25 2024"` - With year
- `"25 Dec 2025"` - Day first with year

## Flow Sequence

### 1. First Call - Prompt for Date

**Input:**
```python
{
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "Tennis Court A",
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "step": "service_selected"
    },
    ...
}
```

**Output:**
```python
{
    "response_content": "When would you like to book Tennis Court A? You can say something like 'tomorrow', 'next Monday', or provide a specific date like '2024-12-25'.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "step": "select_date"
    }
}
```

### 2. Second Call - Process Date Selection

**Input (Valid Date):**
```python
{
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "tomorrow",
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "step": "select_date"
    },
    ...
}
```

**Output (Valid Date):**
```python
{
    "response_content": "Perfect! You've selected Tuesday, January 16, 2024 for Tennis Court A. Now let's choose a time slot.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-01-16",
        "step": "date_selected"
    }
}
```

## Error Handling

### Invalid Date Format

**Input:**
```python
{
    "user_message": "some random text",
    "flow_state": {
        "service_name": "Tennis Court A",
        "step": "select_date"
    }
}
```

**Output:**
```python
{
    "response_content": "I couldn't understand that date. Please try again with a format like 'tomorrow', 'next Monday', or a specific date like '2024-12-25'.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "service_name": "Tennis Court A",
        "step": "select_date"  # Stays in select_date for retry
    }
}
```

### Past Date

**Input:**
```python
{
    "user_message": "2024-01-01",  # Assuming this is in the past
    "flow_state": {
        "service_name": "Tennis Court A",
        "step": "select_date"
    }
}
```

**Output:**
```python
{
    "response_content": "The date January 01, 2024 is in the past. Please provide a date that is today or in the future.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "service_name": "Tennis Court A",
        "step": "select_date"  # Stays in select_date for retry
    }
}
```

### Missing Service Selection

**Input:**
```python
{
    "user_message": "tomorrow",
    "flow_state": {
        "property_id": "1",
        "step": "property_selected"
    }
}
```

**Output:**
```python
{
    "response_content": "Please select a court first before choosing a date.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "property_id": "1",
        "step": "property_selected"
    }
}
```

## Integration with Booking Subgraph

The `select_date` node is part of the booking subgraph flow:

```
select_property → select_service → select_date → select_time → confirm → create_booking
```

### Routing Logic

**From select_service:**
- When `flow_state.step = "service_selected"`, route to `select_date`

**From select_date:**
- When `flow_state.step = "date_selected"`, route to `select_time`
- When user says "back", route to `select_service`
- When user says "cancel", route to END

## Testing

Run tests with:
```bash
cd Backend/apps/chatbot
pytest app/agent/nodes/booking/test_select_date.py -v
```

### Test Coverage

The test suite covers:
- Date already selected (skip processing)
- Missing service selection (error handling)
- Initial date prompt
- Valid date selection (various formats)
- Invalid date format handling
- Past date rejection
- Date parsing for all supported formats
- Case-insensitive parsing
- Edge cases (empty input, invalid input)

## Usage Example

```python
from app.agent.nodes.booking.select_date import select_date

# First call - prompt for date
state = {
    "chat_id": "test-chat-123",
    "user_message": "Tennis Court A",
    "flow_state": {
        "property_id": "1",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "step": "service_selected"
    }
}

result = await select_date(state)
# User sees: "When would you like to book Tennis Court A?..."

# Second call - process date
state["user_message"] = "next Monday"
state["flow_state"]["step"] = "select_date"

result = await select_date(state)
# result["flow_state"]["date"] = "2024-01-22"
# result["flow_state"]["step"] = "date_selected"
```

## Validation Rules

1. **Date must be parseable** - Must match one of the supported formats
2. **Date must be in the future** - Cannot be before today's date
3. **Service must be selected** - `flow_state.service_id` must exist

## Success Criteria

The node successfully completes when:
- `flow_state.date` is set to a valid YYYY-MM-DD string
- `flow_state.step = "date_selected"`
- Flow continues to `select_time` node

## Logging

The node logs:
- **INFO**: Date selection processing start
- **INFO**: Date prompt presented
- **INFO**: Date successfully selected
- **DEBUG**: Date already selected (skip)
- **WARNING**: Invalid date format
- **WARNING**: Past date provided
- **WARNING**: Missing service selection

## Future Enhancements

Potential improvements:
- Calendar widget for visual date selection
- Show available dates based on court availability
- Suggest alternative dates if selected date is fully booked
- Support date ranges for multi-day bookings
- Integration with holiday/blackout date system
- Timezone-aware date handling for international users
