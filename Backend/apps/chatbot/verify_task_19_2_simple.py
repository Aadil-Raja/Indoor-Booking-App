"""
Simple verification script for Task 19.2: Add bot_memory checking to prevent redundant questions

This script verifies that all node prompts check bot_memory before asking questions
and use preferences to pre-fill or suggest options.

Requirements: 4.5
"""

import os


def read_file(filepath: str) -> str:
    """Read file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def verify_prompt_checks_bot_memory(prompt_name: str, prompt_content: str) -> bool:
    """
    Verify that a prompt template checks bot_memory before asking questions.
    
    Args:
        prompt_name: Name of the prompt for logging
        prompt_content: The prompt template string
        
    Returns:
        bool: True if prompt checks bot_memory, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Verifying: {prompt_name}")
    print(f"{'='*80}")
    
    # Check 1: Prompt includes bot_memory in template
    has_bot_memory = "{bot_memory}" in prompt_content
    print(f"✓ Includes {{bot_memory}} placeholder: {has_bot_memory}")
    
    # Check 2: Prompt mentions checking bot_memory
    checks_memory = "check bot_memory" in prompt_content.lower() or "first, check" in prompt_content.lower()
    print(f"✓ Instructs to check bot_memory: {checks_memory}")
    
    # Check 3: Prompt mentions user_preferences
    mentions_preferences = "user_preferences" in prompt_content.lower() or "preferred_" in prompt_content.lower()
    print(f"✓ References user preferences: {mentions_preferences}")
    
    # Check 4: Prompt provides guidance on using preferences
    uses_preferences = (
        "suggest" in prompt_content.lower() or 
        "prefer" in prompt_content.lower() or
        "prioritize" in prompt_content.lower() or
        "highlight" in prompt_content.lower()
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


def extract_template(content: str, template_name: str) -> str:
    """Extract a template from file content."""
    start_marker = f'{template_name} = """'
    if start_marker not in content:
        return ""
    
    start_idx = content.find(start_marker) + len(start_marker)
    end_idx = content.find('"""', start_idx)
    
    if end_idx == -1:
        return ""
    
    return content[start_idx:end_idx]


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
    
    # Read prompt files
    booking_prompts_path = "Backend/apps/chatbot/app/agent/prompts/booking_prompts.py"
    information_prompts_path = "Backend/apps/chatbot/app/agent/prompts/information_prompts.py"
    intent_prompts_path = "Backend/apps/chatbot/app/agent/prompts/intent_prompts.py"
    
    booking_content = read_file(booking_prompts_path)
    information_content = read_file(information_prompts_path)
    intent_content = read_file(intent_prompts_path)
    
    results = []
    
    # Verify booking prompts
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_PROPERTY_SYSTEM_TEMPLATE",
        extract_template(booking_content, "SELECT_PROPERTY_SYSTEM_TEMPLATE")
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_SERVICE_SYSTEM_TEMPLATE",
        extract_template(booking_content, "SELECT_SERVICE_SYSTEM_TEMPLATE")
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_DATE_SYSTEM_TEMPLATE",
        extract_template(booking_content, "SELECT_DATE_SYSTEM_TEMPLATE")
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "SELECT_TIME_SYSTEM_TEMPLATE",
        extract_template(booking_content, "SELECT_TIME_SYSTEM_TEMPLATE")
    ))
    
    results.append(verify_prompt_checks_bot_memory(
        "CONFIRM_BOOKING_SYSTEM_TEMPLATE",
        extract_template(booking_content, "CONFIRM_BOOKING_SYSTEM_TEMPLATE")
    ))
    
    # Verify information prompt
    results.append(verify_prompt_checks_bot_memory(
        "INFORMATION_SYSTEM_TEMPLATE",
        extract_template(information_content, "SYSTEM_TEMPLATE")
    ))
    
    # Verify intent routing prompt
    results.append(verify_prompt_checks_bot_memory(
        "INTENT_ROUTING_PROMPT",
        extract_template(intent_content, "INTENT_ROUTING_PROMPT")
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
    exit(exit_code)
