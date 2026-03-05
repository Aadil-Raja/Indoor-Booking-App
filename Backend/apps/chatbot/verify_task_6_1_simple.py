"""
Simple verification script for Task 6.1: Remove FAQ node from main graph.

This script verifies by inspecting the source code that:
1. FAQ node import is removed
2. FAQ node is not added to the graph
3. FAQ routing is removed from edges
4. Unknown intents route to information handler
"""

import os
import re


def verify_faq_removed():
    """Verify FAQ node is removed from main_graph.py."""
    print("=" * 70)
    print("Task 6.1 Verification: Remove FAQ node from main graph")
    print("=" * 70)
    
    # Read the main_graph.py file
    file_path = os.path.join(
        os.path.dirname(__file__),
        "app", "agent", "graphs", "main_graph.py"
    )
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\nTest 1: Verifying FAQ import is removed...")
    # Check that FAQ import is removed
    if "from app.agent.nodes.faq import faq_handler" in content:
        print("  ✗ FAILED: FAQ import still present")
        return False
    print("  ✓ FAQ import successfully removed")
    
    print("\nTest 2: Verifying FAQ node is not added to graph...")
    # Check that FAQ node is not added
    if 'graph.add_node("faq"' in content:
        print("  ✗ FAILED: FAQ node still added to graph")
        return False
    if "async def faq_node(state):" in content:
        print("  ✗ FAILED: FAQ node function still defined")
        return False
    print("  ✓ FAQ node successfully removed from graph")
    
    print("\nTest 3: Verifying FAQ edge is removed...")
    # Check that FAQ edge is removed
    if 'graph.add_edge("faq", END)' in content:
        print("  ✗ FAILED: FAQ edge still present")
        return False
    print("  ✓ FAQ edge successfully removed")
    
    print("\nTest 4: Verifying unknown intents route to information...")
    # Check that default routing is to information
    if 'next_node = state.get("next_node", "information")' not in content:
        print("  ✗ FAILED: Default routing not set to information")
        return False
    print("  ✓ Default routing correctly set to information")
    
    print("\nTest 5: Verifying routing function defaults to information...")
    # Check that invalid next_node routes to information
    if 'return "information"' not in content:
        print("  ✗ FAILED: Routing function doesn't return information for unknown")
        return False
    
    # Verify the comment mentions routing to information handler
    if "routing to information handler" not in content:
        print("  ✗ FAILED: Comment doesn't mention routing to information handler")
        return False
    print("  ✓ Unknown next_node correctly routes to information handler")
    
    print("\nTest 6: Verifying requirements are documented...")
    # Check that requirements 1.1, 1.2, 1.3 are mentioned
    if "1.1: Remove FAQ node" not in content:
        print("  ✗ FAILED: Requirement 1.1 not documented")
        return False
    if "1.2: Route FAQ-like queries" not in content:
        print("  ✗ FAILED: Requirement 1.2 not documented")
        return False
    if "1.3: Route all informational queries" not in content:
        print("  ✗ FAILED: Requirement 1.3 not documented")
        return False
    print("  ✓ Requirements 1.1, 1.2, 1.3 properly documented")
    
    print("\nTest 7: Verifying only valid nodes remain...")
    # Check that only greeting, information, and booking are in valid_nodes
    valid_nodes_match = re.search(
        r'valid_nodes\s*=\s*\[(.*?)\]',
        content,
        re.DOTALL
    )
    if valid_nodes_match:
        valid_nodes_str = valid_nodes_match.group(1)
        if "faq" in valid_nodes_str:
            print("  ✗ FAILED: 'faq' still in valid_nodes list")
            return False
        if '"greeting"' in valid_nodes_str and '"information"' in valid_nodes_str and '"booking"' in valid_nodes_str:
            print("  ✓ Only valid nodes (greeting, information, booking) remain")
        else:
            print("  ✗ FAILED: Expected nodes not found in valid_nodes")
            return False
    else:
        print("  ✗ FAILED: Could not find valid_nodes list")
        return False
    
    print("\nTest 8: Verifying conditional edges only include valid nodes...")
    # Check conditional edges
    conditional_edges_match = re.search(
        r'graph\.add_conditional_edges\((.*?)\)',
        content,
        re.DOTALL
    )
    if conditional_edges_match:
        edges_str = conditional_edges_match.group(1)
        if "faq" in edges_str:
            print("  ✗ FAILED: 'faq' still in conditional edges")
            return False
        print("  ✓ Conditional edges only include valid nodes")
    else:
        print("  ✗ FAILED: Could not find conditional edges")
        return False
    
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    print("\nSummary:")
    print("  1. FAQ import removed from main_graph.py")
    print("  2. FAQ node removed from graph")
    print("  3. FAQ edge removed from graph")
    print("  4. Unknown intents now route to information handler")
    print("  5. Requirements 1.1, 1.2, 1.3 properly documented")
    print("\nRequirements validated:")
    print("  - 1.1: Chatbot_Agent SHALL NOT include an FAQ node")
    print("  - 1.2: FAQ-like queries route to Information_Handler")
    print("  - 1.3: All informational queries route to Information_Handler")
    
    return True


if __name__ == "__main__":
    try:
        success = verify_faq_removed()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
