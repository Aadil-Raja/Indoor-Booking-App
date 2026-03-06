"""
Verification script for Task 17.1: Remove rule-based routing from main_graph.py

This script verifies that:
1. No route_by_intent function exists
2. No conditional_edges based on intent exist
3. intent_detection returns next_node from LLM
4. Routing is based on LLM's next_node decision
"""

import re
import sys
from pathlib import Path

def verify_task_17_1():
    """Verify task 17.1 implementation."""
    print("=" * 80)
    print("Task 17.1 Verification: Remove rule-based routing from main_graph.py")
    print("=" * 80)
    
    # Read main_graph.py
    main_graph_path = Path("apps/chatbot/app/agent/graphs/main_graph.py")
    if not main_graph_path.exists():
        print(f"❌ FAILED: {main_graph_path} not found")
        return False
    
    with open(main_graph_path, 'r', encoding='utf-8') as f:
        main_graph_content = f.read()
    
    # Read intent_detection.py
    intent_detection_path = Path("apps/chatbot/app/agent/nodes/intent_detection.py")
    if not intent_detection_path.exists():
        print(f"❌ FAILED: {intent_detection_path} not found")
        return False
    
    with open(intent_detection_path, 'r', encoding='utf-8') as f:
        intent_detection_content = f.read()
    
    all_passed = True
    
    # Test 1: Verify no route_by_intent function exists
    print("\n1. Checking for route_by_intent function...")
    if "route_by_intent" in main_graph_content:
        print("   ❌ FAILED: route_by_intent function still exists")
        all_passed = False
    else:
        print("   ✓ PASSED: No route_by_intent function found")
    
    # Test 2: Verify route_by_next_node function exists
    print("\n2. Checking for route_by_next_node function...")
    if "def route_by_next_node" in main_graph_content:
        print("   ✓ PASSED: route_by_next_node function exists")
    else:
        print("   ❌ FAILED: route_by_next_node function not found")
        all_passed = False
    
    # Test 3: Verify conditional_edges uses route_by_next_node
    print("\n3. Checking conditional_edges uses route_by_next_node...")
    if re.search(r'graph\.add_conditional_edges\([^)]*route_by_next_node', main_graph_content, re.DOTALL):
        print("   ✓ PASSED: conditional_edges uses route_by_next_node")
    else:
        print("   ❌ FAILED: conditional_edges does not use route_by_next_node")
        all_passed = False
    
    # Test 4: Verify no rule-based keyword matching in intent_detection
    print("\n4. Checking for rule-based keyword matching...")
    rule_based_patterns = [
        r'if\s+["\']book["\'].*in.*message',
        r'if\s+["\']search["\'].*in.*message',
        r'if\s+["\']faq["\'].*in.*message',
        r'keyword.*match',
        r'pattern.*match'
    ]
    
    found_rule_based = False
    for pattern in rule_based_patterns:
        if re.search(pattern, intent_detection_content, re.IGNORECASE):
            print(f"   ❌ FAILED: Found rule-based pattern: {pattern}")
            found_rule_based = True
            all_passed = False
    
    if not found_rule_based:
        print("   ✓ PASSED: No rule-based keyword matching found")
    
    # Test 5: Verify intent_detection sets next_node in state
    print("\n5. Checking intent_detection sets next_node...")
    if 'state["next_node"]' in intent_detection_content or "state['next_node']" in intent_detection_content:
        print("   ✓ PASSED: intent_detection sets next_node in state")
    else:
        print("   ❌ FAILED: intent_detection does not set next_node")
        all_passed = False
    
    # Test 6: Verify LLM is used for routing decision
    print("\n6. Checking LLM is used for routing decision...")
    if "llm" in intent_detection_content.lower() and "ainvoke" in intent_detection_content:
        print("   ✓ PASSED: LLM is used for routing decision")
    else:
        print("   ❌ FAILED: LLM not used for routing decision")
        all_passed = False
    
    # Test 7: Verify route_by_next_node reads next_node from state
    print("\n7. Checking route_by_next_node reads next_node from state...")
    if 'state.get("next_node"' in main_graph_content or "state.get('next_node'" in main_graph_content:
        print("   ✓ PASSED: route_by_next_node reads next_node from state")
    else:
        print("   ❌ FAILED: route_by_next_node does not read next_node from state")
        all_passed = False
    
    # Test 8: Verify valid routing targets
    print("\n8. Checking valid routing targets...")
    routing_targets = ["greeting", "information", "booking"]
    all_targets_found = True
    for target in routing_targets:
        if f'"{target}": "{target}"' in main_graph_content or f"'{target}': '{target}'" in main_graph_content:
            print(f"   ✓ Found routing target: {target}")
        else:
            print(f"   ❌ Missing routing target: {target}")
            all_targets_found = False
            all_passed = False
    
    if all_targets_found:
        print("   ✓ PASSED: All routing targets found")
    
    # Test 9: Verify no FAQ routing
    print("\n9. Checking no FAQ routing...")
    if '"faq"' in main_graph_content or "'faq'" in main_graph_content:
        # Check if it's in a comment or string
        faq_matches = re.finditer(r'["\']faq["\']', main_graph_content)
        in_code = False
        for match in faq_matches:
            # Simple check: if it's in a routing dict, it's in code
            context = main_graph_content[max(0, match.start()-50):match.end()+50]
            if ":" in context and not context.strip().startswith("#"):
                in_code = True
                break
        
        if in_code:
            print("   ❌ FAILED: FAQ routing still exists")
            all_passed = False
        else:
            print("   ✓ PASSED: No FAQ routing in code (only in comments)")
    else:
        print("   ✓ PASSED: No FAQ routing found")
    
    # Test 10: Verify parse_llm_response is used
    print("\n10. Checking parse_llm_response is used...")
    if "parse_llm_response" in intent_detection_content:
        print("   ✓ PASSED: parse_llm_response is used")
    else:
        print("   ❌ FAILED: parse_llm_response not used")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED - Task 17.1 is complete!")
        print("\nSummary:")
        print("- No rule-based routing logic found")
        print("- LLM-based routing is implemented")
        print("- intent_detection returns next_node from LLM")
        print("- Routing is based on LLM's next_node decision")
    else:
        print("❌ SOME TESTS FAILED - Task 17.1 needs attention")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = verify_task_17_1()
    sys.exit(0 if success else 1)
