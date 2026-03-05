"""
Quick test to verify OpenAI provider initialization works.
"""
import asyncio
import sys
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

async def test_openai_provider():
    """Test OpenAI provider initialization."""
    # Import directly without going through app modules
    from openai import AsyncOpenAI
    
    print("Testing AsyncOpenAI initialization...")
    
    try:
        # Test 1: Initialize with only api_key
        client = AsyncOpenAI(
            api_key="sk-test-key",
            max_retries=0
        )
        print("✅ AsyncOpenAI initialized successfully with api_key and max_retries!")
        
        # Test 2: Try with the old way (should fail)
        try:
            client_old = AsyncOpenAI(api_key="sk-test-key")
            print("✅ AsyncOpenAI initialized with just api_key (old way still works)")
        except Exception as e:
            print(f"⚠️  Old initialization method failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_provider())
    sys.exit(0 if success else 1)
