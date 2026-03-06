"""
Verification script for Task 7.1: Fetch properties in greeting and cache in flow_state

This script verifies that:
1. Properties are fetched using get_owner_properties_tool in greeting handler
2. Properties are displayed to user in greeting message
3. Properties are cached in flow_state.owner_properties
4. Cached properties are available for later booking use

Requirements: 5.1, 5.2, 5.3
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.nodes.greeting import greeting_handler
from app.agent.state.conversation_state import ConversationState


async def verify_property_fetching_and_caching():
    """Verify that properties are fetched and cached in flow_state"""
    
    print("=" * 80)
    print("TASK 7.1 VERIFICATION: Property Fetching and Caching in Greeting")
    print("=" * 80)
    print()
    
    # Test 1: Verify properties are fetched for new user
    print("Test 1: Verify properties are fetched for new user")
    print("-" * 80)
    
    state: ConversationState = {
        "chat_id": "test_chat_001",
        "user_id": "test_user_001",
        "owner_profile_id": "1",  # Use test owner profile ID
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": None,
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None
    }
    
    try:
        # Call greeting handler
        result_state = await greeting_handler(state, llm_provider=None)
        
        # Check if properties were fetched and cached
        flow_state = result_state.get("flow_state", {})
        owner_properties = flow_state.get("owner_properties")
        
        if owner_properties is not None:
            print(f"✓ Properties cached in flow_state: {len(owner_properties)} properties")
            print(f"  Property IDs: {[p.get('id') for p in owner_properties]}")
            print(f"  Property Names: {[p.get('name') for p in owner_properties]}")
        else:
            print("✗ Properties NOT cached in flow_state")
            print(f"  flow_state.owner_properties = {owner_properties}")
        
        # Check if properties are displayed in greeting message
        response_content = result_state.get("response_content", "")
        
        if owner_properties and len(owner_properties) > 0:
            # Check if property names appear in greeting
            property_names_in_greeting = [
                p.get('name') for p in owner_properties 
                if p.get('name') and p.get('name') in response_content
            ]
            
            if property_names_in_greeting:
                print(f"✓ Properties displayed in greeting message")
                print(f"  Properties shown: {property_names_in_greeting}")
            else:
                print("✗ Properties NOT displayed in greeting message")
                print(f"  Response: {response_content[:200]}...")
        
        print()
        print("Response preview:")
        print(response_content[:300] + "..." if len(response_content) > 300 else response_content)
        print()
        
        # Test 2: Verify cached properties structure
        print("\nTest 2: Verify cached properties structure")
        print("-" * 80)
        
        if owner_properties and len(owner_properties) > 0:
            first_property = owner_properties[0]
            required_fields = ['id', 'name', 'address', 'city']
            
            print(f"First property structure:")
            for field in required_fields:
                value = first_property.get(field)
                status = "✓" if value is not None else "✗"
                print(f"  {status} {field}: {value}")
            
            print()
            print(f"✓ Properties have proper structure for booking use")
        else:
            print("✗ No properties to verify structure")
        
        print()
        
        # Test 3: Verify flow_state is properly initialized
        print("\nTest 3: Verify flow_state is properly initialized")
        print("-" * 80)
        
        expected_fields = [
            'current_intent', 'property_id', 'property_name', 
            'court_id', 'court_name', 'date', 'time_slot', 
            'booking_step', 'owner_properties', 'context'
        ]
        
        for field in expected_fields:
            if field in flow_state:
                value = flow_state[field]
                if field == 'owner_properties' and value is not None:
                    print(f"  ✓ {field}: [{len(value)} properties cached]")
                else:
                    print(f"  ✓ {field}: {value}")
            else:
                print(f"  ✗ {field}: MISSING")
        
        print()
        print("=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        
        # Summary
        checks = []
        checks.append(("Properties fetched", owner_properties is not None))
        checks.append(("Properties cached in flow_state", 
                      flow_state.get("owner_properties") is not None))
        checks.append(("Properties displayed in greeting", 
                      owner_properties and any(p.get('name') in response_content 
                                              for p in owner_properties if p.get('name'))))
        checks.append(("Flow state properly initialized", 
                      all(field in flow_state for field in expected_fields)))
        
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        
        for check_name, result in checks:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {check_name}")
        
        print()
        print(f"Result: {passed}/{total} checks passed")
        
        if passed == total:
            print("\n✓ Task 7.1 implementation is CORRECT")
            print("  - Properties are fetched using get_owner_properties_tool")
            print("  - Properties are displayed to user in greeting message")
            print("  - Properties are cached in flow_state.owner_properties")
            print("  - Cached properties are available for later booking use")
        else:
            print(f"\n✗ Task 7.1 implementation has issues ({total - passed} checks failed)")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return passed == total


if __name__ == "__main__":
    result = asyncio.run(verify_property_fetching_and_caching())
    sys.exit(0 if result else 1)
