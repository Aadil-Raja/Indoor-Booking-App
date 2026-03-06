"""
Test script to verify greeting handler correctly identifies new vs returning users.
"""
import asyncio
import sys
from pathlib import Path

# Add Backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.agent.nodes.greeting import _is_returning_user


def test_new_user_detection():
    """Test that new users are correctly identified."""
    
    # Test 1: Empty bot_memory (brand new user)
    bot_memory = {
        "conversation_history": [],
        "user_preferences": {},
        "context": {}
    }
    assert not _is_returning_user(bot_memory), "Empty bot_memory should be new user"
    print("✓ Test 1 passed: Empty bot_memory = new user")
    
    # Test 2: One message in history (current message just added by append_user_message)
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "hi", "timestamp": "2024-03-06T10:00:00"}
        ],
        "user_preferences": {},
        "context": {}
    }
    assert not _is_returning_user(bot_memory), "One message should be new user"
    print("✓ Test 2 passed: One message in history = new user")
    
    # Test 3: Two messages in history (has previous conversation)
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "hi", "timestamp": "2024-03-06T09:00:00"},
            {"role": "assistant", "content": "Hello!", "timestamp": "2024-03-06T09:00:01"},
        ],
        "user_preferences": {},
        "context": {}
    }
    assert _is_returning_user(bot_memory), "Two messages should be returning user"
    print("✓ Test 3 passed: Two messages in history = returning user")
    
    # Test 4: Has user preferences (returning user)
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "hi", "timestamp": "2024-03-06T10:00:00"}
        ],
        "user_preferences": {"preferred_sport": "tennis"},
        "context": {}
    }
    assert _is_returning_user(bot_memory), "User preferences should indicate returning user"
    print("✓ Test 4 passed: User preferences = returning user")
    
    # Test 5: Has context from previous search (returning user)
    bot_memory = {
        "conversation_history": [
            {"role": "user", "content": "hi", "timestamp": "2024-03-06T10:00:00"}
        ],
        "user_preferences": {},
        "context": {"last_search_results": [{"property_id": 1}]}
    }
    assert _is_returning_user(bot_memory), "Search context should indicate returning user"
    print("✓ Test 5 passed: Search context = returning user")
    
    print("\n✅ All tests passed! New user detection is working correctly.")


if __name__ == "__main__":
    test_new_user_detection()
