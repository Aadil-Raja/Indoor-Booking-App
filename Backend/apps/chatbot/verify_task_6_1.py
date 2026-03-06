"""
Verification script for Task 6.1: Remove FAQ node from main graph.

This script verifies that:
1. FAQ node is removed from the main graph
2. FAQ routing is removed from conditional edges
3. Unknown intents route to information handler
"""

import sys
import os

# Add the Backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock, AsyncMock
from app.agent.graphs.main_graph import create_main_graph, route_by_next_node
from app.agent.state.conversation_state import ConversationState


def test_faq_node_removed():
    """Verify FAQ node is not in the graph."""
    print("Test 1: Verifying FAQ node is removed from graph...")
    
    # Create mock dependencies
    mock_llm = Mock()
    mock_tools = {}
    
    # Create the graph
    graph = create_main_graph(mock_llm, mock_tools)
    
    # Get the graph nodes
    nodes = list(graph.nodes.keys())
    
    print(f"  Graph nodes: {nodes}")
    
    # Verify FAQ is not in nodes
    assert "faq" not in nodes, "FAQ node should be removed from graph"
    
    # Verify expected nodes are present
    expected_nodes = ["greeting", "information", "booking"]
    for node in expected_nodes:
        assert node in nodes, f"Expected node '{node}' should be in graph"
    
    print("  ✓ FAQ node successfully removed")
    print("  ✓ Expected nodes (greeting, information, booking) are present")
    return True


def test_unknown_intent_routes_to_information():
    """Verify unknown intents route to information handler."""
    print("\nTest 2: Verifying unknown intents route to information handler...")
    
    # Test with missing next_node
    state1: ConversationState = {
        "chat_id": "test-123",
        "user_id": "user-456",
        "owner_profile_id": "owner-789",
        "user_message": "test",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": None,
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    result1 = route_by_next_node(state1)
    print(f"  Missing next_node routes to: {result1}")
    assert result1 == "information", "Missing next_node should route to information"
    
    # Test with invalid next_node
    state2 = state1.copy()
    state2["next_node"] = "invalid_node"
    
    result2 = route_by_next_node(state2)
    print(f"  Invalid next_node routes to: {result2}")
    assert result2 == "information", "Invalid next_node should route to information"
    
    # Test with "faq" next_node (should route to information)
    state3 = state1.copy()
    state3["next_node"] = "faq"
    
    result3 = route_by_next_node(state3)
    print(f"  'faq' next_node routes to: {result3}")
    assert result3 == "information", "'faq' next_node should route to information"
    
    print("  ✓ Unknown intents correctly route to information handler")
    return True


def test_valid_routing():
    """Verify valid next_node values route correctly."""
    print("\nTest 3: Verifying valid routing decisions...")
    
    base_state: ConversationState = {
        "chat_id": "test-123",
        "user_id": "user-456",
        "owner_profile_id": "owner-789",
        "user_message": "test",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": None,
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Test greeting routing
    state1 = base_state.copy()
    state1["next_node"] = "greeting"
    result1 = route_by_next_node(state1)
    print(f"  'greeting' next_node routes to: {result1}")
    assert result1 == "greeting", "greeting should route to greeting"
    
    # Test information routing
    state2 = base_state.copy()
    state2["next_node"] = "information"
    result2 = route_by_next_node(state2)
    print(f"  'information' next_node routes to: {result2}")
    assert result2 == "information", "information should route to information"
    
    # Test booking routing
    state3 = base_state.copy()
    state3["next_node"] = "booking"
    result3 = route_by_next_node(state3)
    print(f"  'booking' next_node routes to: {result3}")
    assert result3 == "booking", "booking should route to booking"
    
    print("  ✓ Valid routing decisions work correctly")
    return True


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("Task 6.1 Verification: Remove FAQ node from main graph")
    print("=" * 70)
    
    try:
        # Run tests
        test_faq_node_removed()
        test_unknown_intent_routes_to_information()
        test_valid_routing()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        print("\nSummary:")
        print("  1. FAQ node successfully removed from graph")
        print("  2. FAQ routing removed from conditional edges")
        print("  3. Unknown intents now route to information handler")
        print("\nRequirements validated:")
        print("  - 1.1: Chatbot_Agent SHALL NOT include an FAQ node")
        print("  - 1.2: FAQ-like queries route to Information_Handler")
        print("  - 1.3: All informational queries route to Information_Handler")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
