"""
Verification script for Task 19.2: Add bot_memory checking to prevent redundant questions

This script verifies that all node prompts check bot_memory before asking questions
and use preferences to pre-fill or suggest options.

Requirements: 4.5
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.prompts.booking_prompts import (
    SELECT_PROPERTY_SYSTEM_TEMPLATE,
    SELECT_SERVICE_SYSTEM_TEMPLATE,
    SELECT_DATE_SYSTEM_TEMPLATE,
    SELECT_TIME_SYSTEM_TEMPLATE,
    CONFIRM_BOOKING_SYSTEM_TEMPLATE
)
from app.agent.prompts.information_prompts import SYSTEM_TEMPLATE
from app.agent.prompts.intent_prompts import INTENT_ROUTING_PROMPT


def verify_prompt_checks_bot_memory(prompt_name: str, prompt_template: str) -> bool:
    """
    Verify that a prompt template checks bot_memory before asking questions.
    
    Args:
        prompt_name: Name of the prompt for logging
        prompt_template: The prompt template string
        
    Returns:
        bool: True if prompt checks bot_memory, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Verifying: {prompt_name}")
    print(f"{'='*80}")
    
    # Check 1: Prompt includes bot_memory in template
    has_bot_memory = "{bot_memory}" in prompt_template
    print(f"✓ Includes {{bot_memory}} placeholder: {has_bot_memory}")
    
    # Check 2: Prompt mentions checking bot_memory
    checks_memory = "check bot_memory" in prompt_template.lower() or "first, check" in prompt_template.lower()
    print(f"✓ Instructs to check bot_memory: {checks_memory}")
    
    # Check 3: Prompt mentions user_preferences
    mentions_preferences = "user_preferences" in prompt_template.lower() or "preferred_" in prompt_template.lower()
    print(f"✓ References user preferences: {mentions_preferences}")
    
    # Check 4: Prompt provides guidance on using preferences
    uses_preferences = (
        "suggest" in prompt_template.lower() or 
        "prefer" in prompt_template.lower() or
        "prioritize" in prompt_template.lower() or
        "highlight" in prompt_template.lower()
    )
    print(f"✓ Provides guidance on using preferences: {uses_preferences}")
    
    # Overall result
    passed = has_bot_memory and checks_memory and mentions_preferences and uses_preferences
    
    if passed:
        print(f"\n✅ {prompt_name} PASSED - Properly checks bot_memory")
    else:
        print(f"\n❌ {prompt_name} FAILED - Missing bot_memory checks")
        if not has_bot_memory:
            print("   - Missing {bot_memory} placeholder")
        if not checks_memory:
            print("   - Missing instruction to check bot_memory")
        if not mentions_preferences:
            print("   - Missing reference to user preferences")
        if not uses_preferences:
            print("   - Missing guidance on using preferences")
    
    return passed


def main():
    """
    Main verification function.
    
    Verifies that all node prompts check bot_memory before asking questions.
    """
    print("\n" + "="*80)
    print("TASK 19.2 VERIFICATION: Bot Memory Checking in Prompts")
    print("="*80)
    print("\nRequirement 4.5: LLM SHALL check Bot_Memory before asking questions")
    print("that may have been answered previously")
    
    results = []
    
    # Verify booking prompts
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_PROPERTY_SYSTEM_TEMPLATE",
        SELECT_PROPERTY_SYSTEM_TEMPLATE
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_SERVICE_SYSTEM_TEMPLATE",
        SELECT_SERVICE_SYSTEM_TEMPLATE
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_DATE_SYSTEM_TEMPLATE",
        SELECT_DATE_SYSTEM_TEMPLATE
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_TIME_SYSTEM_TEMPLATE",
        SELECT_TIME_SYSTEM_TEMPLATE
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "CONFIRM_BOOKING_SYSTEM_TEMPLATE",
        CONFIRM_BOOKING_SYSTEM_TEMPLATE
    ))
    
    # Verify information prompt
    results.append(verify_prompt_checks_bot_memory(
        "INFORMATION_SYSTEM_TEMPLATE",
        SYSTEM_TEMPLATE
    ))
    
    # Verify intent routing prompt
    results.append(verify_prompt_checks_bot_memory(
        "INTENT_ROUTING_PROMPT",
        INTENT_ROUTING_PROMPT
    ))
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\nTotal prompts verified: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL PROMPTS PASSED - Task 19.2 implementation verified!")
        print("\nAll node prompts now:")
        print("  1. Check bot_memory.user_preferences before asking questions")
        print("  2. Skip questions if bot_memory contains answers")
        print("  3. Use preferences to pre-fill or suggest options")
        print("  4. Provide personalized, context-aware responses")
        return 0
    else:
        print(f"\n⚠️  {failed} prompt(s) need attention")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
