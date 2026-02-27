"""
Verification script for sync-to-async bridge utility.

This script demonstrates the usage of the sync bridge and verifies
that it's properly configured.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.tools.sync_bridge import (
    run_sync_in_executor,
    sync_to_async,
    call_sync_service,
    SyncDBContext,
)


def sync_add(x: int, y: int) -> int:
    """Simple sync function for testing."""
    return x + y


def sync_multiply(x: int, y: int, factor: int = 1) -> int:
    """Sync function with keyword arguments."""
    return (x * y) * factor


@sync_to_async
def decorated_function(message: str) -> str:
    """Function decorated with sync_to_async."""
    return f"Processed: {message}"


async def test_basic_execution():
    """Test basic sync function execution."""
    print("\n=== Testing Basic Execution ===")
    
    result = await run_sync_in_executor(sync_add, 10, 20)
    print(f"✓ Basic execution: 10 + 20 = {result}")
    assert result == 30, "Basic execution failed"


async def test_kwargs_execution():
    """Test execution with keyword arguments."""
    print("\n=== Testing Keyword Arguments ===")
    
    result = await run_sync_in_executor(sync_multiply, 5, 6, factor=2)
    print(f"✓ Kwargs execution: (5 * 6) * 2 = {result}")
    assert result == 60, "Kwargs execution failed"


async def test_decorator():
    """Test sync_to_async decorator."""
    print("\n=== Testing Decorator ===")
    
    result = await decorated_function("Hello, World!")
    print(f"✓ Decorator: {result}")
    assert result == "Processed: Hello, World!", "Decorator failed"


async def test_concurrent_execution():
    """Test concurrent execution of multiple sync functions."""
    print("\n=== Testing Concurrent Execution ===")
    
    tasks = [
        run_sync_in_executor(sync_add, i, i * 2)
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    print(f"✓ Concurrent execution results: {results}")
    assert results == [0, 3, 6, 9, 12], "Concurrent execution failed"


async def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")
    
    def failing_function():
        raise ValueError("Intentional error")
    
    try:
        await run_sync_in_executor(failing_function)
        print("✗ Error handling failed - exception not raised")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Error handling: Caught expected error - {e}")


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Sync-to-Async Bridge Verification")
    print("=" * 60)
    
    try:
        await test_basic_execution()
        await test_kwargs_execution()
        await test_decorator()
        await test_concurrent_execution()
        await test_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ All verification tests passed!")
        print("=" * 60)
        print("\nThe sync bridge is properly configured and ready to use.")
        print("\nUsage examples:")
        print("  1. Basic: await run_sync_in_executor(func, *args, **kwargs)")
        print("  2. Decorator: @sync_to_async on function definition")
        print("  3. Service calls: await call_sync_service(service_func, db=None, ...)")
        print("  4. Context manager: async with SyncDBContext() as db: ...")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
