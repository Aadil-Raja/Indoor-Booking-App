"""
Verification script for Task 7.2: Reuse cached properties in booking flow

This script verifies that:
1. select_property_node checks if owner_properties exists in flow_state
2. If exists, uses cached data (no re-fetch needed)
3. If not exists (edge case/error recovery), fetches using get_owner_properties_tool
4. Caches in flow_state.owner_properties if fetched
5. Ensures booking flow always has property data without redundant API calls

Requirements: 5.2, 5.3, 5.4
"""

import asyncio
import sys
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.agent.nodes.booking.select_property import (
    _present_property_options,
    _process_property_selection
)
from app.agent.state.conversation_state import ConversationState


# Mock tools
async def mock_get_owner_properties(owner_profile_id: int):
    """Mock get_owner_properties tool"""
    return [
        {"id": 1, "name": "Property A", "address": "123 Main St", "city": "NYC"},
        {"id": 2, "name": "Property B", "address": "456 Oak Ave", "city": "LA"}
    ]


async def mock_get_property_details(property_id: int, owner_id=None):
    """Mock get_property_details tool"""
    properties = {
        1: {"id": 1, "name": "Property A", "address": "123 Main St", "city": "NYC"},
        2: {"id": 2, "name": "Property B", "address": "456 Oak Ave", "city": "LA"}
    }
    return properties.get(property_id)


MOCK_TOOLS = {
    "get_owner_properties": mock_get_owner_properties,
    "get_property_details": mock_get_property_details
}


async def test_cached_properties_used():
    """Test that cached properties from flow_state are used"""
    print("\n=== Test 1: Cached properties are used ===")
    
    # Setup state with cached properties in flow_state
    state = ConversationState(
        chat_id="test-123",
        user_id="user-1",
        owner_profile_id="owner-1",
        user_message="I want to book",
        flow_state={
            "owner_properties": [
                {"id": 1, "name": "Cached Property A", "address": "123 Main St", "city": "NYC"},
                {"id": 2, "name": "Cached Property B", "address": "456 Oak Ave", "city": "LA"}
            ]
        },
        bot_memory={"context": {}},
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
    
    # Call _present_property_options
    result = await _present_property_options(
        state=state,
        tools=MOCK_TOOLS,
        chat_id=state["chat_id"],
        flow_state=state["flow_state"],
        bot_memory=state["bot_memory"]
    )
    
    # Verify cached properties were used
    assert result["response_type"] == "button", "Should present buttons"
    assert len(result["response_metadata"]["buttons"]) == 2, "Should have 2 buttons"
    assert result["response_metadata"]["buttons"][0]["text"] == "Cached Property A", \
        "Should use cached property name"
    
    print("✓ Cached properties from flow_state were used")
    print(f"  - Buttons: {result['response_metadata']['buttons']}")
    return True


async def test_fetch_and_cache_when_missing():
    """Test that properties are fetched and cached when not in flow_state"""
    print("\n=== Test 2: Fetch and cache when missing ===")
    
    # Setup state without cached properties but with owner_profile_id
    state = ConversationState(
        chat_id="test-456",
        user_id="user-2",
        owner_profile_id="1",  # Valid owner profile ID
        user_message="I want to book",
        flow_state={},  # No cached properties
        bot_memory={"context": {}},  # No search results
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
    
    # Call _present_property_options
    result = await _present_property_options(
        state=state,
        tools=MOCK_TOOLS,
        chat_id=state["chat_id"],
        flow_state=state["flow_state"],
        bot_memory=state["bot_memory"]
    )
    
    # Verify properties were fetched and cached
    assert result["flow_state"].get("owner_properties") is not None, \
        "Properties should be cached in flow_state"
    assert len(result["flow_state"]["owner_properties"]) == 2, \
        "Should have 2 cached properties"
    assert result["response_type"] == "button", "Should present buttons"
    
    print("✓ Properties were fetched and cached in flow_state")
    print(f"  - Cached properties: {len(result['flow_state']['owner_properties'])}")
    print(f"  - Property names: {[p['name'] for p in result['flow_state']['owner_properties']]}")
    return True


async def test_use_search_results_fallback():
    """Test that search results are used as fallback"""
    print("\n=== Test 3: Use search results as fallback ===")
    
    # Setup state with search results but no cached properties
    state = ConversationState(
        chat_id="test-789",
        user_id="user-3",
        owner_profile_id="1",
        user_message="I want to book",
        flow_state={},  # No cached properties
        bot_memory={
            "context": {
                "last_search_results": ["1", "2"]  # Search results available
            }
        },
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
    
    # Call _present_property_options
    result = await _present_property_options(
        state=state,
        tools=MOCK_TOOLS,
        chat_id=state["chat_id"],
        flow_state=state["flow_state"],
        bot_memory=state["bot_memory"]
    )
    
    # Verify properties were fetched from search results and cached
    assert result["flow_state"].get("owner_properties") is not None, \
        "Properties should be cached in flow_state"
    assert result["response_type"] == "button", "Should present buttons"
    
    print("✓ Search results were used and properties cached")
    print(f"  - Cached properties: {len(result['flow_state']['owner_properties'])}")
    return True


async def test_no_redundant_fetch():
    """Test that no redundant fetch occurs when properties are cached"""
    print("\n=== Test 4: No redundant fetch with cached properties ===")
    
    fetch_count = 0
    
    async def counting_get_owner_properties(owner_profile_id: int):
        nonlocal fetch_count
        fetch_count += 1
        return await mock_get_owner_properties(owner_profile_id)
    
    tools_with_counter = {
        **MOCK_TOOLS,
        "get_owner_properties": counting_get_owner_properties
    }
    
    # Setup state with cached properties
    state = ConversationState(
        chat_id="test-999",
        user_id="user-4",
        owner_profile_id="1",
        user_message="I want to book",
        flow_state={
            "owner_properties": [
                {"id": 1, "name": "Cached Property", "address": "123 Main St", "city": "NYC"}
            ]
        },
        bot_memory={"context": {}},
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
    
    # Call _present_property_options
    result = await _present_property_options(
        state=state,
        tools=tools_with_counter,
        chat_id=state["chat_id"],
        flow_state=state["flow_state"],
        bot_memory=state["bot_memory"]
    )
    
    # Verify no fetch occurred
    assert fetch_count == 0, "Should not fetch when properties are cached"
    assert result["response_type"] == "button", "Should still present buttons"
    
    print("✓ No redundant fetch occurred with cached properties")
    print(f"  - Fetch count: {fetch_count}")
    return True


async def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Task 7.2 Verification: Reuse cached properties in booking flow")
    print("=" * 60)
    
    tests = [
        test_cached_properties_used,
        test_fetch_and_cache_when_missing,
        test_use_search_results_fallback,
        test_no_redundant_fetch
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
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ All tests passed! Task 7.2 implementation verified.")
        print("\nImplementation Summary:")
        print("- ✓ Checks flow_state.owner_properties for cached data")
        print("- ✓ Uses cached data when available (no re-fetch)")
        print("- ✓ Fetches and caches when not available")
        print("- ✓ Ensures no redundant API calls")
        print("\nRequirements validated: 5.2, 5.3, 5.4")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
