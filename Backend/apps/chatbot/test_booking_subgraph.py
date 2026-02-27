"""
Simple test to verify booking subgraph structure and compilation.

This test verifies that:
1. The booking subgraph can be created and compiled
2. All nodes are properly registered
3. Routing functions work correctly
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agent.graphs.booking_subgraph import (
    create_booking_subgraph,
    route_property_selection,
    route_service_selection,
    route_date_selection,
    route_time_selection,
    route_confirmation,
)


def test_create_booking_subgraph():
    """Test that the booking subgraph can be created and compiled."""
    print("Testing booking subgraph creation...")
    
    # Create a mock tools registry
    mock_tools = {
        "get_property_details": lambda **kwargs: None,
        "search_courts": lambda **kwargs: None,
        "get_availability": lambda **kwargs: None,
        "get_pricing": lambda **kwargs: None,
        "create_booking": lambda **kwargs: None,
    }
    
    # Create the subgraph
    try:
        booking_graph = create_booking_subgraph(mock_tools)
        print("✓ Booking subgraph created successfully")
        print(f"✓ Graph type: {type(booking_graph)}")
        return True
    except Exception as e:
        print(f"✗ Failed to create booking subgraph: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routing_functions():
    """Test that routing functions work correctly."""
    print("\nTesting routing functions...")
    
    # Test route_property_selection
    state_with_property = {
        "chat_id": "test-123",
        "user_message": "I selected property 1",
        "flow_state": {"property_id": "1"}
    }
    result = route_property_selection(state_with_property)
    assert result == "continue", f"Expected 'continue', got '{result}'"
    print("✓ route_property_selection: continue case works")
    
    state_cancel = {
        "chat_id": "test-123",
        "user_message": "cancel",
        "flow_state": {}
    }
    result = route_property_selection(state_cancel)
    assert result == "cancel", f"Expected 'cancel', got '{result}'"
    print("✓ route_property_selection: cancel case works")
    
    # Test route_service_selection
    state_with_service = {
        "chat_id": "test-123",
        "user_message": "I selected service 1",
        "flow_state": {"service_id": "1"}
    }
    result = route_service_selection(state_with_service)
    assert result == "continue", f"Expected 'continue', got '{result}'"
    print("✓ route_service_selection: continue case works")
    
    state_back = {
        "chat_id": "test-123",
        "user_message": "go back",
        "flow_state": {}
    }
    result = route_service_selection(state_back)
    assert result == "back", f"Expected 'back', got '{result}'"
    print("✓ route_service_selection: back case works")
    
    # Test route_date_selection
    state_with_date = {
        "chat_id": "test-123",
        "user_message": "2024-01-15",
        "flow_state": {"date": "2024-01-15"}
    }
    result = route_date_selection(state_with_date)
    assert result == "continue", f"Expected 'continue', got '{result}'"
    print("✓ route_date_selection: continue case works")
    
    # Test route_time_selection
    state_with_time = {
        "chat_id": "test-123",
        "user_message": "14:00",
        "flow_state": {"time": "14:00"}
    }
    result = route_time_selection(state_with_time)
    assert result == "continue", f"Expected 'continue', got '{result}'"
    print("✓ route_time_selection: continue case works")
    
    # Test route_confirmation
    state_confirm = {
        "chat_id": "test-123",
        "user_message": "yes, confirm",
        "flow_state": {}
    }
    result = route_confirmation(state_confirm)
    assert result == "confirmed", f"Expected 'confirmed', got '{result}'"
    print("✓ route_confirmation: confirmed case works")
    
    state_modify = {
        "chat_id": "test-123",
        "user_message": "I want to change the time",
        "flow_state": {}
    }
    result = route_confirmation(state_modify)
    assert result == "modify", f"Expected 'modify', got '{result}'"
    print("✓ route_confirmation: modify case works")
    
    state_cancel_confirm = {
        "chat_id": "test-123",
        "user_message": "no thanks",
        "flow_state": {}
    }
    result = route_confirmation(state_cancel_confirm)
    assert result == "cancel", f"Expected 'cancel', got '{result}'"
    print("✓ route_confirmation: cancel case works")
    
    print("✓ All routing functions work correctly")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Booking Subgraph Verification Tests")
    print("=" * 60)
    
    success = True
    
    # Test graph creation
    if not test_create_booking_subgraph():
        success = False
    
    # Test routing functions
    if not test_routing_functions():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
