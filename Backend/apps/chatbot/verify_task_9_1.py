"""
Verification script for Task 9.1: Create select_property_node in booking subgraph

This script verifies that:
1. Property selection is skipped when property_id exists in flow_state
2. Properties are fetched on-demand using get_owner_properties_tool
3. Fetched properties are cached in flow_state.owner_properties
4. Single property is auto-selected and stored in flow_state
5. Multiple properties are presented as options
6. Error handling for no properties available
7. booking_step is updated to "property_selected" when complete

Requirements: 5.2, 5.3, 6.1, 6.2, 6.4, 7.1, 8.2
"""

import asyncio
import sys
import os

# Add the Backend directory to the path for shared modules
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, backend_dir)

# Add the chatbot app directory to the path
chatbot_dir = os.path.dirname(__file__)
sys.path.insert(0, chatbot_dir)

# Import directly from the module file to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "select_property_module",
    os.path.join(chatbot_dir, "app", "agent", "nodes", "booking", "select_property.py")
)
select_property_module = importlib.util.module_from_spec(spec)

# Mock the get_owner_properties_tool before loading the module
async def mock_get_owner_properties(owner_profile_id: int):
    """Mock get_owner_properties tool"""
    if owner_profile_id == 1:
        return [
            {"id": 1, "name": "Property A", "address": "123 Main St", "city": "NYC"},
            {"id": 2, "name": "Property B", "address": "456 Oak Ave", "city": "LA"}
        ]
    elif owner_profile_id == 2:
        return [
            {"id": 3, "name": "Single Property", "address": "789 Pine Rd", "city": "SF"}
        ]
    elif owner_profile_id == 3:
        return []  # No properties
    return []

# Patch the import in the module
import unittest.mock
with unittest.mock.patch.dict('sys.modules', {
    'app.agent.tools.property_tool': unittest.mock.MagicMock(
        get_owner_properties_tool=mock_get_owner_properties
    )
}):
    spec.loader.exec_module(select_property_module)

select_property = select_property_module.select_property

# Now replace the tool function in the loaded module
select_property_module.get_owner_properties_tool = mock_get_owner_properties

# Define ConversationState inline to avoid circular imports
from typing import TypedDict, List, Dict, Any, Optional

class ConversationState(TypedDict):
    chat_id: str
    user_id: str
    owner_profile_id: str
    user_message: str
    flow_state: Dict[str, Any]
    bot_memory: Dict[str, Any]
    messages: List[Dict[str, str]]
    intent: Optional[str]
    response_content: str
    response_type: str
    response_metadata: Dict[str, Any]
    token_usage: Optional[int]
    search_results: Optional[List[Dict[str, Any]]]
    availability_data: Optional[Dict[str, Any]]
    pricing_data: Optional[Dict[str, Any]]


# Mock tools - not used since we mock directly in the module
MOCK_TOOLS = {}


async def test_skip_when_property_already_selected():
    """Test that property selection is skipped when property_id exists in flow_state"""
    print("\n=== Test 1: Skip when property already selected ===")
    
    # Setup state with property already selected
    state = ConversationState(
        chat_id="test-123",
        user_id="user-1",
        owner_profile_id="1",
        user_message="I want to book",
        flow_state={
            "property_id": 1,
            "property_name": "Sports Center"
        },
        bot_memory={},
        messages=[],
        intent=None,
        response_content="",
        response_type="text",
        response_metadata={},
        token_usage=None,
        search_results=None,
        availability_data=None,
        pricing_data=None
    )
    
    # Call select_property
    result = await select_property(state, MOCK_TOOLS)
    
    # Verify property selection was skipped (Requirement 7.1)
    assert result["next_node"] == "select_court", \
        f"Expected next_node='select_court', got '{result.get('next_node')}'"
    assert result["flow_state"]["property_id"] == 1, \
        "Property ID should remain unchanged"
    assert result["flow_state"]["property_name"] == "Sports Center", \
        "Property name should remain unchanged"
    
    print("✓ Property selection skipped when already selected (Requirement 7.1)")
    print(f"  - Property ID: {result['flow_state']['property_id']}")
    print(f"  - Property Name: {result['flow_state']['property_name']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_auto_select_single_property():
    """Test that single property is auto-selected and stored in flow_state"""
    print("\n=== Test 2: Auto-select single property ===")
    
    # Setup state with owner that has single property
    state = ConversationState(
        chat_id="test-456",
        user_id="user-2",
        owner_profile_id="2",
        user_message="I want to book",
        flow_state={},
        bot_memory={},
        messages=[],
        intent=None,
        response_content="",
        response_type="text",
        response_metadata={},
        token_usage=None,
        search_results=None,
        availability_data=None,
        pricing_data=None
    )
    
    # Call select_property
    result = await select_property(state, MOCK_TOOLS)
    
    # Verify single property was auto-selected (Requirements 6.1, 6.2, 6.4)
    assert result["flow_state"]["property_id"] == 3, \
        f"Expected property_id=3, got {result['flow_state'].get('property_id')}"
    assert result["flow_state"]["property_name"] == "Single Property", \
        f"Expected property_name='Single Property', got {result['flow_state'].get('property_name')}"
    assert result["flow_state"]["booking_step"] == "property_selected", \
        f"Expected booking_step='property_selected', got {result['flow_state'].get('booking_step')}"
    assert result["next_node"] == "select_court", \
        f"Expected next_node='select_court', got {result.get('next_node')}"
    
    print("✓ Single property auto-selected successfully")
    print(f"  - Property ID: {result['flow_state']['property_id']}")
    print(f"  - Property Name: {result['flow_state']['property_name']}")
    print(f"  - Booking Step: {result['flow_state']['booking_step']} (Requirement 8.2)")
    print(f"  - Next node: {result['next_node']}")
    print("  - Requirements validated: 6.1, 6.2, 6.4, 8.2")
    return True


async def test_present_multiple_properties():
    """Test that multiple properties are presented as options"""
    print("\n=== Test 3: Present multiple properties ===")
    
    # Setup state with owner that has multiple properties
    state = ConversationState(
        chat_id="test-789",
        user_id="user-3",
        owner_profile_id="1",
        user_message="I want to book",
        flow_state={},
        bot_memory={},
        messages=[],
        intent=None,
        response_content="",
        response_type="text",
        response_metadata={},
        token_usage=None,
        search_results=None,
        availability_data=None,
        pricing_data=None
    )
    
    # Call select_property
    result = await select_property(state, MOCK_TOOLS)
    
    # Verify multiple properties are presented
    assert result["response_type"] == "button", \
        f"Expected response_type='button', got '{result.get('response_type')}'"
    assert "buttons" in result["response_metadata"], \
        "Expected buttons in response_metadata"
    assert len(result["response_metadata"]["buttons"]) == 2, \
        f"Expected 2 buttons, got {len(result['response_metadata']['buttons'])}"
    assert result["flow_state"]["booking_step"] == "awaiting_property_selection", \
        f"Expected booking_step='awaiting_property_selection', got {result['flow_state'].get('booking_step')}"
    assert result["next_node"] == "wait_for_selection", \
        f"Expected next_node='wait_for_selection', got {result.get('next_node')}"
    
    # Verify buttons contain property information
    buttons = result["response_metadata"]["buttons"]
    button_texts = [b["text"] for b in buttons]
    assert any("Property A" in text for text in button_texts), \
        "Expected 'Property A' in button texts"
    assert any("Property B" in text for text in button_texts), \
        "Expected 'Property B' in button texts"
    
    print("✓ Multiple properties presented as options")
    print(f"  - Response type: {result['response_type']}")
    print(f"  - Number of buttons: {len(buttons)}")
    print(f"  - Button texts: {button_texts}")
    print(f"  - Booking step: {result['flow_state']['booking_step']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_no_properties_available():
    """Test error handling when no properties are available"""
    print("\n=== Test 4: No properties available ===")
    
    # Setup state with owner that has no properties
    state = ConversationState(
        chat_id="test-999",
        user_id="user-4",
        owner_profile_id="3",
        user_message="I want to book",
        flow_state={},
        bot_memory={},
        messages=[],
        intent=None,
        response_content="",
        response_type="text",
        response_metadata={},
        token_usage=None,
        search_results=None,
        availability_data=None,
        pricing_data=None
    )
    
    # Call select_property
    result = await select_property(state, MOCK_TOOLS)
    
    # Verify error handling
    assert result["response_type"] == "text", \
        f"Expected response_type='text', got '{result.get('response_type')}'"
    assert "don't have any properties" in result["response_content"].lower(), \
        "Expected error message about no properties"
    assert result["next_node"] == "end", \
        f"Expected next_node='end', got {result.get('next_node')}"
    
    print("✓ No properties error handled correctly")
    print(f"  - Response: {result['response_content']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_on_demand_property_fetching():
    """Test that properties are fetched on-demand and cached"""
    print("\n=== Test 5: On-demand property fetching and caching ===")
    
    # Setup state without cached properties
    state = ConversationState(
        chat_id="test-111",
        user_id="user-5",
        owner_profile_id="1",
        user_message="I want to book",
        flow_state={},  # No cached properties
        bot_memory={},
        messages=[],
        intent=None,
        response_content="",
        response_type="text",
        response_metadata={},
        token_usage=None,
        search_results=None,
        availability_data=None,
        pricing_data=None
    )
    
    # Call select_property
    result = await select_property(state, MOCK_TOOLS)
    
    # Verify properties were fetched and cached (Requirements 5.2, 5.3)
    assert "owner_properties" in result["flow_state"], \
        "Properties should be cached in flow_state (Requirement 5.3)"
    assert len(result["flow_state"]["owner_properties"]) == 2, \
        f"Expected 2 cached properties, got {len(result['flow_state']['owner_properties'])}"
    
    # Verify properties were fetched on-demand (not at initialization)
    cached_properties = result["flow_state"]["owner_properties"]
    assert cached_properties[0]["name"] == "Property A", \
        "First property should be Property A"
    assert cached_properties[1]["name"] == "Property B", \
        "Second property should be Property B"
    
    print("✓ Properties fetched on-demand and cached successfully")
    print(f"  - Cached properties count: {len(cached_properties)}")
    print(f"  - Property names: {[p['name'] for p in cached_properties]}")
    print("  - Requirements validated: 5.2 (on-demand fetch), 5.3 (caching)")
    return True


async def test_use_cached_properties():
    """Test that cached properties are reused without re-fetching"""
    print("\n=== Test 6: Use cached properties ===")
    
    # Track if fetch was called
    fetch_called = False
    
    async def tracking_get_owner_properties(owner_profile_id: int):
        nonlocal fetch_called
        fetch_called = True
        return await mock_get_owner_properties(owner_profile_id)
    
    # Temporarily replace the mock
    original_mock = select_property_module.get_owner_properties_tool
    select_property_module.get_owner_properties_tool = tracking_get_owner_properties
    
    try:
        # Setup state with cached properties
        state = ConversationState(
            chat_id="test-222",
            user_id="user-6",
            owner_profile_id="1",
            user_message="I want to book",
            flow_state={
                "owner_properties": [
                    {"id": 1, "name": "Cached Property A", "address": "123 Main St", "city": "NYC"},
                    {"id": 2, "name": "Cached Property B", "address": "456 Oak Ave", "city": "LA"}
                ]
            },
            bot_memory={},
            messages=[],
            intent=None,
            response_content="",
            response_type="text",
            response_metadata={},
            token_usage=None,
            search_results=None,
            availability_data=None,
            pricing_data=None
        )
        
        # Call select_property
        result = await select_property(state, MOCK_TOOLS)
        
        # Verify cached properties were used without fetching
        assert not fetch_called, \
            "Should not fetch when properties are cached (Requirement 5.3)"
        assert result["response_type"] == "button", \
            "Should still present buttons"
        
        # Verify cached property names are used
        buttons = result["response_metadata"]["buttons"]
        button_texts = [b["text"] for b in buttons]
        assert any("Cached Property A" in text for text in button_texts), \
            "Should use cached property names"
        
        print("✓ Cached properties reused without re-fetching")
        print(f"  - Fetch called: {fetch_called}")
        print(f"  - Button texts: {button_texts}")
        print("  - Requirement validated: 5.3 (cache reuse)")
        return True
    finally:
        # Restore original mock
        select_property_module.get_owner_properties_tool = original_mock


async def main():
    """Run all verification tests"""
    print("=" * 70)
    print("Task 9.1 Verification: Create select_property_node in booking subgraph")
    print("=" * 70)
    
    tests = [
        test_skip_when_property_already_selected,
        test_auto_select_single_property,
        test_present_multiple_properties,
        test_no_properties_available,
        test_on_demand_property_fetching,
        test_use_cached_properties
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            results.append(False)
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 70)
    
    if all(results):
        print("\n✓ All tests passed! Task 9.1 implementation verified.")
        print("\nImplementation Summary:")
        print("- ✓ Skips property selection when property_id exists in flow_state (Req 7.1)")
        print("- ✓ Fetches properties on-demand using get_owner_properties_tool (Req 5.2)")
        print("- ✓ Caches fetched properties in flow_state.owner_properties (Req 5.3)")
        print("- ✓ Auto-selects single property and stores in flow_state (Req 6.1, 6.2)")
        print("- ✓ Presents multiple properties as button options (Req 6.4)")
        print("- ✓ Updates booking_step to 'property_selected' when complete (Req 8.2)")
        print("- ✓ Handles error when no properties available")
        print("- ✓ Reuses cached properties without re-fetching")
        print("\nRequirements validated: 5.2, 5.3, 6.1, 6.2, 6.4, 7.1, 8.2")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
