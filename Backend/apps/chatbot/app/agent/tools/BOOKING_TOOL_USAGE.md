# Booking Tool Usage Guide

This document provides comprehensive guidance on using the booking tools in the chatbot agent.

## Overview

The booking tool module (`booking_tool.py`) provides three main functions for managing bookings:

1. **create_booking_tool** - Create new bookings with pending status
2. **get_booking_details_tool** - Retrieve detailed booking information
3. **cancel_booking_tool** - Cancel existing bookings

All tools integrate with the sync booking_service through the sync bridge, ensuring proper database transaction management and error handling.

## Tool Functions

### 1. create_booking_tool

Creates a new booking with pending status awaiting confirmation or payment.

**Signature:**
```python
async def create_booking_tool(
    customer_id: int,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `customer_id` (int): ID of the customer making the booking (user_id)
- `court_id` (int): ID of the court to book
- `booking_date` (date): Date of the booking
- `start_time` (time): Start time of the booking
- `end_time` (time): End time of the booking
- `notes` (str, optional): Optional notes for the booking (max 500 characters)

**Returns:**
Dictionary containing:
- `success` (bool): Whether the booking was created successfully
- `message` (str): Success or error message
- `data` (dict, if success=True): Booking details including:
  - `id`: Booking ID
  - `booking_date`: Date in ISO format
  - `start_time`: Start time in ISO format
  - `end_time`: End time in ISO format
  - `total_price`: Total cost of the booking
  - `status`: Booking status (always "pending" for new bookings)
  - `payment_status`: Payment status (always "pending" for new bookings)

**Validations Performed:**
- Court exists and is active
- Time slot is not blocked (maintenance, etc.)
- No booking conflicts exist
- Pricing is available for the time slot
- Booking date is not in the past
- End time is after start time

**Example Usage:**
```python
from datetime import date, time
from app.agent.tools.booking_tool import create_booking_tool

# Create a booking
result = await create_booking_tool(
    customer_id=123,
    court_id=456,
    booking_date=date(2024, 1, 15),
    start_time=time(14, 0),
    end_time=time(15, 30),
    notes="Birthday party booking"
)

if result['success']:
    booking_id = result['data']['id']
    total_price = result['data']['total_price']
    print(f"Booking created: ID={booking_id}, Price=${total_price}")
else:
    print(f"Booking failed: {result['message']}")
```

**Success Response Example:**
```json
{
    "success": true,
    "message": "Booking created successfully",
    "data": {
        "id": 789,
        "booking_date": "2024-01-15",
        "start_time": "14:00:00",
        "end_time": "15:30:00",
        "total_price": 75.0,
        "status": "pending",
        "payment_status": "pending"
    }
}
```

**Error Response Examples:**
```json
{
    "success": false,
    "message": "Court not found or inactive"
}

{
    "success": false,
    "message": "This time slot is already booked"
}

{
    "success": false,
    "message": "Court is not available during this time. Reason: Maintenance"
}

{
    "success": false,
    "message": "No pricing available for this time slot"
}

{
    "success": false,
    "message": "Invalid booking data: end_time must be after start_time"
}
```

### 2. get_booking_details_tool

Retrieves detailed information about a specific booking.

**Signature:**
```python
async def get_booking_details_tool(
    booking_id: int,
    user_id: int
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `booking_id` (int): ID of the booking to retrieve
- `user_id` (int): ID of the user requesting the details (for access control)

**Access Control:**
Only the following users can access booking details:
- The customer who made the booking
- The property owner where the court is located

**Returns:**
Dictionary containing:
- `success` (bool): Whether the booking was found and accessible
- `message` (str): Success or error message
- `data` (dict, if success=True): Detailed booking information including:
  - Booking details (id, dates, times, pricing, status)
  - Court information (id, name, sport_type)
  - Property information (id, name, address, phone)
  - Customer information (only visible to property owner)

**Example Usage:**
```python
from app.agent.tools.booking_tool import get_booking_details_tool

# Get booking details
result = await get_booking_details_tool(
    booking_id=789,
    user_id=123
)

if result['success']:
    booking = result['data']
    print(f"Booking at {booking['property']['name']}")
    print(f"Court: {booking['court']['name']}")
    print(f"Date: {booking['booking_date']} {booking['start_time']}-{booking['end_time']}")
    print(f"Total: ${booking['total_price']}")
else:
    print(f"Error: {result['message']}")
```

**Success Response Example:**
```json
{
    "success": true,
    "message": "Booking details retrieved successfully",
    "data": {
        "id": 789,
        "booking_date": "2024-01-15",
        "start_time": "14:00:00",
        "end_time": "15:30:00",
        "total_hours": 1.5,
        "price_per_hour": 50.0,
        "total_price": 75.0,
        "status": "pending",
        "payment_status": "pending",
        "notes": "Birthday party booking",
        "court": {
            "id": 456,
            "name": "Tennis Court A",
            "sport_type": "tennis"
        },
        "property": {
            "id": 123,
            "name": "Downtown Sports Center",
            "address": "123 Main St",
            "phone": "555-0100"
        }
    }
}
```

**Error Response Examples:**
```json
{
    "success": false,
    "message": "Booking not found"
}

{
    "success": false,
    "message": "Access denied"
}
```

### 3. cancel_booking_tool

Cancels an existing booking (customer only).

**Signature:**
```python
async def cancel_booking_tool(
    booking_id: int,
    user_id: int
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `booking_id` (int): ID of the booking to cancel
- `user_id` (int): ID of the user (must be the customer who made the booking)

**Access Control:**
- Only the customer who made the booking can cancel it
- Property owners cannot cancel bookings (they can only confirm/complete them)

**Restrictions:**
- Cannot cancel already cancelled bookings
- Cannot cancel completed bookings
- If payment was made, it will be marked for refund

**Returns:**
Dictionary containing:
- `success` (bool): Whether the booking was cancelled
- `message` (str): Success or error message

**Example Usage:**
```python
from app.agent.tools.booking_tool import cancel_booking_tool

# Cancel a booking
result = await cancel_booking_tool(
    booking_id=789,
    user_id=123
)

if result['success']:
    print("Booking cancelled successfully")
else:
    print(f"Cancellation failed: {result['message']}")
```

**Success Response Example:**
```json
{
    "success": true,
    "message": "Booking cancelled successfully"
}
```

**Error Response Examples:**
```json
{
    "success": false,
    "message": "Booking not found"
}

{
    "success": false,
    "message": "Only the customer can cancel their booking"
}

{
    "success": false,
    "message": "Booking is already cancelled"
}

{
    "success": false,
    "message": "Cannot cancel completed booking"
}
```

## Tool Registry

All booking tools are registered in the `BOOKING_TOOLS` dictionary for easy access:

```python
from app.agent.tools.booking_tool import BOOKING_TOOLS

# Access tools from registry
create_booking = BOOKING_TOOLS['create_booking']
get_details = BOOKING_TOOLS['get_booking_details']
cancel_booking = BOOKING_TOOLS['cancel_booking']

# Use the tools
result = await create_booking(
    customer_id=123,
    court_id=456,
    booking_date=date(2024, 1, 15),
    start_time=time(14, 0),
    end_time=time(15, 30)
)
```

## Integration with LangGraph Nodes

### In Booking Subgraph

The booking tool is primarily used in the `create_pending_booking` node of the booking subgraph:

```python
# Backend/apps/chatbot/app/agent/nodes/booking/create_booking.py

from app.agent.tools.booking_tool import create_booking_tool

async def create_pending_booking(state: ConversationState, tools) -> ConversationState:
    """Create a pending booking from flow_state data"""
    
    flow_state = state.get("flow_state", {})
    
    # Extract booking details from flow_state
    customer_id = int(state["user_id"])
    court_id = flow_state.get("service_id")
    booking_date = flow_state.get("date")
    start_time = flow_state.get("time")
    # Calculate end_time based on duration
    
    # Create the booking
    result = await create_booking_tool(
        customer_id=customer_id,
        court_id=court_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        notes=flow_state.get("notes")
    )
    
    if result['success']:
        # Store booking_id in flow_state
        flow_state["booking_id"] = result['data']['id']
        
        # Generate confirmation message
        state["response_content"] = (
            f"Great! Your booking has been created.\n"
            f"Booking ID: {result['data']['id']}\n"
            f"Total: ${result['data']['total_price']}\n"
            f"Status: {result['data']['status']}"
        )
        
        # Clear booking fields from flow_state
        flow_state.pop("property_id", None)
        flow_state.pop("service_id", None)
        flow_state.pop("date", None)
        flow_state.pop("time", None)
    else:
        # Handle error
        state["response_content"] = (
            f"Sorry, I couldn't create the booking: {result['message']}\n"
            f"Would you like to try a different time slot?"
        )
    
    state["flow_state"] = flow_state
    return state
```

## Error Handling

All booking tools implement comprehensive error handling:

1. **Validation Errors**: Caught from Pydantic schema validation
   - Returns `success=False` with descriptive message
   - Example: "Invalid booking data: end_time must be after start_time"

2. **Service Errors**: Caught from booking_service calls
   - Returns the error response from the service
   - Example: "Court not found or inactive"

3. **Unexpected Errors**: Caught from any other exceptions
   - Returns generic error message
   - Logs full exception details for debugging
   - Example: "An unexpected error occurred while creating the booking"

## Logging

All booking tools include structured logging:

```python
# Info level - successful operations
logger.info(
    f"Creating booking: customer_id={customer_id}, court_id={court_id}, "
    f"date={booking_date}, time={start_time}-{end_time}"
)
logger.info(
    f"Booking created successfully: booking_id={booking_id}, "
    f"total_price=${total_price}"
)

# Warning level - expected failures
logger.warning(
    f"Failed to create booking: {result.get('message')} "
    f"(customer_id={customer_id}, court_id={court_id})"
)

# Error level - unexpected failures
logger.error(f"Error creating booking: {e}", exc_info=True)
```

## Best Practices

1. **Always check success flag**: Never assume a booking operation succeeded
   ```python
   result = await create_booking_tool(...)
   if result['success']:
       # Handle success
   else:
       # Handle failure
   ```

2. **Store booking_id in flow_state**: After successful creation, store the booking_id for future reference
   ```python
   if result['success']:
       flow_state["booking_id"] = result['data']['id']
   ```

3. **Provide user-friendly error messages**: Convert technical errors to conversational responses
   ```python
   if not result['success']:
       if 'already booked' in result['message']:
           response = "That time slot is no longer available. Would you like to see other options?"
       elif 'not available' in result['message']:
           response = "The court is blocked during that time. Let me show you alternative times."
   ```

4. **Clear flow_state after completion**: Remove booking-related fields after successful booking
   ```python
   if result['success']:
       flow_state.pop("property_id", None)
       flow_state.pop("service_id", None)
       flow_state.pop("date", None)
       flow_state.pop("time", None)
   ```

5. **Handle retry scenarios**: For transient failures, allow users to retry
   ```python
   if not result['success'] and 'unexpected error' in result['message']:
       response = "I encountered an issue creating your booking. Would you like to try again?"
   ```

## Testing

The booking tool includes comprehensive unit tests in `test_booking_tool.py`:

- Success scenarios for all operations
- Error scenarios (not found, access denied, validation errors)
- Edge cases (already cancelled, completed bookings)
- Exception handling
- Tool registry validation

Run tests with:
```bash
pytest app/agent/tools/test_booking_tool.py -v
```

## Related Tools

- **pricing_tool.py**: Get pricing information before creating bookings
- **availability_tool.py**: Check available time slots before booking
- **court_tool.py**: Get court details for booking
- **property_tool.py**: Get property information for booking

## Requirements Satisfied

This tool implementation satisfies the following requirements:

- **8.1-8.6**: Booking Integration
  - Creates bookings with pending status
  - Stores booking_id in flow_state
  - Handles booking creation failures
  - Clears flow_state after completion
  - Preserves bot_memory for context

- **19.1-19.5**: Read-Only Access to Main Database
  - Accesses main database only through booking_service
  - Uses sync bridge for safe async-to-sync calls
  - No direct database modifications
  - Proper session management
