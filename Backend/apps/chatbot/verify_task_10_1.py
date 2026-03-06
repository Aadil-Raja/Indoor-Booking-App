"""
Verification script for Task 10.1: Create select_court_node in booking subgraph

This script verifies that:
1. Court selection is skipped when court_id exists in flow_state
2. Courts are fetched for selected property using get_property_courts_tool
3. Single court is auto-selected and stored in flow_state
4. Multiple courts are presented as options
5. Error handling for no courts available
6. Error handling for missing property_id
7. booking_step is updated to "court_selected" when complete

Requirements: 7.2, 8.2, 14.1, 14.2, 14.3
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
    "select_court_module",
    os.path.join(chatbot_dir, "app", "agent", "nodes", "booking", "select_court.py")
)
select_court_module = importlib.util.module_from_spec(spec)

# Mock the get_property_courts_tool before loading the module
async def mock_get_property_courts(property_id: int, owner_id=None):
    """Mock get_property_courts tool"""
    if property_id == 1:
        return [
            {"id": 1, "name": "Court A", "sport_type": "Tennis", "surface_type": "Hard"},
            {"id": 2, "name": "Court B", "sport_type": "Basketball", "surface_type": "Wood"}
        ]
    elif property_id == 2:
        return [
            {"id": 3, "name": "Single Court", "sport_type": "Futsal", "surface_type": "Turf"}
        ]
    elif property_id == 3:
        return []  # No courts
    return []

# Patch the import in the module
import unittest.mock
with unittest.mock.patch.dict('sys.modules', {
    'app.agent.tools.court_tool': unittest.mock.MagicMock(
        get_property_courts_tool=mock_get_property_courts
    )
}):
    spec.loader.exec_module(select_court_module)

select_court = select_court_module.select_court

# Now replace the tool function in the loaded module
select_court_module.get_property_courts_tool = mock_get_property_courts

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


async def test_skip_when_court_already_selected():
    """Test that court selection is skipped when court_id exists in flow_state"""
    print("\n=== Test 1: Skip when court already selected ===")
    
    # Setup state with court already selected
    state = ConversationState(
        chat_id="test-123",
        user_id="user-1",
        owner_profile_id="owner-1",
        user_message="I want to book",
        flow_state={
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 1,
            "court_name": "Court A"
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify court selection was skipped (Requirement 7.2)
    assert result["next_node"] == "select_date", \
        f"Expected next_node='select_date', got '{result.get('next_node')}'"
    assert result["flow_state"]["court_id"] == 1, \
        "Court ID should remain unchanged"
    assert result["flow_state"]["court_name"] == "Court A", \
        "Court name should remain unchanged"
    
    print("✓ Court selection skipped when already selected (Requirement 7.2)")
    print(f"  - Court ID: {result['flow_state']['court_id']}")
    print(f"  - Court Name: {result['flow_state']['court_name']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_auto_select_single_court():
    """Test that single court is auto-selected and stored in flow_state"""
    print("\n=== Test 2: Auto-select single court ===")
    
    # Setup state with property that has single court
    state = ConversationState(
        chat_id="test-456",
        user_id="user-2",
        owner_profile_id="2",
        user_message="I want to book",
        flow_state={
            "property_id": 2,
            "property_name": "Small Facility"
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify single court was auto-selected (Requirements 14.1, 14.2, 14.3)
    assert result["flow_state"]["court_id"] == 3, \
        f"Expected court_id=3, got {result['flow_state'].get('court_id')}"
    assert result["flow_state"]["court_name"] == "Single Court", \
        f"Expected court_name='Single Court', got {result['flow_state'].get('court_name')}"
    assert result["flow_state"]["booking_step"] == "court_selected", \
        f"Expected booking_step='court_selected', got {result['flow_state'].get('booking_step')}"
    assert result["next_node"] == "select_date", \
        f"Expected next_node='select_date', got {result.get('next_node')}"
    
    print("✓ Single court auto-selected successfully")
    print(f"  - Court ID: {result['flow_state']['court_id']}")
    print(f"  - Court Name: {result['flow_state']['court_name']}")
    print(f"  - Booking Step: {result['flow_state']['booking_step']} (Requirement 8.2)")
    print(f"  - Next node: {result['next_node']}")
    print("  - Requirements validated: 14.1, 14.2, 14.3, 8.2")
    return True


async def test_present_multiple_courts():
    """Test that multiple courts are presented as options"""
    print("\n=== Test 3: Present multiple courts ===")
    
    # Setup state with property that has multiple courts
    state = ConversationState(
        chat_id="test-789",
        user_id="user-3",
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify multiple courts are presented (Requirement 14.3)
    assert result["response_type"] == "button", \
        f"Expected response_type='button', got '{result.get('response_type')}'"
    assert "buttons" in result["response_metadata"], \
        "Expected buttons in response_metadata"
    assert len(result["response_metadata"]["buttons"]) == 2, \
        f"Expected 2 buttons, got {len(result['response_metadata']['buttons'])}"
    assert result["flow_state"]["booking_step"] == "awaiting_court_selection", \
        f"Expected booking_step='awaiting_court_selection', got {result['flow_state'].get('booking_step')}"
    assert result["next_node"] == "wait_for_selection", \
        f"Expected next_node='wait_for_selection', got {result.get('next_node')}"
    
    # Verify buttons contain court information
    buttons = result["response_metadata"]["buttons"]
    button_texts = [b["text"] for b in buttons]
    assert any("Court A" in text for text in button_texts), \
        "Expected 'Court A' in button texts"
    assert any("Court B" in text for text in button_texts), \
        "Expected 'Court B' in button texts"
    
    print("✓ Multiple courts presented as options (Requirement 14.3)")
    print(f"  - Response type: {result['response_type']}")
    print(f"  - Number of buttons: {len(buttons)}")
    print(f"  - Button texts: {button_texts}")
    print(f"  - Booking step: {result['flow_state']['booking_step']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_no_courts_available():
    """Test error handling when no courts are available"""
    print("\n=== Test 4: No courts available ===")
    
    # Setup state with property that has no courts
    state = ConversationState(
        chat_id="test-999",
        user_id="user-4",
        owner_profile_id="3",
        user_message="I want to book",
        flow_state={
            "property_id": 3,
            "property_name": "Empty Facility"
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify error handling
    assert result["response_type"] == "text", \
        f"Expected response_type='text', got '{result.get('response_type')}'"
    assert "doesn't have any courts" in result["response_content"].lower(), \
        "Expected error message about no courts"
    assert result["next_node"] == "end", \
        f"Expected next_node='end', got {result.get('next_node')}"
    
    print("✓ No courts error handled correctly")
    print(f"  - Response: {result['response_content']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_missing_property_id():
    """Test error handling when property_id is missing"""
    print("\n=== Test 5: Missing property_id ===")
    
    # Setup state without property_id
    state = ConversationState(
        chat_id="test-111",
        user_id="user-5",
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify error handling
    assert result["response_type"] == "text", \
        f"Expected response_type='text', got '{result.get('response_type')}'"
    assert "select a property first" in result["response_content"].lower(), \
        "Expected error message about missing property"
    assert result["next_node"] == "select_property", \
        f"Expected next_node='select_property', got {result.get('next_node')}"
    
    print("✓ Missing property_id error handled correctly")
    print(f"  - Response: {result['response_content']}")
    print(f"  - Next node: {result['next_node']}")
    return True


async def test_court_buttons_include_sport_type():
    """Test that court buttons include sport type information"""
    print("\n=== Test 6: Court buttons include sport type ===")
    
    # Setup state with property that has multiple courts
    state = ConversationState(
        chat_id="test-222",
        user_id="user-6",
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
    
    # Call select_court
    result = await select_court(state, MOCK_TOOLS)
    
    # Verify buttons include sport type
    buttons = result["response_metadata"]["buttons"]
    button_texts = [b["text"] for b in buttons]
    
    assert any("Tennis" in text for text in button_texts), \
        "Expected 'Tennis' sport type in button texts"
    assert any("Basketball" in text for text in button_texts), \
        "Expected 'Basketball' sport type in button texts"
    
    print("✓ Court buttons include sport type information")
    print(f"  - Button texts: {button_texts}")
    return True


async def main():
    """Run all verification tests"""
    print("=" * 70)
    print("Task 10.1 Verification: Create select_court_node in booking subgraph")
    print("=" * 70)
    
    tests = [
        test_skip_when_court_already_selected,
        test_auto_select_single_court,
        test_present_multiple_courts,
        test_no_courts_available,
        test_missing_property_id,
        test_court_buttons_include_sport_type
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
        print("\n✓ All tests passed! Task 10.1 implementation verified.")
        print("\nImplementation Summary:")
        print("- ✓ Skips court selection when court_id exists in flow_state (Req 7.2)")
        print("- ✓ Fetches courts for selected property using get_property_courts_tool")
        print("- ✓ Auto-selects single court and stores in flow_state (Req 14.1, 14.2)")
        print("- ✓ Presents multiple courts as button options (Req 14.3)")
        print("- ✓ Updates booking_step to 'court_selected' when complete (Req 8.2)")
        print("- ✓ Handles error when no courts available")
        print("- ✓ Handles error when property_id is missing")
        print("- ✓ Includes sport type in court button labels")
        print("\nRequirements validated: 7.2, 8.2, 14.1, 14.2, 14.3")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
