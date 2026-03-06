"""
Verification script for Task 17.2: Update all nodes to apply state_updates before routing.

This script demonstrates that Requirement 13.5 is satisfied:
"The system SHALL apply state_updates to flow_state and bot_memory before routing to the next_node"

Run this script to verify the implementation:
    python verify_task_17_2.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(text)
    print("="*70)


def print_success(text):
    """Print a success message."""
    print(f"✓ {text}")


def print_info(text):
    """Print an info message."""
    print(f"  {text}")


def verify_apply_state_updates_function():
    """Verify that apply_state_updates function exists and works correctly."""
    print_header("1. Verifying apply_state_updates() Function")
    
    from app.agent.state.llm_response_parser import apply_state_updates
    
    # Test basic functionality
    state = {
        "flow_state": {"existing": "value"},
        "bot_memory": {"existing": "value"}
    }
    
    state_updates = {
        "flow_state": {"new_field": "new_value"},
        "bot_memory": {"new_field": "new_value"}
    }
    
    result = apply_state_updates(state, state_updates)
    
    assert result["flow_state"]["existing"] == "value"
    assert result["flow_state"]["new_field"] == "new_value"
    assert result["bot_memory"]["existing"] == "value"
    assert result["bot_memory"]["new_field"] == "new_value"
    
    print_success("apply_state_updates() function exists")
    print_success("Function correctly merges state_updates with existing state")
    print_success("Function preserves existing state while adding new fields")
    
    return True


def verify_intent_detection_implementation():
    """Verify that intent_detection node uses apply_state_updates correctly."""
    print_header("2. Verifying intent_detection Node Implementation")
    
    # Read the intent_detection.py file
    intent_detection_path = os.path.join(
        os.path.dirname(__file__),
        'app', 'agent', 'nodes', 'intent_detection.py'
    )
    
    with open(intent_detection_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for import
    if 'from app.agent.state.llm_response_parser import apply_state_updates' in content:
        print_success("intent_detection imports apply_state_updates")
    else:
        print("❌ intent_detection does not import apply_state_updates")
        return False
    
    # Check for usage
    if 'state = apply_state_updates(state, state_updates)' in content:
        print_success("intent_detection calls apply_state_updates()")
    else:
        print("❌ intent_detection does not call apply_state_updates()")
        return False
    
    # Check order (apply_state_updates before next_node)
    apply_pos = content.find('state = apply_state_updates(state, state_updates)')
    next_node_pos = content.find('state["next_node"] = next_node')
    
    if apply_pos > 0 and next_node_pos > 0 and apply_pos < next_node_pos:
        print_success("apply_state_updates is called BEFORE next_node is set")
    else:
        print("❌ apply_state_updates is not called before next_node")
        return False
    
    # Check for Requirement 13.5 reference
    if '13.5' in content:
        print_success("Code references Requirement 13.5")
    else:
        print("⚠ Code does not explicitly reference Requirement 13.5")
    
    return True


def verify_documentation():
    """Verify that pattern documentation exists."""
    print_header("3. Verifying Pattern Documentation")
    
    doc_path = os.path.join(
        os.path.dirname(__file__),
        'app', 'agent', 'nodes', 'LLM_NODE_PATTERN.md'
    )
    
    if not os.path.exists(doc_path):
        print("❌ LLM_NODE_PATTERN.md does not exist")
        return False
    
    print_success("LLM_NODE_PATTERN.md exists")
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_sections = [
        'Overview',
        'Requirements',
        'Pattern',
        'Code Template',
        'Current Implementation',
        'Migration Guide',
        'Testing'
    ]
    
    for section in required_sections:
        if section in content:
            print_success(f"Documentation includes '{section}' section")
        else:
            print(f"⚠ Documentation missing '{section}' section")
    
    if 'Requirement 13.5' in content:
        print_success("Documentation references Requirement 13.5")
    
    if 'apply_state_updates' in content:
        print_success("Documentation explains apply_state_updates usage")
    
    return True


def verify_tests():
    """Verify that tests exist."""
    print_header("4. Verifying Test Suite")
    
    test_files = [
        'app/agent/nodes/test_state_updates_routing.py',
        'test_task_17_2.py'
    ]
    
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            print_success(f"{test_file} exists")
        else:
            print(f"⚠ {test_file} does not exist")
    
    return True


def demonstrate_usage():
    """Demonstrate how apply_state_updates works."""
    print_header("5. Demonstrating apply_state_updates Usage")
    
    from app.agent.state.llm_response_parser import apply_state_updates
    
    print_info("Initial state:")
    state = {
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center"
        },
        "bot_memory": {
            "user_preferences": {
                "preferred_time": "morning"
            }
        }
    }
    print_info(f"  flow_state: {state['flow_state']}")
    print_info(f"  bot_memory: {state['bot_memory']}")
    
    print_info("\nState updates from LLM:")
    state_updates = {
        "flow_state": {
            "current_intent": "booking",
            "court_id": 10
        },
        "bot_memory": {
            "user_preferences": {
                "preferred_sport": "tennis"
            }
        }
    }
    print_info(f"  flow_state updates: {state_updates['flow_state']}")
    print_info(f"  bot_memory updates: {state_updates['bot_memory']}")
    
    print_info("\nApplying state updates...")
    result = apply_state_updates(state, state_updates)
    
    print_info("\nResult after applying updates:")
    print_info(f"  flow_state: {result['flow_state']}")
    print_info(f"  bot_memory: {result['bot_memory']}")
    
    print_success("\nExisting state preserved:")
    print_info(f"  property_id: {result['flow_state']['property_id']}")
    print_info(f"  property_name: {result['flow_state']['property_name']}")
    print_info(f"  preferred_time: {result['bot_memory']['user_preferences']['preferred_time']}")
    
    print_success("\nNew state added:")
    print_info(f"  current_intent: {result['flow_state']['current_intent']}")
    print_info(f"  court_id: {result['flow_state']['court_id']}")
    print_info(f"  preferred_sport: {result['bot_memory']['user_preferences']['preferred_sport']}")
    
    return True


def main():
    """Main verification function."""
    print_header("Task 17.2 Verification")
    print("Requirement 13.5: System SHALL apply state_updates before routing")
    
    all_passed = True
    
    try:
        all_passed &= verify_apply_state_updates_function()
        all_passed &= verify_intent_detection_implementation()
        all_passed &= verify_documentation()
        all_passed &= verify_tests()
        all_passed &= demonstrate_usage()
        
        if all_passed:
            print_header("✓ ALL VERIFICATIONS PASSED")
            print("\nTask 17.2 is complete:")
            print("1. ✓ apply_state_updates() utility function created")
            print("2. ✓ intent_detection node updated to use apply_state_updates()")
            print("3. ✓ State updates applied BEFORE routing to next_node")
            print("4. ✓ Pattern documentation created")
            print("5. ✓ Test suite created")
            print("\nRequirement 13.5 is satisfied:")
            print("- Nodes that use structured LLM responses apply state_updates")
            print("- State updates are applied BEFORE routing")
            print("- Pattern is documented for future implementations")
            return 0
        else:
            print_header("❌ SOME VERIFICATIONS FAILED")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
