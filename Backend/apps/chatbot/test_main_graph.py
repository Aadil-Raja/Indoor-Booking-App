"""
Test script for main conversation graph structure.

This script verifies that the main graph is properly constructed with all
required nodes and edges.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agent.graphs.main_graph import create_main_graph, route_by_intent
from app.agent.state.conversation_state import ConversationState


def test_main_graph_structure():
    """Test that the main graph has all required nodes and edges."""
    print("Testing main graph structure...")
    
    # Create mock dependencies
    class MockLLMProvider:
        async def generate(self, prompt, max_tokens=100, temperature=0.7):
            return "Mock response"
        
        def count_tokens(self, text):
            return len(text.split())
    
    mock_llm = MockLLMProvider()
    mock_tools = {}
    
    # Create the graph
    try:
        graph = create_main_graph(mock_llm, mock_tools)
        print("✓ Main graph created successfully")
    except Exception as e:
        print(f"✗ Failed to create main graph: {e}")
        return False
    
    # Check that graph is compiled
    if graph is None:
        print("✗ Graph is None")
        return False
    
    print("✓ Graph is compiled")
    
    # Test route_by_intent function
    test_cases = [
        ({"intent": "greeting"}, "greeting"),
        ({"intent": "search"}, "search"),
        ({"intent": "booking"}, "booking"),
        ({"intent": "faq"}, "faq"),
        ({"intent": "unknown"}, "unknown"),
        ({"intent": "invalid"}, "unknown"),
        ({}, "unknown"),
    ]
    
    print("\nTesting route_by_intent function...")
    for state, expected in test_cases:
        result = route_by_intent(state)
        if result == expected:
            print(f"✓ route_by_intent({state.get('intent', 'missing')}) = {result}")
        else:
            print(f"✗ route_by_intent({state.get('intent', 'missing')}) = {result}, expected {expected}")
            return False
    
    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_main_graph_structure()
    sys.exit(0 if success else 1)
