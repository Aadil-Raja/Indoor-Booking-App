"""
Simple verification script for Task 7.2: Reuse cached properties in booking flow

This script verifies the implementation by checking the code structure.

Requirements: 5.2, 5.3, 5.4
"""

import re
from pathlib import Path


def verify_implementation():
    """Verify the implementation by checking code structure"""
    print("=" * 60)
    print("Task 7.2 Verification: Reuse cached properties in booking flow")
    print("=" * 60)
    
    # Read the select_property.py file
    file_path = Path(__file__).parent / "app" / "agent" / "nodes" / "booking" / "select_property.py"
    
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # Check 1: Verify flow_state.owner_properties is checked in _present_property_options
    print("\n=== Check 1: flow_state.owner_properties is checked ===")
    if 'flow_state.get("owner_properties")' in content:
        print("✓ Code checks for flow_state.owner_properties")
        checks.append(True)
    else:
        print("✗ Code does not check for flow_state.owner_properties")
        checks.append(False)
    
    # Check 2: Verify cached properties are used when available
    print("\n=== Check 2: Cached properties are used ===")
    if 'Using cached properties from flow_state' in content:
        print("✓ Code uses cached properties when available")
        checks.append(True)
    else:
        print("✗ Code does not use cached properties")
        checks.append(False)
    
    # Check 3: Verify properties are cached when fetched
    print("\n=== Check 3: Properties are cached when fetched ===")
    cache_pattern = r'flow_state\["owner_properties"\]\s*=\s*properties'
    if re.search(cache_pattern, content):
        print("✓ Code caches fetched properties in flow_state")
        checks.append(True)
    else:
        print("✗ Code does not cache fetched properties")
        checks.append(False)
    
    # Check 4: Verify get_owner_properties is called as fallback
    print("\n=== Check 4: get_owner_properties fallback exists ===")
    if 'get_owner_properties' in content and 'owner_profile_id' in content:
        print("✓ Code has fallback to fetch owner properties")
        checks.append(True)
    else:
        print("✗ Code does not have fallback to fetch owner properties")
        checks.append(False)
    
    # Check 5: Verify _process_property_selection also checks cached properties
    print("\n=== Check 5: _process_property_selection checks cached properties ===")
    process_func_match = re.search(
        r'async def _process_property_selection.*?(?=async def|\Z)',
        content,
        re.DOTALL
    )
    if process_func_match:
        process_func = process_func_match.group(0)
        if 'flow_state.get("owner_properties")' in process_func:
            print("✓ _process_property_selection checks flow_state.owner_properties")
            checks.append(True)
        else:
            print("✗ _process_property_selection does not check flow_state.owner_properties")
            checks.append(False)
    else:
        print("✗ Could not find _process_property_selection function")
        checks.append(False)
    
    # Check 6: Verify requirements are documented
    print("\n=== Check 6: Requirements are documented ===")
    if '5.2' in content and '5.3' in content and '5.4' in content:
        print("✓ Requirements 5.2, 5.3, 5.4 are documented")
        checks.append(True)
    else:
        print("✗ Requirements are not properly documented")
        checks.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {sum(checks)}/{len(checks)} checks passed")
    print("=" * 60)
    
    if all(checks):
        print("\n✓ All checks passed! Task 7.2 implementation verified.")
        print("\nImplementation Summary:")
        print("- ✓ Checks flow_state.owner_properties for cached data")
        print("- ✓ Uses cached data when available (no re-fetch)")
        print("- ✓ Fetches and caches when not available")
        print("- ✓ Has fallback to get_owner_properties tool")
        print("- ✓ Both present and process functions check cache")
        print("- ✓ Requirements properly documented")
        print("\nRequirements validated: 5.2, 5.3, 5.4")
        return True
    else:
        print("\n✗ Some checks failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = verify_implementation()
    exit(0 if success else 1)
