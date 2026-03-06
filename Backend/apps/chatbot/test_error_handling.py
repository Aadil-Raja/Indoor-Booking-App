"""
Simple test to verify error handling implementation.

This script tests the error handling utilities to ensure they work correctly.
"""

import sys
from pathlib import Path

# Add Backend path for imports
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.agent.state.error_handlers import (
    handle_llm_api_error,
    handle_malformed_llm_response,
    handle_flow_state_corruption,
    handle_property_fetch_failure,
    handle_court_fetch_failure,
    handle_availability_check_failure,
    handle_booking_creation_failure,
    handle_invalid_date_format,
    handle_invalid_time_slot_format,
    handle_missing_required_booking_data,
    handle_conflicting_booking_data
)

from app.agent.state.validation import (
    validate_date_format,
    validate_time_slot_format,
    validate_booking_data,
    validate_booking_data_consistency,
    parse_time_slot
)

from app.agent.state.flow_state_manager import (
    initialize_flow_state,
    validate_flow_state,
    update_flow_state,
    clear_flow_state
)


def test_llm_error_handlers():
    """Test LLM error handlers."""
    print("\n=== Testing LLM Error Handlers ===")
    
    # Test LLM API error
    context = {"chat_id": "test-123", "current_node": "greeting"}
    error = Exception("Connection timeout")
    next_node, message, updates = handle_llm_api_error(error, context)
    
    assert next_node == "greeting", f"Expected 'greeting', got '{next_node}'"
    assert len(message) > 0, "Message should not be empty"
    assert updates == {}, "Updates should be empty on error"
    print("✓ LLM API error handler works")
    
    # Test malformed response
    response = "not a dict"
    next_node, message, updates = handle_malformed_llm_response(response, context)
    
    assert next_node == "greeting", f"Expected 'greeting', got '{next_node}'"
    assert len(message) > 0, "Message should not be empty"
    print("✓ Malformed response handler works")


def test_state_error_handlers():
    """Test state management error handlers."""
    print("\n=== Testing State Error Handlers ===")
    
    context = {"chat_id": "test-123"}
    
    # Test flow state corruption
    corrupted_state = "not a dict"
    fixed_state = handle_flow_state_corruption(corrupted_state, context)
    
    assert isinstance(fixed_state, dict), "Fixed state should be a dict"
    assert validate_flow_state(fixed_state), "Fixed state should be valid"
    print("✓ Flow state corruption handler works")
    
    # Test valid flow state
    valid_state = initialize_flow_state()
    result = handle_flow_state_corruption(valid_state, context)
    
    assert result == valid_state, "Valid state should be returned unchanged"
    print("✓ Valid flow state passes through")


def test_tool_error_handlers():
    """Test tool invocation error handlers."""
    print("\n=== Testing Tool Error Handlers ===")
    
    context = {"chat_id": "test-123", "owner_profile_id": "456"}
    error = Exception("Database connection failed")
    
    # Test property fetch failure
    message, metadata = handle_property_fetch_failure(error, context)
    
    assert len(message) > 0, "Message should not be empty"
    assert "error_type" in metadata, "Metadata should contain error_type"
    assert metadata["recoverable"] == True, "Error should be recoverable"
    print("✓ Property fetch failure handler works")
    
    # Test court fetch failure
    context["property_id"] = 1
    message, metadata = handle_court_fetch_failure(error, context)
    
    assert len(message) > 0, "Message should not be empty"
    assert metadata["error_type"] == "court_fetch_failure"
    print("✓ Court fetch failure handler works")
    
    # Test availability check failure
    context["court_id"] = 10
    context["date"] = "2026-03-10"
    message, metadata = handle_availability_check_failure(error, context)
    
    assert len(message) > 0, "Message should not be empty"
    assert metadata["error_type"] == "availability_check_failure"
    print("✓ Availability check failure handler works")
    
    # Test booking creation failure
    booking_data = {"court_id": 10, "date": "2026-03-10"}
    message, next_node, metadata = handle_booking_creation_failure(
        error,
        context,
        booking_data
    )
    
    assert len(message) > 0, "Message should not be empty"
    assert next_node == "select_time", "Should route to time selection"
    assert metadata["recoverable"] == True, "Error should be recoverable"
    print("✓ Booking creation failure handler works")


def test_validation_error_handlers():
    """Test validation error handlers."""
    print("\n=== Testing Validation Error Handlers ===")
    
    context = {"chat_id": "test-123"}
    
    # Test invalid date format
    message, metadata = handle_invalid_date_format("not-a-date", context)
    
    assert len(message) > 0, "Message should not be empty"
    assert "error_type" in metadata, "Metadata should contain error_type"
    print("✓ Invalid date format handler works")
    
    # Test invalid time slot format
    message, metadata = handle_invalid_time_slot_format("not-a-time", context)
    
    assert len(message) > 0, "Message should not be empty"
    assert metadata["error_type"] == "invalid_time_slot_format"
    print("✓ Invalid time slot format handler works")
    
    # Test missing required data
    missing_fields = ["property_id", "court_id"]
    message, next_node, metadata = handle_missing_required_booking_data(
        missing_fields,
        context
    )
    
    assert len(message) > 0, "Message should not be empty"
    assert next_node == "select_property", "Should route to property selection"
    assert metadata["missing_fields"] == missing_fields
    print("✓ Missing required data handler works")
    
    # Test conflicting data
    conflicts = {"date": "Date is in the past"}
    message, next_node, metadata = handle_conflicting_booking_data(conflicts, context)
    
    assert len(message) > 0, "Message should not be empty"
    assert next_node == "select_property", "Should route to property selection"
    print("✓ Conflicting data handler works")


def test_validation_functions():
    """Test validation utility functions."""
    print("\n=== Testing Validation Functions ===")
    
    context = {"chat_id": "test-123"}
    
    # Test valid date
    is_valid, date_obj, error = validate_date_format("2026-03-10", context)
    
    assert is_valid == True, "Valid date should pass"
    assert date_obj is not None, "Date object should be returned"
    assert error is None, "Error should be None for valid date"
    print("✓ Valid date validation works")
    
    # Test invalid date
    is_valid, date_obj, error = validate_date_format("not-a-date", context)
    
    assert is_valid == False, "Invalid date should fail"
    assert date_obj is None, "Date object should be None"
    assert error is not None, "Error message should be returned"
    print("✓ Invalid date validation works")
    
    # Test valid time slot
    is_valid, times, error = validate_time_slot_format("10:00-11:00", context)
    
    assert is_valid == True, "Valid time slot should pass"
    assert times is not None, "Times should be returned"
    assert error is None, "Error should be None for valid time slot"
    print("✓ Valid time slot validation works")
    
    # Test invalid time slot
    is_valid, times, error = validate_time_slot_format("not-a-time", context)
    
    assert is_valid == False, "Invalid time slot should fail"
    assert times is None, "Times should be None"
    assert error is not None, "Error message should be returned"
    print("✓ Invalid time slot validation works")
    
    # Test booking data validation - missing fields
    flow_state = {"property_id": 1}
    is_valid, missing, error = validate_booking_data(flow_state, context)
    
    assert is_valid == False, "Incomplete booking data should fail"
    assert len(missing) > 0, "Missing fields should be returned"
    assert error is not None, "Error message should be returned"
    print("✓ Missing booking data validation works")
    
    # Test booking data validation - complete
    flow_state = {
        "property_id": 1,
        "court_id": 10,
        "date": "2026-03-10",
        "time_slot": "10:00-11:00"
    }
    is_valid, missing, error = validate_booking_data(flow_state, context)
    
    assert is_valid == True, "Complete booking data should pass"
    assert missing is None, "Missing fields should be None"
    assert error is None, "Error should be None"
    print("✓ Complete booking data validation works")
    
    # Test time slot parsing
    start_time, end_time = parse_time_slot("10:00-11:00")
    
    assert start_time is not None, "Start time should be parsed"
    assert end_time is not None, "End time should be parsed"
    assert start_time.hour == 10, "Start hour should be 10"
    assert end_time.hour == 11, "End hour should be 11"
    print("✓ Time slot parsing works")


def test_flow_state_manager():
    """Test flow state manager functions."""
    print("\n=== Testing Flow State Manager ===")
    
    # Test initialization
    flow_state = initialize_flow_state()
    
    assert isinstance(flow_state, dict), "Flow state should be a dict"
    assert "property_id" in flow_state, "Should have property_id field"
    assert "context" in flow_state, "Should have context field"
    print("✓ Flow state initialization works")
    
    # Test validation
    is_valid = validate_flow_state(flow_state)
    
    assert is_valid == True, "Initialized flow state should be valid"
    print("✓ Flow state validation works")
    
    # Test update
    updates = {"property_id": 1, "property_name": "Test Property"}
    updated_state = update_flow_state(flow_state, updates)
    
    assert updated_state["property_id"] == 1, "Property ID should be updated"
    assert updated_state["property_name"] == "Test Property", "Property name should be updated"
    print("✓ Flow state update works")
    
    # Test clear
    cleared_state = clear_flow_state()
    
    assert isinstance(cleared_state, dict), "Cleared state should be a dict"
    assert cleared_state["property_id"] is None, "Property ID should be None"
    print("✓ Flow state clear works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Error Handling Implementation")
    print("=" * 60)
    
    try:
        test_llm_error_handlers()
        test_state_error_handlers()
        test_tool_error_handlers()
        test_validation_error_handlers()
        test_validation_functions()
        test_flow_state_manager()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
