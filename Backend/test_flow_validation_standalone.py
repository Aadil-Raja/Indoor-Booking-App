"""
Standalone test for flow validation utilities.

This test file can be run directly without triggering circular imports.
"""

import sys
import os

# Add the chatbot app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'chatbot'))

# Import only the flow_validation module directly
from app.agent.nodes.booking.flow_validation import (
    get_next_incomplete_step,
    validate_booking_flow_sequence,
    should_skip_to_next_step,
    validate_required_fields_for_step,
    get_booking_progress_summary
)


def test_get_next_incomplete_step():
    """Test get_next_incomplete_step function."""
    print("Testing get_next_incomplete_step...")
    
    # Test 1: Empty flow_state
    flow_state = {}
    result = get_next_incomplete_step(flow_state)
    assert result == "select_property", f"Expected 'select_property', got '{result}'"
    print("✓ Empty flow_state returns select_property")
    
    # Test 2: Property selected
    flow_state = {"property_id": 1, "property_name": "Sports Center"}
    result = get_next_incomplete_step(flow_state)
    assert result == "select_court", f"Expected 'select_court', got '{result}'"
    print("✓ Property selected returns select_court")
    
    # Test 3: Property and court selected
    flow_state = {
        "property_id": 1,
        "property_name": "Sports Center",
        "court_id": 10,
        "court_name": "Tennis Court A"
    }
    result = get_next_incomplete_step(flow_state)
    assert result == "select_date", f"Expected 'select_date', got '{result}'"
    print("✓ Property and court selected returns select_date")
    
    # Test 4: Property, court, and date selected
    flow_state = {
        "property_id": 1,
        "property_name": "Sports Center",
        "court_id": 10,
        "court_name": "Tennis Court A",
        "date": "2024-12-25"
    }
    result = get_next_incomplete_step(flow_state)
    assert result == "select_time", f"Expected 'select_time', got '{result}'"
    print("✓ Property, court, and date selected returns select_time")
    
    # Test 5: All data present
    flow_state = {
        "property_id": 1,
        "property_name": "Sports Center",
        "court_id": 10,
        "court_name": "Tennis Court A",
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    }
    result = get_next_incomplete_step(flow_state)
    assert result == "confirm_booking", f"Expected 'confirm_booking', got '{result}'"
    print("✓ All data present returns confirm_booking")


def test_should_skip_to_next_step():
    """Test should_skip_to_next_step function."""
    print("\nTesting should_skip_to_next_step...")
    
    # Test 1: Property already selected
    flow_state = {"property_id": 1, "property_name": "Sports Center"}
    should_skip, next_node = should_skip_to_next_step("select_property", flow_state)
    assert should_skip is True, "Expected should_skip to be True"
    assert next_node == "select_court", f"Expected 'select_court', got '{next_node}'"
    print("✓ select_property skips when property_id exists")
    
    # Test 2: Property not selected
    flow_state = {}
    should_skip, next_node = should_skip_to_next_step("select_property", flow_state)
    assert should_skip is False, "Expected should_skip to be False"
    assert next_node is None, f"Expected None, got '{next_node}'"
    print("✓ select_property doesn't skip when property_id is missing")
    
    # Test 3: Court already selected
    flow_state = {"property_id": 1, "court_id": 10, "court_name": "Tennis Court A"}
    should_skip, next_node = should_skip_to_next_step("select_court", flow_state)
    assert should_skip is True, "Expected should_skip to be True"
    assert next_node == "select_date", f"Expected 'select_date', got '{next_node}'"
    print("✓ select_court skips when court_id exists")
    
    # Test 4: Date already selected
    flow_state = {"property_id": 1, "court_id": 10, "date": "2024-12-25"}
    should_skip, next_node = should_skip_to_next_step("select_date", flow_state)
    assert should_skip is True, "Expected should_skip to be True"
    assert next_node == "select_time", f"Expected 'select_time', got '{next_node}'"
    print("✓ select_date skips when date exists")
    
    # Test 5: Time already selected
    flow_state = {
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    }
    should_skip, next_node = should_skip_to_next_step("select_time", flow_state)
    assert should_skip is True, "Expected should_skip to be True"
    assert next_node == "confirm_booking", f"Expected 'confirm_booking', got '{next_node}'"
    print("✓ select_time skips when time_slot exists")


def test_validate_required_fields_for_step():
    """Test validate_required_fields_for_step function."""
    print("\nTesting validate_required_fields_for_step...")
    
    # Test 1: select_property has no prerequisites
    flow_state = {}
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "select_property",
        flow_state
    )
    assert is_valid is True, "Expected is_valid to be True"
    assert missing_field is None, f"Expected None, got '{missing_field}'"
    print("✓ select_property has no prerequisites")
    
    # Test 2: select_court requires property_id
    flow_state = {}
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "select_court",
        flow_state
    )
    assert is_valid is False, "Expected is_valid to be False"
    assert missing_field == "property_id", f"Expected 'property_id', got '{missing_field}'"
    assert redirect_node == "select_property", f"Expected 'select_property', got '{redirect_node}'"
    print("✓ select_court requires property_id")
    
    # Test 3: select_date requires property_id and court_id
    flow_state = {"property_id": 1}
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "select_date",
        flow_state
    )
    assert is_valid is False, "Expected is_valid to be False"
    assert missing_field == "court_id", f"Expected 'court_id', got '{missing_field}'"
    assert redirect_node == "select_court", f"Expected 'select_court', got '{redirect_node}'"
    print("✓ select_date requires property_id and court_id")
    
    # Test 4: select_time requires property_id, court_id, and date
    flow_state = {"property_id": 1, "court_id": 10}
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "select_time",
        flow_state
    )
    assert is_valid is False, "Expected is_valid to be False"
    assert missing_field == "date", f"Expected 'date', got '{missing_field}'"
    assert redirect_node == "select_date", f"Expected 'select_date', got '{redirect_node}'"
    print("✓ select_time requires property_id, court_id, and date")
    
    # Test 5: confirm_booking requires all fields
    flow_state = {"property_id": 1, "court_id": 10, "date": "2024-12-25"}
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "confirm_booking",
        flow_state
    )
    assert is_valid is False, "Expected is_valid to be False"
    assert missing_field == "time_slot", f"Expected 'time_slot', got '{missing_field}'"
    assert redirect_node == "select_time", f"Expected 'select_time', got '{redirect_node}'"
    print("✓ confirm_booking requires all fields")
    
    # Test 6: confirm_booking valid with all fields
    flow_state = {
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    }
    is_valid, missing_field, redirect_node = validate_required_fields_for_step(
        "confirm_booking",
        flow_state
    )
    assert is_valid is True, "Expected is_valid to be True"
    assert missing_field is None, f"Expected None, got '{missing_field}'"
    print("✓ confirm_booking valid with all fields")


def test_get_booking_progress_summary():
    """Test get_booking_progress_summary function."""
    print("\nTesting get_booking_progress_summary...")
    
    # Test 1: Empty flow_state
    flow_state = {}
    summary = get_booking_progress_summary(flow_state)
    assert summary["completion_percentage"] == 0, f"Expected 0%, got {summary['completion_percentage']}%"
    assert summary["completed_steps"] == 0, f"Expected 0 steps, got {summary['completed_steps']}"
    assert summary["next_step"] == "select_property", f"Expected 'select_property', got '{summary['next_step']}'"
    print("✓ Empty flow_state shows 0% progress")
    
    # Test 2: Property selected
    flow_state = {"property_id": 1, "property_name": "Sports Center"}
    summary = get_booking_progress_summary(flow_state)
    assert summary["completion_percentage"] == 25, f"Expected 25%, got {summary['completion_percentage']}%"
    assert summary["completed_steps"] == 1, f"Expected 1 step, got {summary['completed_steps']}"
    assert summary["next_step"] == "select_court", f"Expected 'select_court', got '{summary['next_step']}'"
    print("✓ Property selected shows 25% progress")
    
    # Test 3: Property and court selected
    flow_state = {
        "property_id": 1,
        "property_name": "Sports Center",
        "court_id": 10,
        "court_name": "Tennis Court A"
    }
    summary = get_booking_progress_summary(flow_state)
    assert summary["completion_percentage"] == 50, f"Expected 50%, got {summary['completion_percentage']}%"
    assert summary["completed_steps"] == 2, f"Expected 2 steps, got {summary['completed_steps']}"
    assert summary["next_step"] == "select_date", f"Expected 'select_date', got '{summary['next_step']}'"
    print("✓ Property and court selected shows 50% progress")
    
    # Test 4: All data present
    flow_state = {
        "property_id": 1,
        "property_name": "Sports Center",
        "court_id": 10,
        "court_name": "Tennis Court A",
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    }
    summary = get_booking_progress_summary(flow_state)
    assert summary["completion_percentage"] == 100, f"Expected 100%, got {summary['completion_percentage']}%"
    assert summary["completed_steps"] == 4, f"Expected 4 steps, got {summary['completed_steps']}"
    assert summary["next_step"] == "confirm_booking", f"Expected 'confirm_booking', got '{summary['next_step']}'"
    print("✓ All data present shows 100% progress")


def test_validate_booking_flow_sequence():
    """Test validate_booking_flow_sequence function."""
    print("\nTesting validate_booking_flow_sequence...")
    
    # Test 1: select_property valid when no data
    is_valid, redirect = validate_booking_flow_sequence("select_property", {})
    assert is_valid is True, "Expected is_valid to be True"
    assert redirect is None, f"Expected None, got '{redirect}'"
    print("✓ select_property valid when no data")
    
    # Test 2: select_property invalid when property exists
    flow_state = {"property_id": 1, "property_name": "Sports Center"}
    is_valid, redirect = validate_booking_flow_sequence("select_property", flow_state)
    assert is_valid is False, "Expected is_valid to be False"
    assert redirect == "select_court", f"Expected 'select_court', got '{redirect}'"
    print("✓ select_property invalid when property exists")
    
    # Test 3: select_court invalid when no property
    is_valid, redirect = validate_booking_flow_sequence("select_court", {})
    assert is_valid is False, "Expected is_valid to be False"
    assert redirect == "select_property", f"Expected 'select_property', got '{redirect}'"
    print("✓ select_court invalid when no property")
    
    # Test 4: select_court valid when property exists
    flow_state = {"property_id": 1, "property_name": "Sports Center"}
    is_valid, redirect = validate_booking_flow_sequence("select_court", flow_state)
    assert is_valid is True, "Expected is_valid to be True"
    assert redirect is None, f"Expected None, got '{redirect}'"
    print("✓ select_court valid when property exists")


if __name__ == "__main__":
    print("=" * 70)
    print("Running Flow Validation Tests")
    print("=" * 70)
    
    try:
        test_get_next_incomplete_step()
        test_should_skip_to_next_step()
        test_validate_required_fields_for_step()
        test_get_booking_progress_summary()
        test_validate_booking_flow_sequence()
        
        print("\n" + "=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
