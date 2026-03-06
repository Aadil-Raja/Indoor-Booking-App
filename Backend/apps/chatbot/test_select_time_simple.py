"""
Simple standalone tests for select_time node helper functions.

This module tests the helper functions without triggering circular imports.
"""

import sys
from pathlib import Path
from datetime import datetime, date

# Add the chatbot app to path
chatbot_path = Path(__file__).parent / "app"
sys.path.insert(0, str(chatbot_path))

from agent.nodes.booking.select_time import (
    _format_time_slot,
    _format_time_for_display,
    _parse_time_selection
)


def test_format_time_slot():
    """Test time_slot formatting to HH:MM-HH:MM format (Requirement 8.5)."""
    print("Testing _format_time_slot...")
    
    # Test normal case
    result = _format_time_slot("14:00:00", "15:00:00")
    assert result == "14:00-15:00", f"Expected '14:00-15:00', got '{result}'"
    print("  ✓ Normal case: 14:00:00 -> 14:00-15:00")
    
    # Test without seconds
    result = _format_time_slot("09:30", "10:30")
    assert result == "09:30-10:30", f"Expected '09:30-10:30', got '{result}'"
    print("  ✓ Without seconds: 09:30 -> 09:30-10:30")
    
    # Test edge case
    result = _format_time_slot("23:45:00", "00:45:00")
    assert result == "23:45-00:45", f"Expected '23:45-00:45', got '{result}'"
    print("  ✓ Edge case: 23:45:00 -> 23:45-00:45")
    
    print("✅ All _format_time_slot tests passed!\n")


def test_format_time_for_display():
    """Test time formatting for user-friendly display."""
    print("Testing _format_time_for_display...")
    
    # Test afternoon time
    result = _format_time_for_display("14:00:00")
    assert result == "2:00 PM", f"Expected '2:00 PM', got '{result}'"
    print("  ✓ Afternoon: 14:00:00 -> 2:00 PM")
    
    # Test morning time
    result = _format_time_for_display("09:30:00")
    assert result == "9:30 AM", f"Expected '9:30 AM', got '{result}'"
    print("  ✓ Morning: 09:30:00 -> 9:30 AM")
    
    # Test noon
    result = _format_time_for_display("12:00:00")
    assert result == "12:00 PM", f"Expected '12:00 PM', got '{result}'"
    print("  ✓ Noon: 12:00:00 -> 12:00 PM")
    
    # Test midnight
    result = _format_time_for_display("00:00:00")
    assert result == "12:00 AM", f"Expected '12:00 AM', got '{result}'"
    print("  ✓ Midnight: 00:00:00 -> 12:00 AM")
    
    print("✅ All _format_time_for_display tests passed!\n")


def test_parse_time_selection():
    """Test parsing user time selection from various formats."""
    print("Testing _parse_time_selection...")
    
    available_slots = [
        {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0},
        {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 60.0},
        {"start_time": "18:00:00", "end_time": "19:00:00", "price_per_hour": 70.0}
    ]
    
    # Test exact time match
    result = _parse_time_selection("14:00", available_slots)
    assert result is not None, "Expected to find slot for '14:00'"
    assert result["start_time"] == "14:00:00", f"Expected '14:00:00', got '{result['start_time']}'"
    print("  ✓ Exact time match: '14:00' -> 14:00:00")
    
    # Test index selection
    result = _parse_time_selection("1", available_slots)
    assert result is not None, "Expected to find slot for index '1'"
    assert result["start_time"] == "09:00:00", f"Expected '09:00:00', got '{result['start_time']}'"
    print("  ✓ Index selection: '1' -> 09:00:00")
    
    # Test word-based index
    result = _parse_time_selection("second", available_slots)
    assert result is not None, "Expected to find slot for 'second'"
    assert result["start_time"] == "14:00:00", f"Expected '14:00:00', got '{result['start_time']}'"
    print("  ✓ Word-based index: 'second' -> 14:00:00")
    
    # Test PM format
    result = _parse_time_selection("2 pm", available_slots)
    assert result is not None, "Expected to find slot for '2 pm'"
    assert result["start_time"] == "14:00:00", f"Expected '14:00:00', got '{result['start_time']}'"
    print("  ✓ PM format: '2 pm' -> 14:00:00")
    
    # Test invalid selection
    result = _parse_time_selection("25:00", available_slots)
    assert result is None, "Expected None for invalid time '25:00'"
    print("  ✓ Invalid selection: '25:00' -> None")
    
    print("✅ All _parse_time_selection tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running select_time helper function tests")
    print("=" * 60)
    print()
    
    try:
        test_format_time_slot()
        test_format_time_for_display()
        test_parse_time_selection()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
