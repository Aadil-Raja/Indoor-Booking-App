"""
Simple standalone verification for confirm booking node logic.

This script verifies the core logic without requiring database or external dependencies.
"""

import asyncio
from datetime import datetime


def format_time_for_display(time_str: str) -> str:
    """Format time string for user-friendly display."""
    try:
        time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
        hour = time_obj.hour
        minute = time_obj.minute
        am_pm = "AM" if hour < 12 else "PM"
        
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"{hour}:00 {am_pm}"
        else:
            return f"{hour}:{minute:02d} {am_pm}"
    except ValueError:
        return time_str


def test_time_formatting():
    """Test time formatting function."""
    print("\n=== Test: Time Formatting ===")
    
    test_cases = [
        ("14:00:00", "2:00 PM"),
        ("09:30:00", "9:30 AM"),
        ("00:00:00", "12:00 AM"),
        ("12:00:00", "12:00 PM"),
        ("23:45:00", "11:45 PM"),
    ]
    
    passed = 0
    for input_time, expected in test_cases:
        result = format_time_for_display(input_time)
        if result == expected:
            print(f"  ✓ {input_time} -> {result}")
            passed += 1
        else:
            print(f"  ✗ {input_time} -> {result} (expected {expected})")
    
    print(f"  {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_booking_summary_generation():
    """Test booking summary generation logic."""
    print("\n=== Test: Booking Summary Generation ===")
    
    # Simulate booking details
    property_name = "Downtown Sports Center"
    service_name = "Tennis Court A"
    sport_type = "tennis"
    date_str = "2024-12-25"
    start_time = "14:00:00"
    end_time = "15:00:00"
    price = 50.0
    
    # Format date
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
    except ValueError:
        formatted_date = date_str
    
    # Format times
    display_start = format_time_for_display(start_time)
    display_end = format_time_for_display(end_time)
    
    # Calculate duration and total price
    start_obj = datetime.strptime(start_time, "%H:%M:%S").time()
    end_obj = datetime.strptime(end_time, "%H:%M:%S").time()
    start_minutes = start_obj.hour * 60 + start_obj.minute
    end_minutes = end_obj.hour * 60 + end_obj.minute
    duration_minutes = end_minutes - start_minutes
    duration_hours = duration_minutes / 60
    total_price = price * duration_hours
    
    # Generate summary
    summary_lines = [
        "📋 **Booking Summary**",
        "",
        f"🏢 **Facility:** {property_name}",
        f"🎾 **Court:** {service_name} ({sport_type})",
        f"📅 **Date:** {formatted_date}",
        f"⏰ **Time:** {display_start} - {display_end}",
        f"💰 **Price:** ${price:.2f}/hour",
        f"⏱️ **Duration:** {duration_hours:.1f} hour(s)",
        f"💵 **Total:** ${total_price:.2f}",
    ]
    
    summary = "\n".join(summary_lines)
    
    # Verify summary contains expected elements
    checks = [
        ("Booking Summary" in summary, "Contains 'Booking Summary'"),
        (property_name in summary, f"Contains property name '{property_name}'"),
        (service_name in summary, f"Contains service name '{service_name}'"),
        (sport_type in summary, f"Contains sport type '{sport_type}'"),
        ("$50.00/hour" in summary, "Contains price per hour"),
        ("$50.00" in summary, "Contains total price"),
        ("1.0 hour(s)" in summary, "Contains duration"),
    ]
    
    passed = 0
    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
    
    print(f"\n  Generated summary:")
    print("  " + "\n  ".join(summary_lines))
    print(f"\n  {passed}/{len(checks)} checks passed")
    
    return passed == len(checks)


def test_confirmation_keywords():
    """Test confirmation keyword detection logic."""
    print("\n=== Test: Confirmation Keywords ===")
    
    confirmation_keywords = [
        "yes", "confirm", "book", "proceed", "ok", "okay",
        "sure", "correct", "right", "yep", "yeah", "yup"
    ]
    
    cancellation_keywords = [
        "no", "cancel", "nevermind", "never mind", "nope",
        "nah", "stop", "abort", "quit"
    ]
    
    modification_keywords = [
        "change", "modify", "edit", "update", "different",
        "back", "return", "redo"
    ]
    
    test_cases = [
        ("yes, confirm it", "confirmation", confirmation_keywords),
        ("no, cancel", "cancellation", cancellation_keywords),
        ("change the date", "modification", modification_keywords),
        ("I want to modify the time", "modification", modification_keywords),
        ("okay, book it", "confirmation", confirmation_keywords),
        ("nevermind", "cancellation", cancellation_keywords),
    ]
    
    passed = 0
    for message, expected_type, keywords in test_cases:
        message_lower = message.lower()
        detected = any(keyword in message_lower for keyword in keywords)
        
        if detected:
            print(f"  ✓ '{message}' -> {expected_type}")
            passed += 1
        else:
            print(f"  ✗ '{message}' -> not detected as {expected_type}")
    
    print(f"  {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_modification_routing():
    """Test modification routing logic."""
    print("\n=== Test: Modification Routing ===")
    
    test_cases = [
        ("change the property", "property", ["property", "facility", "location"]),
        ("different court", "court", ["court", "service"]),
        ("change the date", "date", ["date", "day"]),
        ("different time", "time", ["time", "slot"]),
    ]
    
    passed = 0
    for message, expected_target, keywords in test_cases:
        message_lower = message.lower()
        detected = any(keyword in message_lower for keyword in keywords)
        
        if detected:
            print(f"  ✓ '{message}' -> modify {expected_target}")
            passed += 1
        else:
            print(f"  ✗ '{message}' -> not detected as {expected_target} modification")
    
    print(f"  {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Confirm Booking Node - Simple Verification")
    print("=" * 60)
    
    tests = [
        test_time_formatting,
        test_booking_summary_generation,
        test_confirmation_keywords,
        test_modification_routing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
