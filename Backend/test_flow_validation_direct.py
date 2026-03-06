"""
Direct test for flow validation utilities without triggering circular imports.
"""

import sys
import os
import importlib.util

# Load the module directly without going through __init__.py
module_path = os.path.join(
    os.path.dirname(__file__),
    'apps', 'chatbot', 'app', 'agent', 'nodes', 'booking', 'flow_validation.py'
)

spec = importlib.util.spec_from_file_location("flow_validation", module_path)
flow_validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow_validation)

# Extract functions
get_next_incomplete_step = flow_validation.get_next_incomplete_step
should_skip_to_next_step = flow_validation.should_skip_to_next_step
validate_required_fields_for_step = flow_validation.validate_required_fields_for_step
get_booking_progress_summary = flow_validation.get_booking_progress_summary
validate_booking_flow_sequence = flow_validation.validate_booking_flow_sequence


def run_tests():
    """Run all tests."""
    print("=" * 70)
    print("Testing Flow Validation Utilities")
    print("=" * 70)
    
    # Test 1: get_next_incomplete_step
    print("\n1. Testing get_next_incomplete_step...")
    assert get_next_incomplete_step({}) == "select_property"
    assert get_next_incomplete_step({"property_id": 1}) == "select_court"
    assert get_next_incomplete_step({"property_id": 1, "court_id": 10}) == "select_date"
    assert get_next_incomplete_step({"property_id": 1, "court_id": 10, "date": "2024-12-25"}) == "select_time"
    assert get_next_incomplete_step({
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    }) == "confirm_booking"
    print("   ✓ All tests passed")
    
    # Test 2: should_skip_to_next_step
    print("\n2. Testing should_skip_to_next_step...")
    should_skip, next_node = should_skip_to_next_step("select_property", {"property_id": 1})
    assert should_skip is True and next_node == "select_court"
    
    should_skip, next_node = should_skip_to_next_step("select_property", {})
    assert should_skip is False and next_node is None
    
    should_skip, next_node = should_skip_to_next_step("select_court", {"property_id": 1, "court_id": 10})
    assert should_skip is True and next_node == "select_date"
    
    should_skip, next_node = should_skip_to_next_step("select_date", {"property_id": 1, "court_id": 10, "date": "2024-12-25"})
    assert should_skip is True and next_node == "select_time"
    
    should_skip, next_node = should_skip_to_next_step("select_time", {
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    })
    assert should_skip is True and next_node == "confirm_booking"
    print("   ✓ All tests passed")
    
    # Test 3: validate_required_fields_for_step
    print("\n3. Testing validate_required_fields_for_step...")
    is_valid, missing, redirect = validate_required_fields_for_step("select_property", {})
    assert is_valid is True
    
    is_valid, missing, redirect = validate_required_fields_for_step("select_court", {})
    assert is_valid is False and missing == "property_id" and redirect == "select_property"
    
    is_valid, missing, redirect = validate_required_fields_for_step("select_court", {"property_id": 1})
    assert is_valid is True
    
    is_valid, missing, redirect = validate_required_fields_for_step("select_date", {"property_id": 1})
    assert is_valid is False and missing == "court_id" and redirect == "select_court"
    
    is_valid, missing, redirect = validate_required_fields_for_step("select_time", {"property_id": 1, "court_id": 10})
    assert is_valid is False and missing == "date" and redirect == "select_date"
    
    is_valid, missing, redirect = validate_required_fields_for_step("confirm_booking", {
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25"
    })
    assert is_valid is False and missing == "time_slot" and redirect == "select_time"
    
    is_valid, missing, redirect = validate_required_fields_for_step("confirm_booking", {
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    })
    assert is_valid is True
    print("   ✓ All tests passed")
    
    # Test 4: get_booking_progress_summary
    print("\n4. Testing get_booking_progress_summary...")
    summary = get_booking_progress_summary({})
    assert summary["completion_percentage"] == 0
    assert summary["completed_steps"] == 0
    assert summary["next_step"] == "select_property"
    
    summary = get_booking_progress_summary({"property_id": 1})
    assert summary["completion_percentage"] == 25
    assert summary["completed_steps"] == 1
    assert summary["next_step"] == "select_court"
    
    summary = get_booking_progress_summary({"property_id": 1, "court_id": 10})
    assert summary["completion_percentage"] == 50
    assert summary["completed_steps"] == 2
    assert summary["next_step"] == "select_date"
    
    summary = get_booking_progress_summary({
        "property_id": 1,
        "court_id": 10,
        "date": "2024-12-25",
        "time_slot": "14:00-15:00"
    })
    assert summary["completion_percentage"] == 100
    assert summary["completed_steps"] == 4
    assert summary["next_step"] == "confirm_booking"
    print("   ✓ All tests passed")
    
    # Test 5: validate_booking_flow_sequence
    print("\n5. Testing validate_booking_flow_sequence...")
    is_valid, redirect = validate_booking_flow_sequence("select_property", {})
    assert is_valid is True and redirect is None
    
    is_valid, redirect = validate_booking_flow_sequence("select_property", {"property_id": 1})
    assert is_valid is False and redirect == "select_court"
    
    is_valid, redirect = validate_booking_flow_sequence("select_court", {})
    assert is_valid is False and redirect == "select_property"
    
    is_valid, redirect = validate_booking_flow_sequence("select_court", {"property_id": 1})
    assert is_valid is True and redirect is None
    print("   ✓ All tests passed")
    
    print("\n" + "=" * 70)
    print("✅ All Flow Validation Tests Passed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
