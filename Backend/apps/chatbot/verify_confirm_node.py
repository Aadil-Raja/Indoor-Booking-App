"""
Manual verification script for confirm booking node.

This script verifies that the confirm booking node implementation works correctly
by testing various scenarios without requiring pytest.
"""

import asyncio
import sys
from pathlib import Path

# Add Backend directory to Python path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from apps.chatbot.app.agent.nodes.booking.confirm import confirm_booking


async def test_present_booking_summary():
    """Test that booking summary is presented correctly."""
    print("\n=== Test: Present Booking Summary ===")
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "14:00",
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
            "step": "time_selected"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify response contains booking summary
    assert "Booking Summary" in result["response_content"], "Missing 'Booking Summary'"
    assert "Downtown Sports Center" in result["response_content"], "Missing property name"
    assert "Tennis Court A" in result["response_content"], "Missing service name"
    assert "tennis" in result["response_content"], "Missing sport type"
    assert "$50.00/hour" in result["response_content"], "Missing price"
    assert "Would you like to confirm this booking?" in result["response_content"], "Missing confirmation prompt"
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "confirm", f"Expected step 'confirm', got '{result['flow_state']['step']}'"
    assert "total_price" in result["flow_state"], "Missing total_price in flow_state"
    assert "duration_hours" in result["flow_state"], "Missing duration_hours in flow_state"
    
    print("✓ Booking summary presented correctly")
    print(f"  Response preview: {result['response_content'][:100]}...")
    return True


async def test_confirm_booking_yes():
    """Test that user confirmation is handled correctly."""
    print("\n=== Test: Confirm Booking (Yes) ===")
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "yes, confirm it",
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
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify confirmation response
    assert "creating your booking" in result["response_content"].lower(), "Missing confirmation message"
    
    # Verify flow state updated to confirmed
    assert result["flow_state"]["step"] == "confirmed", f"Expected step 'confirmed', got '{result['flow_state']['step']}'"
    
    print("✓ Confirmation handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def test_cancel_booking():
    """Test that booking cancellation is handled correctly."""
    print("\n=== Test: Cancel Booking ===")
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "no, cancel",
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
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify cancellation response
    assert "cancelled" in result["response_content"].lower(), "Missing cancellation message"
    
    # Verify flow state cleared
    assert result["flow_state"]["step"] == "cancelled", f"Expected step 'cancelled', got '{result['flow_state']['step']}'"
    assert "property_id" not in result["flow_state"], "property_id should be cleared"
    assert "service_id" not in result["flow_state"], "service_id should be cleared"
    assert "date" not in result["flow_state"], "date should be cleared"
    
    print("✓ Cancellation handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def test_modify_date():
    """Test that date modification request is handled correctly."""
    print("\n=== Test: Modify Date ===")
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "change the date",
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
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify modification response
    assert "different date" in result["response_content"].lower(), "Missing date modification message"
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "service_selected", f"Expected step 'service_selected', got '{result['flow_state']['step']}'"
    assert "date" not in result["flow_state"], "date should be cleared"
    assert "start_time" not in result["flow_state"], "start_time should be cleared"
    assert "end_time" not in result["flow_state"], "end_time should be cleared"
    # Property and service should still be present
    assert result["flow_state"]["property_id"] == "1", "property_id should be preserved"
    assert result["flow_state"]["service_id"] == "10", "service_id should be preserved"
    
    print("✓ Date modification handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def test_modify_time():
    """Test that time modification request is handled correctly."""
    print("\n=== Test: Modify Time ===")
    
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "change the time",
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
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify modification response
    assert "different time" in result["response_content"].lower(), "Missing time modification message"
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "date_selected", f"Expected step 'date_selected', got '{result['flow_state']['step']}'"
    assert "start_time" not in result["flow_state"], "start_time should be cleared"
    assert "end_time" not in result["flow_state"], "end_time should be cleared"
    # Property, service, and date should still be present
    assert result["flow_state"]["property_id"] == "1", "property_id should be preserved"
    assert result["flow_state"]["service_id"] == "10", "service_id should be preserved"
    assert result["flow_state"]["date"] == "2024-12-25", "date should be preserved"
    
    print("✓ Time modification handled correctly")
    print(f"  Response: {result['response_content']}")
    return True


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Confirm Booking Node Verification")
    print("=" * 60)
    
    tests = [
        test_present_booking_summary,
        test_confirm_booking_yes,
        test_cancel_booking,
        test_modify_date,
        test_modify_time,
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
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
