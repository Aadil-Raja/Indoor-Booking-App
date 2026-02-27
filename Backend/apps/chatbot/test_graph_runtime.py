"""
Test script for graph runtime initialization and execution.

This script verifies that the graph runtime can be properly initialized
and executed with mock dependencies.
"""

import sys
import os
import asyncio

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agent.runtime import create_graph_runtime, GraphRuntime, GraphExecutionError
from app.services.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    async def generate(self, prompt, max_tokens=100, temperature=0.7, **kwargs):
        """Return a mock response."""
        return "Mock LLM response"
    
    async def stream(self, prompt, max_tokens=100, temperature=0.7, **kwargs):
        """Return a mock streaming response."""
        yield "Mock "
        yield "streaming "
        yield "response"
    
    def count_tokens(self, text):
        """Return a mock token count."""
        return len(text.split())


def test_runtime_initialization():
    """Test that the runtime can be initialized."""
    print("Testing runtime initialization...")
    
    try:
        mock_llm = MockLLMProvider()
        runtime = create_graph_runtime(llm_provider=mock_llm)
        print("✓ Runtime created successfully")
        
        # Check that runtime has required attributes
        if not hasattr(runtime, 'graph'):
            print("✗ Runtime missing 'graph' attribute")
            return False
        print("✓ Runtime has 'graph' attribute")
        
        if not hasattr(runtime, 'tools'):
            print("✗ Runtime missing 'tools' attribute")
            return False
        print("✓ Runtime has 'tools' attribute")
        
        if not hasattr(runtime, 'llm_provider'):
            print("✗ Runtime missing 'llm_provider' attribute")
            return False
        print("✓ Runtime has 'llm_provider' attribute")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create runtime: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_runtime_execution():
    """Test that the runtime can execute a simple state."""
    print("\nTesting runtime execution...")
    
    try:
        mock_llm = MockLLMProvider()
        runtime = create_graph_runtime(llm_provider=mock_llm)
        
        # Create a minimal valid state
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "456e7890-e89b-12d3-a456-426614174000",
            "owner_id": "789e0123-e89b-12d3-a456-426614174000",
            "user_message": "Hello",
        }
        
        print("Executing graph with greeting message...")
        result = await runtime.execute(state)
        
        # Check that result has required fields
        if "response_content" not in result:
            print("✗ Result missing 'response_content'")
            return False
        print(f"✓ Result has response_content: '{result['response_content'][:50]}...'")
        
        if "response_type" not in result:
            print("✗ Result missing 'response_type'")
            return False
        print(f"✓ Result has response_type: {result['response_type']}")
        
        if "flow_state" not in result:
            print("✗ Result missing 'flow_state'")
            return False
        print("✓ Result has flow_state")
        
        if "bot_memory" not in result:
            print("✗ Result missing 'bot_memory'")
            return False
        print("✓ Result has bot_memory")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to execute runtime: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_runtime_state_validation():
    """Test that the runtime validates input state."""
    print("\nTesting runtime state validation...")
    
    try:
        mock_llm = MockLLMProvider()
        runtime = create_graph_runtime(llm_provider=mock_llm)
        
        # Test with missing required fields
        invalid_states = [
            {},  # Missing all fields
            {"chat_id": "123"},  # Missing user_id, owner_id, user_message
            {"chat_id": "123", "user_id": "456"},  # Missing owner_id, user_message
            {"chat_id": "123", "user_id": "456", "owner_id": "789"},  # Missing user_message
        ]
        
        for i, invalid_state in enumerate(invalid_states):
            try:
                await runtime.execute(invalid_state)
                print(f"✗ Test case {i+1}: Should have raised ValueError for invalid state")
                return False
            except ValueError as e:
                print(f"✓ Test case {i+1}: Correctly raised ValueError: {str(e)[:50]}...")
            except Exception as e:
                print(f"✗ Test case {i+1}: Raised unexpected exception: {type(e).__name__}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Failed state validation test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_runtime_state_preparation():
    """Test that the runtime prepares state with defaults."""
    print("\nTesting runtime state preparation...")
    
    try:
        mock_llm = MockLLMProvider()
        runtime = create_graph_runtime(llm_provider=mock_llm)
        
        # Create state with only required fields
        minimal_state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "456e7890-e89b-12d3-a456-426614174000",
            "owner_id": "789e0123-e89b-12d3-a456-426614174000",
            "user_message": "Hello",
        }
        
        result = await runtime.execute(minimal_state)
        
        # Check that optional fields are populated with defaults
        optional_fields = [
            "flow_state",
            "bot_memory",
            "messages",
            "response_metadata",
        ]
        
        for field in optional_fields:
            if field not in result:
                print(f"✗ Result missing optional field: {field}")
                return False
            print(f"✓ Result has optional field: {field}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed state preparation test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_runtime_error_handling():
    """Test that the runtime handles errors gracefully."""
    print("\nTesting runtime error handling...")
    
    # Create a mock LLM that raises an error
    class ErrorLLMProvider(LLMProvider):
        async def generate(self, prompt, max_tokens=100, temperature=0.7, **kwargs):
            from app.services.llm.base import LLMProviderError
            raise LLMProviderError("Mock LLM error")
        
        async def stream(self, prompt, max_tokens=100, temperature=0.7, **kwargs):
            from app.services.llm.base import LLMProviderError
            raise LLMProviderError("Mock LLM error")
        
        def count_tokens(self, text):
            return len(text.split())
    
    try:
        error_llm = ErrorLLMProvider()
        runtime = create_graph_runtime(llm_provider=error_llm)
        
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "456e7890-e89b-12d3-a456-426614174000",
            "owner_id": "789e0123-e89b-12d3-a456-426614174000",
            "user_message": "Hello",
            "flow_state": {"test": "data"},
            "bot_memory": {"test": "memory"},
        }
        
        result = await runtime.execute(state)
        
        # Check that error was handled gracefully
        if "response_content" not in result:
            print("✗ Result missing response_content after error")
            return False
        
        # Check that state was preserved
        if result.get("flow_state") != {"test": "data"}:
            print("✗ flow_state was not preserved after error")
            return False
        print("✓ flow_state preserved after error")
        
        if result.get("bot_memory") != {"test": "memory"}:
            print("✗ bot_memory was not preserved after error")
            return False
        print("✓ bot_memory preserved after error")
        
        print(f"✓ Error handled gracefully with fallback response")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed error handling test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Graph Runtime Test Suite")
    print("=" * 60)
    
    tests = [
        ("Initialization", test_runtime_initialization),
        ("Execution", test_runtime_execution),
        ("State Validation", test_runtime_state_validation),
        ("State Preparation", test_runtime_state_preparation),
        ("Error Handling", test_runtime_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Test: {name}")
        print(f"{'=' * 60}")
        
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        
        results.append((name, result))
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("Test Summary")
    print(f"{'=' * 60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
