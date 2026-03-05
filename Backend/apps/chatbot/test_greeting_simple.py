"""
Simple test for greeting handler business_name personalization.

This script directly tests the greeting generation functions without
requiring database connections.
"""


def _generate_new_user_greeting(owner_profile: dict) -> str:
    """
    Generate a simple greeting for a new user (fallback).
    
    This greeting introduces the bot and explains what it can do,
    helping new users understand the available functionality.
    Used as fallback when property information is not available.
    
    Args:
        owner_profile: Owner profile dictionary with business_name
    
    Returns:
        str: Greeting message for new users
    """
    business_name = owner_profile.get("business_name") or "our facility"
    
    return (
        f"Hello! I am {business_name}'s assistant. "
        "I can show you indoors and courts where you can play futsal, cricket, etc. "
        "What would you like to do today?"
    )


def _generate_new_user_greeting_with_properties(owner_profile: dict, properties: list) -> tuple:
    """
    Generate a rich greeting with property information for new users.
    
    Creates a personalized welcome message that introduces the facility
    with business_name, property name, address, city, and map link.
    
    Args:
        owner_profile: Owner profile dictionary with business_name
        properties: List of property dictionaries
        
    Returns:
        Tuple of (response_content, response_type, response_metadata)
    """
    if not properties:
        return _generate_new_user_greeting(owner_profile), "text", {}
    
    # Get business_name from owner profile
    business_name = owner_profile.get("business_name") or "our facility"
    
    # Create greeting message with business_name personalization
    greeting_text = f"Hello, I am {business_name}'s assistant. I can show you indoors and courts where you can play futsal, cricket, etc.\n\n"
    
    # Add available properties information
    greeting_text += "Here are our available facilities:\n\n"
    
    for idx, property_info in enumerate(properties, 1):
        property_name = property_info.get("name", "Facility")
        address = property_info.get("address", "")
        city = property_info.get("city", "")
        state_name = property_info.get("state", "")
        maps_link = property_info.get("maps_link", "")
        
        # Build location string
        location_parts = []
        if address:
            location_parts.append(address)
        if city:
            location_parts.append(city)
        if state_name:
            location_parts.append(state_name)
        
        location = ", ".join(location_parts) if location_parts else "Location not specified"
        
        # Add property information
        greeting_text += f"{idx}. {property_name}\n"
        greeting_text += f"   Location: {location}\n"
        
        # Add map link if available
        if maps_link:
            greeting_text += f"   View on map: {maps_link}\n"
        
        greeting_text += "\n"
    
    greeting_text += "How can I help you today? I can:\n"
    greeting_text += "• Show you available courts and facilities\n"
    greeting_text += "• Help you make a booking\n"
    greeting_text += "• Answer questions about pricing and availability"
    
    return greeting_text, "text", {}


def test_greeting_with_business_name():
    """Test greeting generation with business_name."""
    print("\n=== Test 1: Greeting with business_name ===")
    
    owner_profile = {
        "id": 1,
        "business_name": "Sports Arena Pro",
        "phone": "123-456-7890"
    }
    
    greeting = _generate_new_user_greeting(owner_profile)
    print(f"Generated greeting:\n{greeting}\n")
    
    # Verify requirements
    checks = [
        ("Sports Arena Pro" in greeting, "Business name is included"),
        ("assistant" in greeting, "Mentions assistant"),
        ("futsal" in greeting, "Mentions futsal"),
        ("cricket" in greeting, "Mentions cricket"),
    ]
    
    print("Verification:")
    all_passed = True
    for check, description in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"  {status}: {description}")
        if not check:
            all_passed = False
    
    return all_passed


def test_greeting_without_business_name():
    """Test greeting generation without business_name (fallback)."""
    print("\n=== Test 2: Greeting without business_name (fallback) ===")
    
    owner_profile = {
        "id": 1,
        "business_name": None
    }
    
    greeting = _generate_new_user_greeting(owner_profile)
    print(f"Generated greeting:\n{greeting}\n")
    
    # Verify fallback
    checks = [
        ("our facility" in greeting, "Uses fallback 'our facility'"),
        ("assistant" in greeting, "Mentions assistant"),
        ("futsal" in greeting, "Mentions futsal"),
        ("cricket" in greeting, "Mentions cricket"),
    ]
    
    print("Verification:")
    all_passed = True
    for check, description in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"  {status}: {description}")
        if not check:
            all_passed = False
    
    return all_passed


def test_greeting_with_properties():
    """Test greeting generation with properties."""
    print("\n=== Test 3: Greeting with properties ===")
    
    owner_profile = {
        "id": 1,
        "business_name": "Elite Sports Complex",
        "phone": "123-456-7890"
    }
    
    properties = [
        {
            "id": 1,
            "name": "Downtown Arena",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "maps_link": "https://maps.google.com/downtown"
        },
        {
            "id": 2,
            "name": "Uptown Sports Center",
            "address": "456 Park Ave",
            "city": "New York",
            "state": "NY",
            "maps_link": "https://maps.google.com/uptown"
        }
    ]
    
    greeting, response_type, metadata = _generate_new_user_greeting_with_properties(
        owner_profile, properties
    )
    
    print(f"Generated greeting:\n{greeting}\n")
    print(f"Response type: {response_type}\n")
    
    # Verify requirements
    checks = [
        ("Elite Sports Complex" in greeting, "Business name is included"),
        ("assistant" in greeting, "Mentions assistant"),
        ("futsal" in greeting, "Mentions futsal"),
        ("cricket" in greeting, "Mentions cricket"),
        ("Downtown Arena" in greeting, "First property is listed"),
        ("Uptown Sports Center" in greeting, "Second property is listed"),
        ("123 Main St" in greeting, "Property address is shown"),
        ("New York" in greeting, "City is shown"),
        ("View on map" in greeting, "Map link is included"),
        (response_type == "text", "Response type is 'text'"),
    ]
    
    print("Verification:")
    all_passed = True
    for check, description in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"  {status}: {description}")
        if not check:
            all_passed = False
    
    return all_passed


def test_greeting_with_empty_properties():
    """Test greeting generation with empty properties list."""
    print("\n=== Test 4: Greeting with empty properties (fallback) ===")
    
    owner_profile = {
        "id": 1,
        "business_name": "Test Facility",
        "phone": "123-456-7890"
    }
    
    properties = []
    
    greeting, response_type, metadata = _generate_new_user_greeting_with_properties(
        owner_profile, properties
    )
    
    print(f"Generated greeting:\n{greeting}\n")
    
    # Should fall back to simple greeting
    checks = [
        ("Test Facility" in greeting, "Business name is included"),
        ("assistant" in greeting, "Mentions assistant"),
        ("futsal" in greeting, "Mentions futsal"),
        ("cricket" in greeting, "Mentions cricket"),
    ]
    
    print("Verification:")
    all_passed = True
    for check, description in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"  {status}: {description}")
        if not check:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("=" * 70)
    print("Greeting Handler Business Name Personalization Tests")
    print("=" * 70)
    
    results = []
    results.append(("Test 1", test_greeting_with_business_name()))
    results.append(("Test 2", test_greeting_without_business_name()))
    results.append(("Test 3", test_greeting_with_properties()))
    results.append(("Test 4", test_greeting_with_empty_properties()))
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
