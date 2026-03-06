"""
Simple verification script for Task 19.3: Add current date context to all date-related prompts

This script verifies that current_date is added to all date-related prompts by checking the source code.

Requirements: 17.1, 17.5
"""

import os
import re


def check_file_for_current_date(filepath, expected_patterns):
    """Check if a file contains expected current_date patterns."""
    print(f"\nChecking: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"  ✗ File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_found = True
    for pattern_name, pattern in expected_patterns.items():
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"  ✓ Found: {pattern_name}")
        else:
            print(f"  ✗ Missing: {pattern_name}")
            all_found = False
    
    return all_found


def verify_date_selection_prompt():
    """Verify date selection prompt includes current_date."""
    print("\n" + "=" * 70)
    print("Test 1: Date Selection Prompt")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/prompts/booking_prompts.py"
    
    patterns = {
        "current_date parameter in create_select_date_prompt": 
            r"def create_select_date_prompt\([^)]*current_date[^)]*\)",
        "current_date in SELECT_DATE_SYSTEM_TEMPLATE": 
            r"SELECT_DATE_SYSTEM_TEMPLATE.*?Current date:.*?\{current_date\}",
        "current_date in prompt.partial": 
            r"return prompt\.partial\([^)]*current_date=current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Date selection prompt correctly includes current_date")
    else:
        print("\n✗ Date selection prompt is missing current_date")
    
    return result


def verify_time_selection_prompt():
    """Verify time selection prompt includes current_date."""
    print("\n" + "=" * 70)
    print("Test 2: Time Selection Prompt")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/prompts/booking_prompts.py"
    
    patterns = {
        "current_date parameter in create_select_time_prompt": 
            r"def create_select_time_prompt\([^)]*current_date[^)]*\)",
        "current_date in SELECT_TIME_SYSTEM_TEMPLATE": 
            r"SELECT_TIME_SYSTEM_TEMPLATE.*?Current date:.*?\{current_date\}",
        "current_date in prompt.partial": 
            r"return prompt\.partial\([^)]*current_date=current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Time selection prompt correctly includes current_date")
    else:
        print("\n✗ Time selection prompt is missing current_date")
    
    return result


def verify_confirmation_prompt():
    """Verify confirmation prompt includes current_date."""
    print("\n" + "=" * 70)
    print("Test 3: Confirmation Prompt")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/prompts/booking_prompts.py"
    
    patterns = {
        "current_date parameter in create_confirm_booking_prompt": 
            r"def create_confirm_booking_prompt\([^)]*current_date[^)]*\)",
        "current_date in CONFIRM_BOOKING_SYSTEM_TEMPLATE": 
            r"CONFIRM_BOOKING_SYSTEM_TEMPLATE.*?Current date:.*?\{current_date\}",
        "current_date in prompt.partial": 
            r"return prompt\.partial\([^)]*current_date=current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Confirmation prompt correctly includes current_date")
    else:
        print("\n✗ Confirmation prompt is missing current_date")
    
    return result


def verify_select_time_node():
    """Verify select_time node passes current_date to prompt."""
    print("\n" + "=" * 70)
    print("Test 4: Select Time Node Passes Current Date")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/nodes/booking/select_time.py"
    
    patterns = {
        "current_date calculation in ISO format": 
            r'current_date\s*=\s*datetime\.now\(\)\.date\(\)\.strftime\("%Y-%m-%d"\)',
        "current_date passed to create_select_time_prompt": 
            r"create_select_time_prompt\([^)]*current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Select time node correctly passes current_date")
    else:
        print("\n✗ Select time node is missing current_date")
    
    return result


def verify_confirm_node():
    """Verify confirm node passes current_date to prompt."""
    print("\n" + "=" * 70)
    print("Test 5: Confirm Node Passes Current Date")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/nodes/booking/confirm.py"
    
    patterns = {
        "current_date calculation in ISO format": 
            r'current_date\s*=\s*datetime\.now\(\)\.date\(\)\.strftime\("%Y-%m-%d"\)',
        "current_date passed to create_confirm_booking_prompt": 
            r"create_confirm_booking_prompt\([^)]*current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Confirm node correctly passes current_date")
    else:
        print("\n✗ Confirm node is missing current_date")
    
    return result


def verify_select_date_node():
    """Verify select_date node already has current_date (from previous task)."""
    print("\n" + "=" * 70)
    print("Test 6: Select Date Node Has Current Date (Pre-existing)")
    print("=" * 70)
    
    filepath = "Backend/apps/chatbot/app/agent/nodes/booking/select_date.py"
    
    patterns = {
        "current_date calculation in ISO format": 
            r'current_date\s*=\s*datetime\.now\(\)\.date\(\)\.strftime\("%Y-%m-%d"\)',
        "current_date passed to create_select_date_prompt": 
            r"create_select_date_prompt\([^)]*current_date[^)]*\)"
    }
    
    result = check_file_for_current_date(filepath, patterns)
    
    if result:
        print("\n✓ Select date node correctly has current_date")
    else:
        print("\n✗ Select date node is missing current_date")
    
    return result


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("TASK 19.3 VERIFICATION")
    print("Add current date context to all date-related prompts")
    print("=" * 70)
    
    results = []
    
    # Test prompts
    results.append(("Date Selection Prompt", verify_date_selection_prompt()))
    results.append(("Time Selection Prompt", verify_time_selection_prompt()))
    results.append(("Confirmation Prompt", verify_confirmation_prompt()))
    
    # Test nodes
    results.append(("Select Time Node", verify_select_time_node()))
    results.append(("Confirm Node", verify_confirm_node()))
    results.append(("Select Date Node", verify_select_date_node()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED - Task 19.3 implementation is correct!")
        print("=" * 70)
        print("\nRequirements validated:")
        print("  ✓ 17.1: LLM receives current date in ISO format (YYYY-MM-DD)")
        print("  ✓ 17.5: Current date included in all date-related prompts")
        print("\nImplementation details:")
        print("  • Date selection prompt: current_date already included (from previous task)")
        print("  • Time selection prompt: current_date added to template and function")
        print("  • Confirmation prompt: current_date added to template and function")
        print("  • All nodes pass current_date in ISO format (YYYY-MM-DD)")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Please review the implementation")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
