"""
Verification script for Task 19.3: Add current date context to all date-related prompts

This script verifies that:
1. Date selection prompt includes current_date
2. Time selection prompt includes current_date
3. Confirmation prompt includes current_date
4. All prompts format current_date in ISO format (YYYY-MM-DD)

Requirements: 17.1, 17.5
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from apps.chatbot.app.agent.prompts.booking_prompts import (
    create_select_date_prompt,
    create_select_time_prompt,
    create_confirm_booking_prompt
)


def test_date_selection_prompt_has_current_date():
    """Test that date selection prompt includes current_date in ISO format."""
    print("\n=== Test 1: Date Selection Prompt Has Current Date ===")
    
    property_name = "Test Property"
    service_name = "Test Court"
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    
    prompt = create_select_date_prompt(property_name, service_name, current_date)
    
    # Get the prompt template text
    prompt_text = str(prompt.messages[0].prompt.template)
    
    # Check if current_date is in the template
    if "{current_date}" in prompt_text:
        print("✓ Date selection prompt includes {current_date} placeholder")
    else:
        print("✗ Date selection prompt MISSING {current_date} placeholder")
        return False
    
    # Check if current_date is mentioned in guidelines
    if "Current date:" in prompt_text or "current_date" in prompt_text.lower():
        print("✓ Date selection prompt references current_date in guidelines")
    else:
        print("✗ Date selection prompt does NOT reference current_date in guidelines")
        return False
    
    # Verify the prompt is partially filled with current_date
    if hasattr(prompt, 'partial_variables') and 'current_date' in prompt.partial_variables:
        actual_date = prompt.partial_variables['current_date']
        print(f"✓ Date selection prompt has current_date set to: {actual_date}")
        
        # Verify ISO format (YYYY-MM-DD)
        try:
            datetime.strptime(actual_date, "%Y-%m-%d")
            print("✓ Current date is in ISO format (YYYY-MM-DD)")
        except ValueError:
            print(f"✗ Current date is NOT in ISO format: {actual_date}")
            return False
    else:
        print("✗ Date selection prompt does NOT have current_date in partial_variables")
        return False
    
    print("✓ Test 1 PASSED: Date selection prompt correctly includes current_date\n")
    return True


def test_time_selection_prompt_has_current_date():
    """Test that time selection prompt includes current_date in ISO format."""
    print("\n=== Test 2: Time Selection Prompt Has Current Date ===")
    
    property_name = "Test Property"
    service_name = "Test Court"
    date = "2026-03-10"
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    slots = [
        {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0}
    ]
    
    prompt = create_select_time_prompt(property_name, service_name, date, slots, current_date)
    
    # Get the prompt template text
    prompt_text = str(prompt.messages[0].prompt.template)
    
    # Check if current_date is in the template
    if "{current_date}" in prompt_text:
        print("✓ Time selection prompt includes {current_date} placeholder")
    else:
        print("✗ Time selection prompt MISSING {current_date} placeholder")
        return False
    
    # Check if current_date is mentioned in the prompt
    if "Current date:" in prompt_text or "current_date" in prompt_text.lower():
        print("✓ Time selection prompt references current_date")
    else:
        print("✗ Time selection prompt does NOT reference current_date")
        return False
    
    # Verify the prompt is partially filled with current_date
    if hasattr(prompt, 'partial_variables') and 'current_date' in prompt.partial_variables:
        actual_date = prompt.partial_variables['current_date']
        print(f"✓ Time selection prompt has current_date set to: {actual_date}")
        
        # Verify ISO format (YYYY-MM-DD)
        try:
            datetime.strptime(actual_date, "%Y-%m-%d")
            print("✓ Current date is in ISO format (YYYY-MM-DD)")
        except ValueError:
            print(f"✗ Current date is NOT in ISO format: {actual_date}")
            return False
    else:
        print("✗ Time selection prompt does NOT have current_date in partial_variables")
        return False
    
    print("✓ Test 2 PASSED: Time selection prompt correctly includes current_date\n")
    return True


def test_confirmation_prompt_has_current_date():
    """Test that confirmation prompt includes current_date in ISO format."""
    print("\n=== Test 3: Confirmation Prompt Has Current Date ===")
    
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    flow_state = {
        "property_name": "Test Property",
        "service_name": "Test Court",
        "sport_type": "Tennis",
        "date": "2026-03-10",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "price": 50.0,
        "total_price": 50.0,
        "duration_hours": 1.0
    }
    
    prompt = create_confirm_booking_prompt(flow_state, current_date)
    
    # Get the prompt template text
    prompt_text = str(prompt.messages[0].prompt.template)
    
    # Check if current_date is in the template
    if "{current_date}" in prompt_text:
        print("✓ Confirmation prompt includes {current_date} placeholder")
    else:
        print("✗ Confirmation prompt MISSING {current_date} placeholder")
        return False
    
    # Check if current_date is mentioned in the prompt
    if "Current date:" in prompt_text or "current_date" in prompt_text.lower():
        print("✓ Confirmation prompt references current_date")
    else:
        print("✗ Confirmation prompt does NOT reference current_date")
        return False
    
    # Verify the prompt is partially filled with current_date
    if hasattr(prompt, 'partial_variables') and 'current_date' in prompt.partial_variables:
        actual_date = prompt.partial_variables['current_date']
        print(f"✓ Confirmation prompt has current_date set to: {actual_date}")
        
        # Verify ISO format (YYYY-MM-DD)
        try:
            datetime.strptime(actual_date, "%Y-%m-%d")
            print("✓ Current date is in ISO format (YYYY-MM-DD)")
        except ValueError:
            print(f"✗ Current date is NOT in ISO format: {actual_date}")
            return False
    else:
        print("✗ Confirmation prompt does NOT have current_date in partial_variables")
        return False
    
    print("✓ Test 3 PASSED: Confirmation prompt correctly includes current_date\n")
    return True


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("TASK 19.3 VERIFICATION: Add current date context to all date-related prompts")
    print("=" * 70)
    
    results = []
    
    # Test 1: Date selection prompt
    results.append(("Date Selection Prompt", test_date_selection_prompt_has_current_date()))
    
    # Test 2: Time selection prompt
    results.append(("Time Selection Prompt", test_time_selection_prompt_has_current_date()))
    
    # Test 3: Confirmation prompt
    results.append(("Confirmation Prompt", test_confirmation_prompt_has_current_date()))
    
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
        print("\n✓ ALL TESTS PASSED - Task 19.3 implementation is correct!")
        print("\nRequirements validated:")
        print("  - 17.1: LLM receives current date in ISO format (YYYY-MM-DD)")
        print("  - 17.5: Current date included in all date-related prompts")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Please review the implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
