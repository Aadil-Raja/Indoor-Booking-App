# Select Time Node Usage Guide

## Overview

The `select_time` node handles time slot selection in the booking flow. It retrieves available time slots with pricing information, presents them as list options, parses user selection, and stores the selected time in `flow_state`.

## Requirements

**Implements:**
- Requirement 6.3: Booking_Subgraph with Select_Time node
- Requirement 10.1: Integrate availability_service.check_blocked_slots() as a tool
- Requirement 10.2: Integrate pricing_service.get_pricing_for_time_slot() as a tool
- Requirement 10.3: Retrieve available time slots when user selects a date
- Requirement 10.4: Include pricing information when displaying time slots
- Requirement 10.5: Exclude blocked time slots from available options
- Requirement 10.6: Suggest alternative dates when no slots are available
- Requirement 20.5: Store selected time when user chooses a time slot
- Requirements 22.1-22.6: Booking confirmation flow
- Requirement 23.3: Support list message type for multiple choice selections

## Node Behavior

### Input State

The node expects:
- `flow_state.property_id` - Selected property ID (required)
- `flow_state.service_id` - Selected service/court ID (required)
- `flow_state.service_name` - Selected service name (for display)
- `flow_state.date` - Selected date in YYYY-MM-DD format (required)
- `flow_state.step` - Current step in booking flow

### Output State

The node updates:
- `flow_state.start_time` - Selected start time in HH:MM:SS format
- `flow_state.end_time` - Selected end time in HH:MM:SS format
- `flow_state.price` - Price per hour for the selected slot
- `flow_state.price_label` - Pricing label (e.g., "Morning Rate", "Peak Rate")
- `flow_state.step` - Updated to "select_time" or "time_selected"
- `response_content` - Message to display to user
- `response_type` - Message type ("list" or "text")
- `response_metadata` - List items with time slots and pricing

### Bot Memory

The node stores:
- `bot_memory.context.slot_details` - Available time slots for reference during selection

## Supported Time Selection Formats

### Exact Time Match
- `"14:00"` - 24-hour format without seconds
- `"14:00:00"` - 24-hour format with seconds
- `"09:00"` - Morning time

### 12-Hour Format with AM/PM
- `"9:00 AM"` - Morning time with AM
- `"2:00 PM"` - Afternoon time with PM
- `"2 pm"` - Without colon (hour only)
- `"9 am"` - Morning without colon

### Time Range
- `"2:00 PM - 3:00 PM"` - Full range with AM/PM
- `"14:00 - 15:00"` - 24-hour range

### Slot Index
- `"1"` - First slot
- `"2"` - Second slot
- `"first"` - First slot (word form)
- `"second"` - Second slot (word form)
- `"1st"`, `"2nd"`, `"3rd"` - Ordinal numbers

## Flow Sequence

### 1. First Call - Present Time Options

**Input:**
```python
{
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "2024-12-25",
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-12-25",
        "step": "date_selected"
    },
    "bot_memory": {},
    ...
}
```

**Output:**
```python
{
    "response_content": "Great! Here are the available time slots for Tennis Court A on Wednesday, December 25, 2024:",
    "response_type": "list",
    "response_metadata": {
        "list_items": [
            {
                "id": "09:00:00",
                "title": "9:00 AM - 10:00 AM",
                "description": "$50.00/hour (Morning Rate)"
            },
            {
                "id": "14:00:00",
                "title": "2:00 PM - 3:00 PM",
                "description": "$75.00/hour (Afternoon Rate)"
            },
            {
                "id": "16:00:00",
                "title": "4:00 PM - 5:00 PM",
                "description": "$75.00/hour (Evening Rate)"
            }
        ]
    },
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-12-25",
        "step": "select_time"
    },
    "bot_memory": {
        "context": {
            "slot_details": [
                {
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "price_per_hour": 50.0,
                    "label": "Morning Rate"
                },
                {
                    "start_time": "14:00:00",
                    "end_time": "15:00:00",
                    "price_per_hour": 75.0,
                    "label": "Afternoon Rate"
                },
                {
                    "start_time": "16:00:00",
                    "end_time": "17:00:00",
                    "price_per_hour": 75.0,
                    "label": "Evening Rate"
                }
            ]
        }
    }
}
```

### 2. Second Call - Process Time Selection

**Input (Valid Time):**
```python
{
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_message": "14:00",
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-12-25",
        "step": "select_time"
    },
    "bot_memory": {
        "context": {
            "slot_details": [
                {
                    "start_time": "14:00:00",
                    "end_time": "15:00:00",
                    "price_per_hour": 75.0,
                    "label": "Afternoon Rate"
                }
            ]
        }
    },
    ...
}
```

**Output (Valid Time):**
```python
{
    "response_content": "Perfect! You've selected 2:00 PM - 3:00 PM for Tennis Court A on Wednesday, December 25, 2024. The price is $75.00/hour (Afternoon Rate). Let me prepare your booking summary.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-12-25",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "price_label": "Afternoon Rate",
        "step": "time_selected"
    }
}
```

## Error Handling

### No Available Slots

**Input:**
```python
{
    "user_message": "2024-12-25",
    "flow_state": {
        "service_id": "10",
        "service_name": "Tennis Court A",
        "date": "2024-12-25",
        "step": "date_selected"
    }
}
```

**Output:**
```python
{
    "response_content": "I'm sorry, but there are no available time slots for Tennis Court A on Wednesday, December 25, 2024. Would you like to try a different date?",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "service_id": "10",
        "service_name": "Tennis Court A",
        "date": "2024-12-25",
        "step": "date_selected"  # Stays in date_selected to allow date change
    }
}
```

### Invalid Time Selection

**Input:**
```python
{
    "user_message": "18:00",  # Not available
    "flow_state": {
        "service_name": "Tennis Court A",
        "date": "2024-12-25",
        "step": "select_time"
    },
    "bot_memory": {
        "context": {
            "slot_details": [
                {
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "price_per_hour": 50.0,
                    "label": "Morning Rate"
                }
            ]
        }
    }
}
```

**Output:**
```python
{
    "response_content": "I couldn't find that time slot. Please select from the available options: 09:00:00 - 10:00:00",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "service_name": "Tennis Court A",
        "date": "2024-12-25",
        "step": "select_time"  # Stays in select_time for retry
    }
}
```

### Missing Date Selection

**Input:**
```python
{
    "user_message": "14:00",
    "flow_state": {
        "property_id": "1",
        "service_id": "10",
        "step": "service_selected"
    }
}
```

**Output:**
```python
{
    "response_content": "Please select a date first before choosing a time slot.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "property_id": "1",
        "service_id": "10",
        "step": "service_selected"
    }
}
```

### Missing Service Selection

**Input:**
```python
{
    "user_message": "14:00",
    "flow_state": {
        "property_id": "1",
        "date": "2024-12-25",
        "step": "date_selected"
    }
}
```

**Output:**
```python
{
    "response_content": "Please select a court first before choosing a time slot.",
    "response_type": "text",
    "response_metadata": {},
    "flow_state": {
        "property_id": "1",
        "date": "2024-12-25",
        "step": "date_selected"
    }
}
```

## Integration with Booking Subgraph

The `select_time` node is part of the booking subgraph flow:

```
select_property → select_service → select_date → select_time → confirm → create_booking
```

### Routing Logic

**From select_date:**
- When `flow_state.step = "date_selected"`, route to `select_time`

**From select_time:**
- When `flow_state.step = "time_selected"`, route to `confirm`
- When user says "back", route to `select_date`
- When user says "cancel", route to END

## Tool Integration

### get_available_slots Tool

The node calls `get_available_slots` tool to retrieve time slots:

```python
availability_data = await tools["get_available_slots"](
    court_id=service_id_int,
    date_val=date_obj
)
```

**Tool Response:**
```python
{
    "date": "2024-12-25",
    "court_id": 10,
    "court_name": "Tennis Court A",
    "available_slots": [
        {
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "price_per_hour": 50.0,
            "label": "Morning Rate"
        }
    ]
}
```

The tool automatically:
- Excludes blocked time slots
- Excludes existing bookings
- Includes pricing information for each slot
- Returns slots in chronological order

## Testing

Run tests with:
```bash
cd Backend/apps/chatbot
pytest app/agent/nodes/booking/test_select_time.py -v
```

### Test Coverage

The test suite covers:
- Time already selected (skip processing)
- Missing date/service selection (error handling)
- Presenting time options with pricing
- No available slots handling
- Valid time selection (various formats)
- Invalid time selection handling
- Time parsing for all supported formats
- Time formatting for display (12-hour with AM/PM)
- Slot formatting as list items
- Case-insensitive parsing
- Edge cases (empty input, invalid input)

## Usage Example

```python
from app.agent.nodes.booking.select_time import select_time

# First call - present time options
state = {
    "chat_id": "test-chat-123",
    "user_message": "2024-12-25",
    "flow_state": {
        "property_id": "1",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "date": "2024-12-25",
        "step": "date_selected"
    },
    "bot_memory": {}
}

result = await select_time(state, tools=mock_tools)
# User sees list of available time slots with pricing

# Second call - process time selection
state["user_message"] = "2:00 PM"
state["flow_state"]["step"] = "select_time"
state["bot_memory"] = result["bot_memory"]

result = await select_time(state, tools=mock_tools)
# result["flow_state"]["start_time"] = "14:00:00"
# result["flow_state"]["end_time"] = "15:00:00"
# result["flow_state"]["price"] = 75.0
# result["flow_state"]["step"] = "time_selected"
```

## Validation Rules

1. **Date must be selected** - `flow_state.date` must exist
2. **Service must be selected** - `flow_state.service_id` must exist
3. **Time must be available** - Must match one of the available slots
4. **Blocked slots excluded** - Automatically filtered by availability tool

## Success Criteria

The node successfully completes when:
- `flow_state.start_time` is set to a valid HH:MM:SS string
- `flow_state.end_time` is set to a valid HH:MM:SS string
- `flow_state.price` is set to the slot's price per hour
- `flow_state.step = "time_selected"`
- Flow continues to `confirm` node

## Time Display Formatting

The node formats times for user-friendly display:

| Input (24-hour) | Output (12-hour) |
|-----------------|------------------|
| `09:00:00` | `9:00 AM` |
| `09:30:00` | `9:30 AM` |
| `12:00:00` | `12:00 PM` |
| `14:00:00` | `2:00 PM` |
| `16:30:00` | `4:30 PM` |
| `00:00:00` | `12:00 AM` |

## Pricing Display

Pricing is displayed in the list item description:
- Format: `$XX.XX/hour (Label)`
- Example: `$75.00/hour (Afternoon Rate)`
- If no label: `$50.00/hour`

## Logging

The node logs:
- **INFO**: Time selection processing start
- **INFO**: Time options presented with slot count
- **INFO**: Time successfully selected with details
- **DEBUG**: Time already selected (skip)
- **DEBUG**: Retrieving available slots
- **WARNING**: Invalid time selection
- **WARNING**: No available slots found
- **WARNING**: Missing date/service selection
- **ERROR**: Error retrieving available slots
- **ERROR**: Invalid date format in flow_state

## Future Enhancements

Potential improvements:
- Duration selection (1 hour, 1.5 hours, 2 hours)
- Multi-slot booking for longer sessions
- Show total price based on duration
- Real-time availability updates
- Peak/off-peak pricing indicators
- Slot recommendations based on user preferences
- Calendar view with time slot availability
- Recurring booking support (weekly, monthly)
- Waitlist for fully booked slots
- Dynamic pricing based on demand

