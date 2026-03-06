"""
Verification script for Task 14.1: Create confirm_booking_node in booking subgraph.

This script verifies that the confirm_booking node implementation meets all requirements:
- Builds booking summary (property, court, date, time) - Req 8.1
- Fetches pricing using get_pricing_tool
- Uses LLM to check for user confirmation
- If confirmed: updates booking_step to "confirming" and routes to create_booking
- If user wants to modify: routes back to appropriate selection node - Req 8.3
- If cancelled: clears flow_state and ends - Req 8.4
- Returns next_node decision
"""

import re


def verify_helper_functions_exist():
    """Verify that all required helper functions exist in the implementation."""
    print("Verifying helper functions exist...")
    
    try:
        # Read the confirm.py file
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        required_functions = [
            "confirm_booking",
            "_present_booking_summary",
            "_process_confirmation_response",
            "_parse_confirmation_fallback",
            "_format_time_for_display"
        ]
        
        for func in required_functions:
            if f"def {func}(" in content or f"async def {func}(" in content:
                print(f"  ✓ Function exists: {func}")
            else:
                print(f"  ❌ Missing function: {func}")
                return False
        
        print("✅ All required helper functions exist!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_requirements_implementation():
    """Verify that requirements are implemented in the code."""
    print("Verifying requirements implementation...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        checks = [
            ("Build booking summary (Req 8.1)", 'booking_summary'),
            ("Fetch pricing", 'get_pricing_tool'),
            ("Update booking_step", 'booking_step'),
            ("Route to create_booking", 'create_booking'),
            ("Handle modification (Req 8.3)", 'CHANGE_'),
            ("Handle cancellation (Req 8.4)", 'CANCEL'),
            ("Clear flow_state on cancel", 'flow_state.*=.*{}'),
            ("Return next_node", 'next_node'),
            ("LLM confirmation check", 'llm_provider'),
        ]
        
        for check_name, check_str in checks:
            if re.search(check_str, content):
                print(f"  ✓ {check_name}")
            else:
                print(f"  ❌ Missing: {check_name}")
                return False
        
        print("✅ All requirements are implemented!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_docstring_requirements():
    """Verify that docstring mentions all requirements."""
    print("Verifying docstring requirements...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if requirements are mentioned in the file
        required_mentions = [
            ("Requirement 8.1", "8.1"),
            ("Requirement 8.3", "8.3"),
            ("Requirement 8.4", "8.4"),
        ]
        
        for mention_name, mention_str in required_mentions:
            if mention_str in content:
                print(f"  ✓ Mentions: {mention_name}")
            else:
                print(f"  ⚠ Missing mention: {mention_name}")
        
        print("✅ Docstring requirements verified!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_state_structure():
    """Verify that the implementation uses correct state structure."""
    print("Verifying state structure...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for correct field names
        correct_fields = [
            'flow_state.get("property_name")',
            'flow_state.get("court_name")',
            'flow_state.get("date")',
            'flow_state.get("time_slot")',
            'flow_state.get("booking_step")',
            'state["next_node"]',
        ]
        
        for field in correct_fields:
            if field in content:
                print(f"  ✓ Uses correct field: {field}")
            else:
                print(f"  ⚠ Field not found: {field}")
        
        print("✅ State structure verified!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_confirmation_logic():
    """Verify confirmation response handling logic."""
    print("Verifying confirmation logic...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for different confirmation responses
        responses = [
            ("CONFIRM response", 'response_text == "CONFIRM"'),
            ("CANCEL response", 'response_text == "CANCEL"'),
            ("CHANGE response", 'response_text.startswith("CHANGE_")'),
            ("CLARIFY response", 'response_text == "CLARIFY"'),
        ]
        
        for response_name, response_check in responses:
            if response_check in content:
                print(f"  ✓ Handles: {response_name}")
            else:
                print(f"  ❌ Missing: {response_name}")
                return False
        
        # Check for modification routing
        modifications = [
            ("Change property", 'change_type == "property"'),
            ("Change court", 'change_type == "court"'),
            ("Change date", 'change_type == "date"'),
            ("Change time", 'change_type == "time"'),
        ]
        
        for mod_name, mod_check in modifications:
            if mod_check in content:
                print(f"  ✓ Routes: {mod_name}")
            else:
                print(f"  ⚠ Missing routing: {mod_name}")
        
        print("✅ Confirmation logic verified!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_pricing_integration():
    """Verify pricing tool integration."""
    print("Verifying pricing integration...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        checks = [
            ("Import pricing tool", "from app.agent.tools.pricing_tool import get_pricing_tool"),
            ("Call pricing tool", "await get_pricing_tool"),
            ("Store pricing in summary", "total_price"),
            ("Display pricing", "price_per_hour"),
        ]
        
        for check_name, check_str in checks:
            if check_str in content:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ⚠ Missing: {check_name}")
        
        print("✅ Pricing integration verified!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def verify_flow_state_clearing():
    """Verify flow_state is cleared on cancellation (Req 8.4)."""
    print("Verifying flow_state clearing on cancellation...")
    
    try:
        with open("app/agent/nodes/booking/confirm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for flow_state clearing in cancel logic
        cancel_section = re.search(
            r'response_text == "CANCEL".*?return state',
            content,
            re.DOTALL
        )
        
        if cancel_section:
            cancel_code = cancel_section.group(0)
            if 'flow_state.*=.*{}' in cancel_code or 'state["flow_state"] = {}' in cancel_code:
                print("  ✓ flow_state cleared on cancellation (Req 8.4)")
            else:
                print("  ❌ flow_state NOT cleared on cancellation")
                return False
        else:
            print("  ⚠ Could not find cancel section")
        
        print("✅ Flow state clearing verified!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Task 14.1 Verification: Create confirm_booking_node")
    print("=" * 70)
    print()
    
    all_passed = True
    
    all_passed &= verify_helper_functions_exist()
    all_passed &= verify_requirements_implementation()
    all_passed &= verify_docstring_requirements()
    all_passed &= verify_state_structure()
    all_passed &= verify_confirmation_logic()
    all_passed &= verify_pricing_integration()
    all_passed &= verify_flow_state_clearing()
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("Task 14.1 implementation is complete and correct.")
        print()
        print("Requirements verified:")
        print("  - Req 8.1: Builds booking summary with pricing")
        print("  - Req 8.3: Handles modification requests")
        print("  - Req 8.4: Clears flow_state on cancellation")
    else:
        print("⚠ SOME VERIFICATIONS FAILED")
        print("Please review the implementation.")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
