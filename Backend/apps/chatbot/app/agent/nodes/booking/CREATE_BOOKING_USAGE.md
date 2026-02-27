# Create Booking Node Usage Guide

## Overview

The `create_pending_booking` node is the final step in the booking subgraph. It creates a booking with pending status by calling the booking tool, stores the booking_id in flow_state, handles errors gracefully, clears booking fields from flow_state on completion, and generates a confirmation message with booking details.

## Requirements Implemented

- **6.3**: Booking_Subgraph with Create_Pending_Booking node
- **8.1**: Call booking_service.create_booking() when booking is confirmed
- **8.2**: Create booking with pending status
- **8.3**: Store booking_id in flow_state when booking is created successfully
- **8.4**: Inform user and retain booking details in flow_state for retry when booking creation fails
- **8.5**: Clear booking-specific fields from flow_state when booking is completed
- **8.6**: Preserve bot_memory for conversation context after booking completion
- **20.8**: Clear booking-related fields from Flow_State when booking is completed or cancelled
- **22.1-22.6**: Booking confirmation flow requirements

## Node Behavior

### Input Requirements

The node expects the following fields in `flow_state`:
- `service_id`: ID of the selected court/service (required)
- `date`: Booking date in YYYY-MM-DD format (required)
- `start_time`: Start time in HH:MM:SS format (required)
- `end_time`: End time in HH:MM:SS format (required)
- `property_name`: Name of the property (for confirmation message)
- `service_name`: Name of the court/service (for confirmation message)
- `sport_type`: Type of sport (for confirmation message)
- `total_price`: Total price of the booking (for confirmation message)
- `duration_hours`: Duration in hours (for confirmation message)

The node also requires:
- `user_id`: ID of the user making the booking (from state)

### Processing Steps

1. **Validate Required Fields**: Checks that all required booking fields are present
2. **Parse Date and Time**: Converts string dates/times to proper Python objects
3. **Convert IDs**: Converts user_id and service_id to integers
4. **Call Booking Tool**: Calls `create_booking` tool with booking details
5. **Handle Success**:
   - Stores `booking_id` in flow_state
   - Generates confirmation message with booking details
   - Updates step to "booking_created"
   - Clears booking fields from flow_state
6. **Handle Failure**:
   - Generates error message with retry information
   - Updates step to "booking_failed"
   - Retains booking details in flow_state for retry
   - Stores error message in flow_state

### Output

The node updates the state with:
- `response_content`: Confirmation or error message
- `response_type`: "text"
- `response_metadata`: Empty dict
- `flow_state`: Updated with booking_id (on success) or error_message (on failure)

### Flow State Changes

**On Success:**
- Adds: `booking_id`
- Updates: `step` to "booking_created"
- Removes: `property_id`, `property_name`, `service_id`, `service_name`, `sport_type`, `date`, `start_time`, `end_time`, `price`, `price_label`, `total_price`, `duration_hours`, `error_message`

**On Failure:**
- Updates: `step` to "booking_failed"
- Adds: `error_message`
- Retains: All booking details for retry

## Usage Example

```python
from app.agent.nodes.booking.create_booking import create_pending_booking
from app.agent.tools import initialize_tools

# Initialize tools
tools = initialize_tools()

# State after user confirms booking
state = {
    "chat_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456",
    "owner_id": "789",
    "user_message": "yes, confirm",
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
        "price": 50.0,
        "total_price": 50.0,
        "duration_hours": 1.0,
        "step": "confirmed"
    },
    "bot_memory": {},
    "messages": [],
    "response_content": "",
    "response_type": "text",
    "response_metadata": {}
}

# Process booking creation
result = await create_pending_booking(state, tools)

# Result on success:
# result["flow_state"]["booking_id"] = 123
# result["flow_state"]["step"] = "booking_created"
# result["response_content"] contains confirmation message
# Booking fields cleared from flow_state
```

## Success Response Format

```
🎉 Booking Confirmed!

Your booking has been successfully created with ID: 123

Booking Details:
📍 Location: Downtown Sports Center
🏟️ Court: Tennis Court A
⚽ Sport: Tennis
📅 Date: Wednesday, December 25, 2024
⏰ Time: 2:00 PM - 3:00 PM
⏱️ Duration: 1 hour
💰 Total Price: $50.00

Your booking is currently pending. You will receive a confirmation once payment is processed.

Thank you for booking with us! Is there anything else I can help you with?
```

## Error Response Format

```
❌ Booking Failed

I'm sorry, but I couldn't create your booking: This time slot is already booked

Your booking details:
📍 Downtown Sports Center
🏟️ Tennis Court A
📅 Wednesday, December 25, 2024
⏰ 2:00 PM - 3:00 PM

Would you like to:
• Try booking again
• Select a different time slot
• Start a new booking

Just let me know what you'd like to do!
```

## Error Handling

The node handles the following error scenarios:

1. **Missing Required Fields**: Returns error message and resets to property selection
2. **Invalid Date/Time Format**: Returns error message and resets to date/time selection
3. **Invalid User ID**: Returns error message with support contact information
4. **Invalid Service ID**: Returns error message and resets to service selection
5. **Booking Tool Not Found**: Returns system error message
6. **Booking Creation Failure**: Returns error message with retry options, retains booking details
7. **Unexpected Exception**: Returns error message with retry option, retains booking details

## Integration with Booking Subgraph

The node is the final step in the booking subgraph flow:

```
Select Property → Select Service → Select Date → Select Time → Confirm → Create Booking → END
```

After this node completes successfully:
- The booking is created in the database with pending status
- The booking_id is stored in flow_state
- All booking fields are cleared from flow_state
- The user receives a confirmation message
- The conversation can continue with a new topic

## Testing

The node includes comprehensive error handling and has been tested with:
- Successful booking creation
- Booking creation failures
- Missing required fields
- Invalid date/time formats
- Invalid user/service IDs

See `test_create_booking_simple.py` for test examples.

## Notes

- The node uses the `create_booking` tool from the tool registry
- The booking is created with pending status awaiting payment
- All booking fields are cleared from flow_state after successful creation
- Bot_memory is preserved for conversation context
- Error messages provide clear guidance for retry or modification
- The node follows the same pattern as other booking nodes for consistency
