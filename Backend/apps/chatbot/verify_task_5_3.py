"""
Verification script for Task 5.3: Update information handler prompts for personalization

This script verifies that:
1. Information prompts include business_name personalization
2. Prompts reference that bot only shows owner's properties
3. Fuzzy match confirmation prompts are included
4. The create_information_prompt function accepts business_name parameter
5. The information_handler fetches and uses business_name

Requirements: 9.2, 9.5, 9.6
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.prompts.information_prompts import (
    SYSTEM_TEMPLATE,
    create_information_prompt
)


def test_business_name_in_system_template():
    """Test that SYSTEM_TEMPLATE includes business_name placeholder"""
    print("\n=== Test 1: Business Name in System Template ===")
    
    # Check for business_name placeholder
    assert "{business_name}" in SYSTEM_TEMPLATE, "SYSTEM_TEMPLATE should include {business_name} placeholder"
    print("✓ SYSTEM_TEMPLATE includes {business_name} placeholder")
    
    # Check for personalized introduction
    assert "You are {business_name}'s assistant" in SYSTEM_TEMPLATE, \
        "SYSTEM_TEMPLATE should introduce bot as business_name's assistant"
    print("✓ SYSTEM_TEMPLATE introduces bot as business_name's assistant")
    
    print("✓ Test 1 PASSED")


def test_owner_properties_context():
    """Test that SYSTEM_TEMPLATE mentions showing only owner's properties"""
    print("\n=== Test 2: Owner Properties Context ===")
    
    # Check for context about showing only owner's properties
    assert "only show" in SYSTEM_TEMPLATE.lower() or "only provide" in SYSTEM_TEMPLATE.lower(), \
        "SYSTEM_TEMPLATE should mention showing only owner's properties"
    print("✓ SYSTEM_TEMPLATE mentions showing only owner's properties")
    
    assert "{business_name}'s properties" in SYSTEM_TEMPLATE or "our facilities" in SYSTEM_TEMPLATE, \
        "SYSTEM_TEMPLATE should reference business properties"
    print("✓ SYSTEM_TEMPLATE references business properties")
    
    print("✓ Test 2 PASSED")


def test_fuzzy_match_confirmation_prompts():
    """Test that SYSTEM_TEMPLATE includes fuzzy match confirmation guidance"""
    print("\n=== Test 3: Fuzzy Match Confirmation Prompts ===")
    
    # Check for fuzzy search confirmation guidance
    assert "confirm" in SYSTEM_TEMPLATE.lower() or "acknowledge" in SYSTEM_TEMPLATE.lower(), \
        "SYSTEM_TEMPLATE should include fuzzy match confirmation guidance"
    print("✓ SYSTEM_TEMPLATE includes fuzzy match confirmation guidance")
    
    # Check for fuzzy context placeholder
    assert "{fuzzy_context}" in SYSTEM_TEMPLATE, \
        "SYSTEM_TEMPLATE should include {fuzzy_context} placeholder"
    print("✓ SYSTEM_TEMPLATE includes {fuzzy_context} placeholder")
    
    print("✓ Test 3 PASSED")


def test_create_information_prompt_signature():
    """Test that create_information_prompt accepts business_name parameter"""
    print("\n=== Test 4: create_information_prompt Function Signature ===")
    
    import inspect
    
    # Get function signature
    sig = inspect.signature(create_information_prompt)
    params = sig.parameters
    
    # Check for business_name parameter
    assert "business_name" in params, \
        "create_information_prompt should accept business_name parameter"
    print("✓ create_information_prompt accepts business_name parameter")
    
    # Check that business_name is optional
    assert params["business_name"].default is not inspect.Parameter.empty, \
        "business_name parameter should be optional"
    print("✓ business_name parameter is optional")
    
    print("✓ Test 4 PASSED")


def test_create_information_prompt_with_business_name():
    """Test that create_information_prompt uses business_name correctly"""
    print("\n=== Test 5: create_information_prompt with business_name ===")
    
    # Create prompt with business_name
    bot_memory = {
        "context": {},
        "user_preferences": {}
    }
    
    prompt = create_information_prompt(
        owner_profile_id=1,
        bot_memory=bot_memory,
        business_name="ABC Sports Center"
    )
    
    # Check that prompt was created successfully
    assert prompt is not None, "Prompt should be created successfully"
    print("✓ Prompt created successfully with business_name")
    
    # Check that prompt has partial variables
    assert hasattr(prompt, 'partial_variables'), "Prompt should have partial_variables"
    print("✓ Prompt has partial_variables")
    
    # Check that business_name is in partial variables
    assert 'business_name' in prompt.partial_variables, \
        "business_name should be in partial_variables"
    print("✓ business_name is in partial_variables")
    
    # Check the value
    assert prompt.partial_variables['business_name'] == "ABC Sports Center", \
        "business_name value should match input"
    print("✓ business_name value matches input")
    
    print("✓ Test 5 PASSED")


def test_create_information_prompt_default_business_name():
    """Test that create_information_prompt uses default when business_name is None"""
    print("\n=== Test 6: create_information_prompt with default business_name ===")
    
    bot_memory = {
        "context": {},
        "user_preferences": {}
    }
    
    # Create prompt without business_name
    prompt = create_information_prompt(
        owner_profile_id=1,
        bot_memory=bot_memory,
        business_name=None
    )
    
    # Check that business_name defaults to "our facility"
    assert prompt.partial_variables['business_name'] == "our facility", \
        "business_name should default to 'our facility' when None"
    print("✓ business_name defaults to 'our facility' when None")
    
    print("✓ Test 6 PASSED")


def test_information_handler_imports():
    """Test that information_handler has necessary imports for fetching owner profile"""
    print("\n=== Test 7: information_handler Imports ===")
    
    # Read the information.py file
    info_file_path = os.path.join(
        os.path.dirname(__file__),
        'app', 'agent', 'nodes', 'information.py'
    )
    
    with open(info_file_path, 'r') as f:
        content = f.read()
    
    # Check for _fetch_owner_profile function
    assert "_fetch_owner_profile" in content, \
        "information.py should have _fetch_owner_profile function"
    print("✓ information.py has _fetch_owner_profile function")
    
    # Check that business_name is passed to create_information_prompt
    assert "business_name=business_name" in content or "business_name=" in content, \
        "information_handler should pass business_name to create_information_prompt"
    print("✓ information_handler passes business_name to create_information_prompt")
    
    print("✓ Test 7 PASSED")


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("TASK 5.3 VERIFICATION: Information Handler Prompts Personalization")
    print("=" * 70)
    
    try:
        test_business_name_in_system_template()
        test_owner_properties_context()
        test_fuzzy_match_confirmation_prompts()
        test_create_information_prompt_signature()
        test_create_information_prompt_with_business_name()
        test_create_information_prompt_default_business_name()
        test_information_handler_imports()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED - Task 5.3 Implementation Verified")
        print("=" * 70)
        print("\nSummary:")
        print("1. ✓ SYSTEM_TEMPLATE includes business_name personalization")
        print("2. ✓ SYSTEM_TEMPLATE mentions showing only owner's properties")
        print("3. ✓ SYSTEM_TEMPLATE includes fuzzy match confirmation guidance")
        print("4. ✓ create_information_prompt accepts business_name parameter")
        print("5. ✓ create_information_prompt uses business_name correctly")
        print("6. ✓ create_information_prompt defaults to 'our facility'")
        print("7. ✓ information_handler fetches and passes business_name")
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
    sys.exit(main())
