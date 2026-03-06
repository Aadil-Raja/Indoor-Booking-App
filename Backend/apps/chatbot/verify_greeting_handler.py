"""
Simple verification script for greeting handler state initialization.

This script verifies that the greeting handler correctly:
- Initializes flow_state when empty (Requirement 10.1)
- Initializes bot_memory when empty (Requirement 10.2)
- Sets up conversation context (Requirement 10.3)
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.agent.state.conversation_state import ConversationState
from app.agent.state.flow_state_manager import initialize_flow_state, validate_flow_state
from app.agent.state.memory_manager import _initialize_bot_memory, _ensure_bot_memory_structure


def verify_flow_state_initialization():
    """Verify flow_state initialization works correctly."""
    print("Testing flow_state initialization...")
    
    # Test 1: Initialize empty flow_state
    flow_state = initialize_flow_state()
    
    # Verify structure
    assert isinstance(flow_state, dict), "flow_state should be a dict"
    assert "current_intent" in flow_state, "flow_state should have current_intent"
    assert "property_id" in flow_state, "flow_state should have property_id"
    assert "court_id" in flow_state, "flow_state should have court_id"
    assert "date" in flow_state, "flow_state should have date"
    assert "time_slot" in flow_state, "flow_state should have time_slot"
    assert "booking_step" in flow_state, "flow_state should have booking_step"
    assert "owner_properties" in flow_state, "flow_state should have owner_properties"
    assert "context" in flow_state, "flow_state should have context"
    
    # Verify validation
    assert validate_flow_state(flow_state), "Initialized flow_state should be valid"
    
    print("✓ flow_state initialization works correctly")
    return True


def verify_bot_memory_initialization():
    """Verify bot_memory initialization works correctly."""
    print("Testing bot_memory initialization...")
    
    # Test 1: Initialize empty bot_memory
    bot_memory = _initialize_bot_memory()
    
    # Verify structure
    assert isinstance(bot_memory, dict), "bot_memory should be a dict"
    assert "conversation_history" in bot_memory, "bot_memory should have conversation_history"
    assert "user_preferences" in bot_memory, "bot_memory should have user_preferences"
    assert "inferred_information" in bot_memory, "bot_memory should have inferred_information"
    assert "context" in bot_memory, "bot_memory should have context"
    
    # Verify types
    assert isinstance(bot_memory["conversation_history"], list), "conversation_history should be a list"
    assert isinstance(bot_memory["user_preferences"], dict), "user_preferences should be a dict"
    assert isinstance(bot_memory["inferred_information"], dict), "inferred_information should be a dict"
    assert isinstance(bot_memory["context"], dict), "context should be a dict"
    
    print("✓ bot_memory initialization works correctly")
    return True


def verify_bot_memory_structure_enforcement():
    """Verify bot_memory structure enforcement works correctly."""
    print("Testing bot_memory structure enforcement...")
    
    # Test with incomplete bot_memory
    incomplete_memory = {"conversation_history": []}
    
    # Ensure structure
    complete_memory = _ensure_bot_memory_structure(incomplete_memory)
    
    # Verify all fields are present
    assert "conversation_history" in complete_memory
    assert "user_preferences" in complete_memory
    assert "inferred_information" in complete_memory
    assert "context" in complete_memory
    
    print("✓ bot_memory structure enforcement works correctly")
    return True


async def verify_greeting_handler_state_init():
    """Verify greeting handler initializes state correctly."""
    print("Testing greeting handler state initialization...")
    
    # Import here to avoid circular imports
    from app.agent.nodes.greeting import greeting_handler
    
    # Create a minimal state with empty flow_state and bot_memory
    state: ConversationState = {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "223e4567-e89b-12d3-a456-426614174000",
        "owner_profile_id": "1",
        "user_message": "Hello",
        "flow_state": {},  # Empty
        "bot_memory": {},  # Empty
        "messages": [],
        "intent": "greeting",
        "response_content": "",
        "response_type": "",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }
    
    # Call greeting handler
    result = await greeting_handler(state)
    
    # Verify flow_state was initialized
    assert result["flow_state"] is not None, "flow_state should not be None"
    assert isinstance(result["flow_state"], dict), "flow_state should be a dict"
    assert "current_intent" in result["flow_state"], "flow_state should have current_intent"
    assert "context" in result["flow_state"], "flow_state should have context"
    
    # Verify bot_memory was initialized
    assert result["bot_memory"] is not None, "bot_memory should not be None"
    assert isinstance(result["bot_memory"], dict), "bot_memory should be a dict"
    assert "conversation_history" in result["bot_memory"], "bot_memory should have conversation_history"
    assert "user_preferences" in result["bot_memory"], "bot_memory should have user_preferences"
    assert "inferred_information" in result["bot_memory"], "bot_memory should have inferred_information"
    
    # Verify response was generated
    assert result["response_content"] is not None, "response_content should not be None"
    assert len(result["response_content"]) > 0, "response_content should not be empty"
    assert result["response_type"] == "text", "response_type should be 'text'"
    
    print("✓ greeting handler initializes state correctly")
    return True


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Greeting Handler State Initialization Verification")
    print("=" * 60)
    print()
    
    try:
        # Test flow_state initialization
        verify_flow_state_initialization()
        print()
        
        # Test bot_memory initialization
        verify_bot_memory_initialization()
        print()
        
        # Test bot_memory structure enforcement
        verify_bot_memory_structure_enforcement()
        print()
        
        # Test greeting handler state initialization
        await verify_greeting_handler_state_init()
        print()
        
        print("=" * 60)
        print("✓ All verification tests passed!")
        print("=" * 60)
        print()
        print("Requirements verified:")
        print("  ✓ 10.1: Initialize Flow_State when conversation begins")
        print("  ✓ 10.2: Initialize Bot_Memory when conversation begins")
        print("  ✓ 10.3: Set up conversation context for subsequent nodes")
        print()
        
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"✗ Verification failed: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Unexpected error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
