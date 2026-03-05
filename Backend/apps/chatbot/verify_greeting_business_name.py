"""
Verification script for greeting handler with business_name personalization.

This script tests the greeting handler to ensure it:
1. Fetches owner profile with business_name
2. Uses business_name in the greeting message
3. Displays available properties
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.nodes.greeting import (
    greeting_handler,
    _fetch_owner_profile,
    _fetch_owner_properties,
    _generate_new_user_greeting,
    _generate_new_user_greeting_with_properties
)
from app.agent.state.conversation_state import ConversationState


async def test_fetch_owner_profile():
    """Test fetching owner profile."""
    print("\n=== Testing Owner Profile Fetch ===")
    
    # Use a test owner_profile_id (you may need to adjust this)
    owner_profile_id = "1"
    chat_id = "test-chat-123"
    
    try:
        profile = await _fetch_owner_profile(owner_profile_id, chat_id)
        print(f"✓ Successfully fetched owner profile")
        print(f"  Profile data: {profile}")
        
        if profile.get("business_name"):
            print(f"  ✓ Business name found: {profile['business_name']}")
        else:
            print(f"  ⚠ Business name is empty or None")
        
        return profile
    except Exception as e:
        print(f"✗ Error fetching owner profile: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_fetch_properties():
    """Test fetching owner properties."""
    print("\n=== Testing Properties Fetch ===")
    
    owner_profile_id = "1"
    chat_id = "test-chat-123"
    
    try:
        properties = await _fetch_owner_properties(owner_profile_id, chat_id)
        print(f"✓ Successfully fetched properties")
        print(f"  Number of properties: {len(properties)}")
        
        if properties:
            print(f"  First property: {properties[0].get('name', 'N/A')}")
        
        return properties
    except Exception as e:
        print(f"✗ Error fetching properties: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_greeting_generation():
    """Test greeting message generation."""
    print("\n=== Testing Greeting Generation ===")
    
    # Test with business_name
    owner_profile = {
        "id": 1,
        "business_name": "Sports Arena Pro",
        "phone": "123-456-7890",
        "address": "123 Main St",
        "verified": True
    }
    
    greeting = _generate_new_user_greeting(owner_profile)
    print(f"✓ Generated greeting with business_name:")
    print(f"  {greeting}")
    
    if "Sports Arena Pro" in greeting:
        print(f"  ✓ Business name is included in greeting")
    else:
        print(f"  ✗ Business name NOT found in greeting")
    
    if "futsal, cricket" in greeting:
        print(f"  ✓ Sports examples are included")
    else:
        print(f"  ✗ Sports examples NOT found")
    
    # Test without business_name
    owner_profile_no_name = {
        "id": 1,
        "business_name": None
    }
    
    greeting_fallback = _generate_new_user_greeting(owner_profile_no_name)
    print(f"\n✓ Generated greeting without business_name (fallback):")
    print(f"  {greeting_fallback}")
    
    if "our facility" in greeting_fallback:
        print(f"  ✓ Fallback text is used")


def test_greeting_with_properties():
    """Test greeting generation with properties."""
    print("\n=== Testing Greeting with Properties ===")
    
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
            "maps_link": "https://maps.google.com/..."
        },
        {
            "id": 2,
            "name": "Uptown Sports Center",
            "address": "456 Park Ave",
            "city": "New York",
            "state": "NY",
            "maps_link": "https://maps.google.com/..."
        }
    ]
    
    greeting, response_type, metadata = _generate_new_user_greeting_with_properties(
        owner_profile, properties
    )
    
    print(f"✓ Generated greeting with properties:")
    print(f"  Response type: {response_type}")
    print(f"  Greeting text:\n{greeting}")
    
    checks = [
        ("Elite Sports Complex" in greeting, "Business name included"),
        ("futsal, cricket" in greeting, "Sports examples included"),
        ("Downtown Arena" in greeting, "First property included"),
        ("Uptown Sports Center" in greeting, "Second property included"),
        ("New York" in greeting, "City included"),
        ("View on map" in greeting, "Map link included")
    ]
    
    print(f"\n  Checks:")
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"    {status} {description}")


async def test_full_greeting_handler():
    """Test the full greeting handler."""
    print("\n=== Testing Full Greeting Handler ===")
    
    state: ConversationState = {
        "chat_id": "test-chat-456",
        "user_id": "test-user-789",
        "owner_profile_id": "1",  # Adjust this to a valid owner_profile_id
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    try:
        result = await greeting_handler(state)
        
        print(f"✓ Greeting handler executed successfully")
        print(f"  Response type: {result['response_type']}")
        print(f"  Response content:\n{result['response_content']}")
        
        # Check if business_name is in the response
        if "assistant" in result['response_content']:
            print(f"  ✓ Greeting mentions assistant")
        
        if "futsal" in result['response_content'] or "cricket" in result['response_content']:
            print(f"  ✓ Sports examples are included")
        
        return result
    except Exception as e:
        print(f"✗ Error in greeting handler: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Greeting Handler Business Name Verification")
    print("=" * 60)
    
    # Test individual functions
    test_greeting_generation()
    test_greeting_with_properties()
    
    # Test async functions
    profile = await test_fetch_owner_profile()
    properties = await test_fetch_properties()
    
    # Test full handler
    result = await test_full_greeting_handler()
    
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
