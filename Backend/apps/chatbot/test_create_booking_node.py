"""
Simple test for create_booking node.

This test verifies that the create_booking node correctly:
- Creates a booking with pending status
- Stores booking_id in flow_state on success
- Handles booking creation errors
- Clears booking fields from flow_state on completion
- Generates confirmation message with booking details
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Add chatbot app directory to Python path
chatbot_path = Path(__file__).parent
if str(chatbot_path) not in sys.path:
    sys.path.insert(0, str(chatbot_path))

from app.agent.nodes.booking.create_booking import create_pending_booking


async def test_successful_booking_creation():
    """Test that booking is created successfully and confirmation is generated."""
    print("\n=== Test: Successful Booking Creation ===")
    
    # Mock create_booking tool
    mock_create_booking = AsyncMock(return_value={
        "success": True,
        "message": "Booking created successfully",
        "data": {
            "id": 123,
            "booking_date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "total_price": 50.0,
            "status": "pending",
            "payment_status": "pending"
        }
    })
    
    tools = {
        "create_booking": mock_create_booking
    }
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "456",  # Will be converted to int
        "owner_id": "test-owner-123",
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
    
    result = await create_pending_booking(state, tools)
    
    # Verify booking tool was called
    assert mock_create_booking.called, "create_booking tool should be called"
    
    # Verify response contains confirmation
    assert "Booking Confirmed" in result["response_content"], "Missing confirmation message"
    assert "123" in result["response_content"], "Missing booking ID"
    assert "Downtown Sports Center" in result["response_content"], "Missing property name"
    assert "Tennis Court A" in result["response_content"], "Missing service name"
    assert "$50.00" in result["response_content"], "Missing price"
    
    # Verify booking_id stored in flow_state
    assert result["flow_state"].get("booking_id") == 123, "booking_id should be stored"
    
    # Verify flow state step updated
    assert result["flow_state"]["step"] == "booking_created", f"Expected step 'booking_created', got '{result['flow_state']['step']}'"
    
    # Verify booking fields cleared
    assert "property_id" not in result["flow_state"], "property_id should be cleared"
    assert "service_id" not in result["flow_state"], "service_id should be cleared"
    assert "date" not in result["flow_state"], "date should be cleared"
    assert "start_time" not in result["flow_state"], "start_time should be cleared"
    assert "end_time" not in result["flow_state"], "end_time should be cleared"
    assert "price" not in result["flow_state"], "price should be cleared"
    
    print("✓ Booking created successfully")
    print(f"  Booking ID: 123")
    print(f"  Response preview: {result['response_content'][:100]}...")
    return True


async def test_booking_creation_failure():
    """Test that booking creation failure is handled gracefully."""
    print("\n=== Test: Booking Creation Failure ===")
    
    # Mock create_booking tool with failure
    mock_create_booking = AsyncMock(return_value={
        "success": False,
        "message": "This time slot is already booked"
    })
    
    tools = {
        "create_booking": mock_create_booking
    }
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "456",
        "owner_id": "test-owner-123",
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
    
    result = await create_pending_booking(state, tools)
    
    # Verify booking tool was called
    assert mock_create_booking.called, "create_booking tool should be called"
    
    # Verify response contains error message
    assert "Booking Failed" in result["response_content"], "Missing error message"
    assert "already booked" in result["response_content"], "Missing specific error"
    
    # Verify flow state step updated to failed
    assert result["flow_state"]["step"] == "booking_failed", f"Expected step 'booking_failed', got '{result['flow_state']['step']}'"
    
    # Verify booking details retained for retry
    assert result["flow_state"]["property_id"] == "1", "property_id should be retained"
    assert result["flow_state"]["service_id"] == "10", "service_id should be retained"
    assert result["flow_state"]["date"] == "2024-12-25", "date should be retained"
    assert result["flow_state"]["start_time"] == "14:00:00", "start_time should be retained"
    
    # Verify error message stored
    assert "error_message" in result["flow_state"], "error_message should be stored"
    
    print("✓ Booking failure handled correctly")
    print(f"  Error: {result['flow_state']['error_message']}")
    print(f"  Response preview: {result['response_content'][:100]}...")
    return True


async def test_missing_required_fields():
    """Test that missing required fields are handled gracefully."""
    print("\n=== Test: Missing Required Fields ===")
    
    tools = {
        "create_booking": AsyncMock()
    }
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "456",
        "owner_id": "test-owner-123",
        "user_message": "yes, confirm",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            # Missing service_id, date, start_time, end_time
            "step": "confirmed"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await create_pending_booking(state, tools)
    
    # Verify error response
    assert "missing" in result["response_content"].lower(), "Missing error message"
    
    # Verify flow state reset
    assert result["flow_state"]["step"] == "select_property", f"Expected step 'select_property', got '{result['flow_state']['step']}'"
    
    print("✓ Missing fields handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def test_invalid_date_format():
    """Test that invalid date format is handled gracefully."""
    print("\n=== Test: Invalid Date Format ===")
    
    tools = {
        "create_booking": AsyncMock()
    }
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "456",
        "owner_id": "test-owner-123",
        "user_message": "yes, confirm",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "service_id": "10",
            "date": "invalid-date",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "step": "confirmed"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await create_pending_booking(state, tools)
    
    # Verify error response
    assert "error" in result["response_content"].lower(), "Missing error message"
    
    # Verify flow state reset to date selection
    assert result["flow_state"]["step"] == "service_selected", f"Expected step 'service_selected', got '{result['flow_state']['step']}'"
    
    print("✓ Invalid date format handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Create Booking Node Test")
    print("=" * 60)
    
    tests = [
        test_successful_booking_creation,
        test_booking_creation_failure,
        test_missing_required_fields,
        test_invalid_date_format,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
