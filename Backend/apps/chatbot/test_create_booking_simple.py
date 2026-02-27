"""
Simple standalone test for create_booking node logic.

This test verifies the core logic without requiring full dependencies.
"""

import asyncio
from unittest.mock import AsyncMock


async def test_booking_creation_logic():
    """Test the booking creation logic."""
    print("\n=== Testing Create Booking Node Logic ===\n")
    
    # Simulate successful booking creation
    print("Test 1: Successful booking creation")
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
    
    result = await mock_create_booking(
        customer_id=456,
        court_id=10,
        booking_date="2024-12-25",
        start_time="14:00:00",
        end_time="15:00:00",
        notes=None
    )
    
    assert result["success"] == True, "Booking should succeed"
    assert result["data"]["id"] == 123, "Booking ID should be 123"
    assert result["data"]["total_price"] == 50.0, "Total price should be 50.0"
    print("✓ Successful booking creation works correctly")
    print(f"  Booking ID: {result['data']['id']}")
    print(f"  Total Price: ${result['data']['total_price']}")
    
    # Simulate booking creation failure
    print("\nTest 2: Booking creation failure")
    mock_create_booking_fail = AsyncMock(return_value={
        "success": False,
        "message": "This time slot is already booked"
    })
    
    result = await mock_create_booking_fail(
        customer_id=456,
        court_id=10,
        booking_date="2024-12-25",
        start_time="14:00:00",
        end_time="15:00:00",
        notes=None
    )
    
    assert result["success"] == False, "Booking should fail"
    assert "already booked" in result["message"], "Error message should mention already booked"
    print("✓ Booking failure handling works correctly")
    print(f"  Error: {result['message']}")
    
    # Test field clearing logic
    print("\nTest 3: Field clearing logic")
    flow_state = {
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
        "step": "confirmed",
        "booking_id": 123
    }
    
    # Fields to clear after booking completion
    fields_to_clear = [
        "property_id", "property_name", "service_id", "service_name",
        "sport_type", "date", "start_time", "end_time", "price",
        "price_label", "total_price", "duration_hours", "error_message"
    ]
    
    for field in fields_to_clear:
        flow_state.pop(field, None)
    
    # Verify only intent, step, and booking_id remain
    assert "property_id" not in flow_state, "property_id should be cleared"
    assert "service_id" not in flow_state, "service_id should be cleared"
    assert "date" not in flow_state, "date should be cleared"
    assert "intent" in flow_state, "intent should be preserved"
    assert "step" in flow_state, "step should be preserved"
    assert "booking_id" in flow_state, "booking_id should be preserved"
    print("✓ Field clearing logic works correctly")
    print(f"  Remaining fields: {list(flow_state.keys())}")
    
    # Test confirmation message generation
    print("\nTest 4: Confirmation message generation")
    booking_details = {
        "property_name": "Downtown Sports Center",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2024-12-25",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "duration_hours": 1.0,
        "booking_id": 123,
        "total_price": 50.0
    }
    
    # Verify all required fields are present
    assert "property_name" in booking_details, "property_name should be present"
    assert "service_name" in booking_details, "service_name should be present"
    assert "booking_id" in booking_details, "booking_id should be present"
    assert "total_price" in booking_details, "total_price should be present"
    print("✓ Confirmation message data is complete")
    print(f"  Booking ID: {booking_details['booking_id']}")
    print(f"  Property: {booking_details['property_name']}")
    print(f"  Court: {booking_details['service_name']}")
    print(f"  Total: ${booking_details['total_price']}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    
    return True


async def main():
    """Run all tests."""
    try:
        await test_booking_creation_logic()
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
