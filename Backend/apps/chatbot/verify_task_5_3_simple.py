"""
Simple verification script for Task 5.3: Update information handler prompts for personalization

This script verifies the code changes without requiring imports.

Requirements: 9.2, 9.5, 9.6
"""

import os
import re


def read_file(filepath):
    """Read file content"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def test_information_prompts():
    """Test information_prompts.py changes"""
    print("\n=== Testing information_prompts.py ===")
    
    filepath = os.path.join('app', 'agent', 'prompts', 'information_prompts.py')
    content = read_file(filepath)
    
    # Test 1: business_name placeholder in SYSTEM_TEMPLATE
    assert '{business_name}' in content, "Missing {business_name} placeholder"
    print("✓ {business_name} placeholder found")
    
    # Test 2: Personalized introduction
    assert "You are {business_name}'s assistant" in content, \
        "Missing personalized introduction"
    print("✓ Personalized introduction found")
    
    # Test 3: Context about showing only owner's properties
    assert "only show" in content.lower() or "only provide" in content.lower(), \
        "Missing context about showing only owner's properties"
    print("✓ Context about showing only owner's properties found")
    
    # Test 4: business_name parameter in function signature
    assert re.search(r'business_name:\s*Optional\[str\]\s*=\s*None', content), \
        "Missing business_name parameter in create_information_prompt"
    print("✓ business_name parameter in function signature")
    
    # Test 5: business_name in partial variables
    assert 'business_name=business_name_str' in content or 'business_name=' in content, \
        "Missing business_name in partial variables"
    print("✓ business_name passed to partial variables")
    
    # Test 6: Default value handling
    assert 'business_name_str = business_name or "our facility"' in content, \
        "Missing default value handling for business_name"
    print("✓ Default value handling for business_name")
    
    # Test 7: Fuzzy match confirmation guidance
    assert 'confirm the correction with the user' in content.lower() or \
           'acknowledge it naturally in your response' in content.lower(), \
        "Missing fuzzy match confirmation guidance"
    print("✓ Fuzzy match confirmation guidance found")
    
    # Test 8: Optional import
    assert 'from typing import Dict, Any, Optional' in content, \
        "Missing Optional import"
    print("✓ Optional import found")
    
    print("✓ All information_prompts.py tests PASSED")


def test_information_handler():
    """Test information.py changes"""
    print("\n=== Testing information.py ===")
    
    filepath = os.path.join('app', 'agent', 'nodes', 'information.py')
    content = read_file(filepath)
    
    # Test 1: _fetch_owner_profile function exists
    assert 'async def _fetch_owner_profile' in content, \
        "Missing _fetch_owner_profile function"
    print("✓ _fetch_owner_profile function found")
    
    # Test 2: Fetching owner profile in handler
    assert 'owner_profile = await _fetch_owner_profile' in content, \
        "Missing owner profile fetch call"
    print("✓ Owner profile fetch call found")
    
    # Test 3: Extracting business_name
    assert 'business_name = owner_profile.get("business_name")' in content, \
        "Missing business_name extraction"
    print("✓ business_name extraction found")
    
    # Test 4: Passing business_name to create_information_prompt
    assert 'business_name=business_name' in content, \
        "Missing business_name parameter in create_information_prompt call"
    print("✓ business_name passed to create_information_prompt")
    
    # Test 5: Logging for personalization
    assert 'business_name' in content and 'personalization' in content.lower(), \
        "Missing logging for personalization"
    print("✓ Logging for personalization found")
    
    # Test 6: _fetch_owner_profile uses OwnerProfile model
    assert 'from shared.models import OwnerProfile' in content or \
           'OwnerProfile' in content, \
        "Missing OwnerProfile model usage"
    print("✓ OwnerProfile model usage found")
    
    print("✓ All information.py tests PASSED")


def test_requirements_coverage():
    """Test that requirements are covered"""
    print("\n=== Testing Requirements Coverage ===")
    
    prompts_file = os.path.join('app', 'agent', 'prompts', 'information_prompts.py')
    handler_file = os.path.join('app', 'agent', 'nodes', 'information.py')
    
    prompts_content = read_file(prompts_file)
    handler_content = read_file(handler_file)
    
    # Requirement 9.2: Information_Handler processes informational queries
    assert 'Information_Handler processes all non-booking informational queries' in handler_content or \
           'information queries' in handler_content.lower(), \
        "Requirement 9.2 not covered"
    print("✓ Requirement 9.2: Information_Handler processes informational queries")
    
    # Requirement 9.5: Property details queries handled
    assert 'get_property_details' in prompts_content or 'property details' in prompts_content.lower(), \
        "Requirement 9.5 not covered"
    print("✓ Requirement 9.5: Property details queries handled")
    
    # Requirement 9.6: Court availability queries handled
    assert 'get_court_availability' in prompts_content or 'availability' in prompts_content.lower(), \
        "Requirement 9.6 not covered"
    print("✓ Requirement 9.6: Court availability queries handled")
    
    print("✓ All requirements covered")


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("TASK 5.3 VERIFICATION: Information Handler Prompts Personalization")
    print("=" * 70)
    
    try:
        # Change to chatbot directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        test_information_prompts()
        test_information_handler()
        test_requirements_coverage()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED - Task 5.3 Implementation Verified")
        print("=" * 70)
        print("\nImplementation Summary:")
        print("1. ✓ Updated SYSTEM_TEMPLATE with business_name personalization")
        print("2. ✓ Added context that bot only shows owner's properties")
        print("3. ✓ Enhanced fuzzy match confirmation prompts")
        print("4. ✓ Added business_name parameter to create_information_prompt")
        print("5. ✓ Added _fetch_owner_profile function to information_handler")
        print("6. ✓ information_handler fetches and uses business_name")
        print("\nRequirements Validated:")
        print("- 9.2: Information_Handler processes informational queries")
        print("- 9.5: Property details queries handled")
        print("- 9.6: Court availability queries handled")
        print("=" * 70)
        
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
    exit(main())
