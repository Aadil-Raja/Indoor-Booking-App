"""
Verification script for LLM provider factory.

This script demonstrates the factory function creating different LLM providers
based on configuration.
"""

import sys
import os

# Add the parent directory to the path to access shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import only the LLM module to avoid dependency issues
from app.services.llm import create_llm_provider, LLMProvider, OpenAIProvider, GeminiProvider


def verify_factory():
    """Verify the LLM provider factory function."""
    
    print("=" * 60)
    print("LLM Provider Factory Verification")
    print("=" * 60)
    
    # Test 1: Create OpenAI provider using settings
    print("\n1. Creating OpenAI provider with default settings...")
    try:
        openai_provider = create_llm_provider(
            provider_name="openai",
            api_key="test-key",
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.7
        )
        print(f"   ✓ Provider created: {type(openai_provider).__name__}")
        print(f"   ✓ Is LLMProvider: {isinstance(openai_provider, LLMProvider)}")
        print(f"   ✓ Is OpenAIProvider: {isinstance(openai_provider, OpenAIProvider)}")
        print(f"   ✓ Model: {openai_provider.model}")
        print(f"   ✓ Max tokens: {openai_provider.default_max_tokens}")
        print(f"   ✓ Temperature: {openai_provider.default_temperature}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: Create OpenAI provider with explicit parameters
    print("\n2. Creating OpenAI provider with explicit parameters...")
    try:
        openai_custom = create_llm_provider(
            provider_name="openai",
            api_key="test-api-key",
            model="gpt-4",
            max_tokens=1000,
            temperature=0.5
        )
        print(f"   ✓ Provider created: {type(openai_custom).__name__}")
        print(f"   ✓ Model: {openai_custom.model}")
        print(f"   ✓ Max tokens: {openai_custom.default_max_tokens}")
        print(f"   ✓ Temperature: {openai_custom.default_temperature}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Create OpenAI provider with defaults
    print("\n3. Creating OpenAI provider with defaults...")
    try:
        openai_defaults = create_llm_provider(
            provider_name="openai",
            api_key="test-api-key"
        )
        print(f"   ✓ Provider created: {type(openai_defaults).__name__}")
        print(f"   ✓ Model (default): {openai_defaults.model}")
        print(f"   ✓ Max tokens (default): {openai_defaults.default_max_tokens}")
        print(f"   ✓ Temperature (default): {openai_defaults.default_temperature}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 4: Create Gemini provider (placeholder)
    print("\n4. Creating Gemini provider (placeholder)...")
    try:
        gemini_provider = create_llm_provider(
            provider_name="gemini",
            api_key="test-gemini-key",
            model="gemini-pro"
        )
        print(f"   ✓ Provider created: {type(gemini_provider).__name__}")
        print(f"   ✓ Is LLMProvider: {isinstance(gemini_provider, LLMProvider)}")
        print(f"   ✓ Is GeminiProvider: {isinstance(gemini_provider, GeminiProvider)}")
        print(f"   ⚠ Note: Gemini is a placeholder and not yet implemented")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 5: Test unsupported provider
    print("\n5. Testing unsupported provider (should fail)...")
    try:
        invalid_provider = create_llm_provider(
            provider_name="invalid-provider",
            api_key="test-key"
        )
        print(f"   ✗ Should have raised ValueError but didn't")
        return False
    except ValueError as e:
        print(f"   ✓ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        return False
    
    # Test 6: Test case insensitivity
    print("\n6. Testing case insensitivity...")
    try:
        openai_upper = create_llm_provider(
            provider_name="OPENAI",
            api_key="test-key"
        )
        openai_mixed = create_llm_provider(
            provider_name="OpenAI",
            api_key="test-key"
        )
        print(f"   ✓ 'OPENAI' works: {type(openai_upper).__name__}")
        print(f"   ✓ 'OpenAI' works: {type(openai_mixed).__name__}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All factory tests passed!")
    print("=" * 60)
    
    # Display usage example
    print("\nUsage Example:")
    print("  from app.services.llm import create_llm_provider")
    print("  from app.core.config import settings")
    print("")
    print("  provider = create_llm_provider(")
    print("      provider_name=settings.LLM_PROVIDER,")
    print("      api_key=settings.OPENAI_API_KEY,")
    print("      model=settings.OPENAI_MODEL,")
    print("      max_tokens=settings.OPENAI_MAX_TOKENS,")
    print("      temperature=settings.OPENAI_TEMPERATURE")
    print("  )")
    
    return True


if __name__ == "__main__":
    success = verify_factory()
    sys.exit(0 if success else 1)
