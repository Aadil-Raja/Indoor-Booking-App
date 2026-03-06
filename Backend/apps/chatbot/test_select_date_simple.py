"""
Simple verification script for Task 11.1: select_date node date parsing

This script tests the _parse_date function directly without requiring
database connections or full environment setup.

Tests:
1. Parse "tomorrow" as current_date + 1 day
2. Parse "next Monday" calculation
3. Parse ISO date format (YYYY-MM-DD)
4. Parse various natural language formats
"""

import sys
import os
from datetime import datetime, timedelta

# Add the Backend directory to the path
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, backend_dir)

# Import the _parse_date function directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "select_date_module",
    os.path.join(os.path.dirname(__file__), "app", "agent", "nodes", "booking", "select_date.py")
)
select_date_module = importlib.util.module_from_spec(spec)

# We need to mock some imports before loading
import sys
from unittest.mock import MagicMock

# Mock the imports that require database
sys.modules['app.agent.state.conversation_state'] = MagicMock()
sys.modules['app.agent.tools'] = MagicMock()
sys.modules['app.services.llm.langchain_wrapper'] = MagicMock()
sys.modules['app.agent.prompts.booking_prompts'] = MagicMock()
sys.modules['app.services.llm.base'] = MagicMock()

# Load the module
spec.loader.exec_module(select_date_module)
_parse_date = select_date_module._parse_date


def test_parse_tomorrow():
    """Test parsing 'tomorrow' as current_date + 1 day"""
    print("\n=== Test 1: Parse 'tomorrow' ===")
    
    result = _parse_date("tomorrow")
    expected = datetime.now().date() + timedelta(days=1)
    
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"✓ Correctly parsed 'tomorrow' as {result}")
    return True


def test_parse_today():
    """Test parsing 'today'"""
    print("\n=== Test 2: Parse 'today' ===")
    
    result = _parse_date("today")
    expected = datetime.now().date()
    
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"✓ Correctly parsed 'today' as {result}")
    return True


def test_parse_in_days():
    """Test parsing 'in X days' format"""
    print("\n=== Test 3: Parse 'in 3 days' ===")
    
    result = _parse_date("in 3 days")
    expected = datetime.now().date() + timedelta(days=3)
    
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"✓ Correctly parsed 'in 3 days' as {result}")
    return True


def test_parse_next_monday():
    """Test parsing 'next Monday'"""
    print("\n=== Test 4: Parse 'next Monday' ===")
    
    result = _parse_date("next Monday")
    today = datetime.now().date()
    
    # Should be at least 1 day in the future
    assert result > today, f"Next Monday should be in the future, got {result}"
    
    # Should be a Monday (weekday 0)
    assert result.weekday() == 0, f"Should be Monday (0), got {result.weekday()}"
    
    print(f"✓ Correctly parsed 'next Monday' as {result} (weekday: {result.weekday()})")
    return True


def test_parse_iso_date():
    """Test parsing ISO date format (YYYY-MM-DD)"""
    print("\n=== Test 5: Parse ISO Date '2025-12-25' ===")
    
    result = _parse_date("2025-12-25")
    expected = datetime(2025, 12, 25).date()
    
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"✓ Correctly parsed ISO date as {result}")
    return True


def test_parse_slash_date():
    """Test parsing date with slashes (MM/DD/YYYY)"""
    print("\n=== Test 6: Parse '12/25/2025' ===")
    
    result = _parse_date("12/25/2025")
    expected = datetime(2025, 12, 25).date()
    
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"✓ Correctly parsed slash date as {result}")
    return True


def test_parse_month_name():
    """Test parsing natural language with month name"""
    print("\n=== Test 7: Parse 'December 25' ===")
    
    result = _parse_date("December 25")
    
    # Should parse to December 25 of current or next year
    assert result is not None, "Should parse month name format"
    assert result.month == 12, f"Should be December (12), got {result.month}"
    assert result.day == 25, f"Should be day 25, got {result.day}"
    
    print(f"✓ Correctly parsed 'December 25' as {result}")
    return True


def test_parse_invalid():
    """Test that invalid input returns None"""
    print("\n=== Test 8: Parse invalid input ===")
    
    result = _parse_date("not a date")
    
    assert result is None, f"Should return None for invalid input, got {result}"
    print("✓ Correctly returned None for invalid input")
    return True


def test_parse_empty():
    """Test that empty input returns None"""
    print("\n=== Test 9: Parse empty input ===")
    
    result = _parse_date("")
    
    assert result is None, f"Should return None for empty input, got {result}"
    print("✓ Correctly returned None for empty input")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Task 11.1 Simple Verification: _parse_date function")
    print("=" * 60)
    
    tests = [
        ("Parse 'tomorrow'", test_parse_tomorrow),
        ("Parse 'today'", test_parse_today),
        ("Parse 'in 3 days'", test_parse_in_days),
        ("Parse 'next Monday'", test_parse_next_monday),
        ("Parse ISO date", test_parse_iso_date),
        ("Parse slash date", test_parse_slash_date),
        ("Parse month name", test_parse_month_name),
        ("Parse invalid input", test_parse_invalid),
        ("Parse empty input", test_parse_empty),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"✗ {test_name} failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"  Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All date parsing tests passed!")
        print("\nVerified Requirements:")
        print("  - 17.2: Support 'tomorrow' calculation (current_date + 1 day)")
        print("  - 17.3: Support 'next Monday' calculation based on current date")
        print("  - 17.4: Convert natural language to YYYY-MM-DD format")
        print("  - 8.5: Date format validation")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
