"""
Simple test script to verify the chat history endpoint.

This script tests:
1. Retrieving chat history for an existing chat
2. Handling non-existent chat IDs
3. Verifying message order (chronological)
"""

import asyncio
import sys
from uuid import UUID, uuid4
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.core.database import get_async_db, AsyncSessionLocal
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.services.chat_service import ChatService
from app.services.message_service import MessageService


async def test_chat_history_endpoint():
    """Test the chat history retrieval functionality."""
    
    print("=" * 60)
    print("Testing Chat History Endpoint")
    print("=" * 60)
    
    # Create async session
    async with AsyncSessionLocal() as session:
        # Initialize repositories and services
        chat_repo = ChatRepository(session)
        message_repo = MessageRepository(session)
        chat_service = ChatService(session, chat_repo, message_repo)
        message_service = MessageService(session, message_repo)
        
        # Test 1: Create a test chat with messages
        print("\n[Test 1] Creating test chat with messages...")
        
        user_id = uuid4()
        owner_id = uuid4()
        
        # Create chat
        chat = await chat_service.create_chat(user_id, owner_id)
        print(f"✓ Created chat: {chat.id}")
        
        # Create multiple messages
        messages_created = []
        
        # User message 1
        msg1 = await message_service.create_message(
            chat_id=chat.id,
            sender_type="user",
            content="I want to book a tennis court"
        )
        messages_created.append(msg1)
        print(f"✓ Created user message 1: {msg1.id}")
        
        # Bot response 1
        msg2 = await message_service.create_message(
            chat_id=chat.id,
            sender_type="bot",
            content="Great! Let me show you available properties.",
            message_type="text",
            token_usage=50
        )
        messages_created.append(msg2)
        print(f"✓ Created bot message 1: {msg2.id}")
        
        # User message 2
        msg3 = await message_service.create_message(
            chat_id=chat.id,
            sender_type="user",
            content="Show me downtown locations"
        )
        messages_created.append(msg3)
        print(f"✓ Created user message 2: {msg3.id}")
        
        # Bot response 2 with buttons
        msg4 = await message_service.create_message(
            chat_id=chat.id,
            sender_type="bot",
            content="Here are the available facilities:",
            message_type="button",
            metadata={
                "buttons": [
                    {"id": "prop1", "text": "Downtown Sports Center"},
                    {"id": "prop2", "text": "City Arena"}
                ]
            },
            token_usage=75
        )
        messages_created.append(msg4)
        print(f"✓ Created bot message 2 (with buttons): {msg4.id}")
        
        await session.commit()
        
        # Test 2: Retrieve chat history
        print("\n[Test 2] Retrieving chat history...")
        
        history = await message_service.get_chat_history(chat.id)
        
        print(f"✓ Retrieved {len(history)} messages")
        
        # Verify message count
        assert len(history) == 4, f"Expected 4 messages, got {len(history)}"
        print("✓ Message count correct")
        
        # Verify chronological order
        for i in range(len(history) - 1):
            assert history[i].created_at <= history[i + 1].created_at, \
                "Messages not in chronological order"
        print("✓ Messages in chronological order")
        
        # Verify message content
        assert history[0].sender_type == "user"
        assert history[0].content == "I want to book a tennis court"
        print("✓ First message content correct")
        
        assert history[1].sender_type == "bot"
        assert history[1].token_usage == 50
        print("✓ Bot message with token usage correct")
        
        assert history[3].message_type == "button"
        assert "buttons" in history[3].message_metadata
        assert len(history[3].message_metadata["buttons"]) == 2
        print("✓ Button message metadata correct")
        
        # Test 3: Test with non-existent chat
        print("\n[Test 3] Testing with non-existent chat...")
        
        fake_chat_id = uuid4()
        fake_chat = await chat_repo.get_by_id(fake_chat_id)
        
        assert fake_chat is None, "Expected None for non-existent chat"
        print(f"✓ Non-existent chat {fake_chat_id} returns None")
        
        # Test 4: Test with empty chat
        print("\n[Test 4] Testing with empty chat...")
        
        empty_chat = await chat_service.create_chat(uuid4(), uuid4())
        empty_history = await message_service.get_chat_history(empty_chat.id)
        
        assert len(empty_history) == 0, "Expected empty history"
        print(f"✓ Empty chat returns 0 messages")
        
        await session.commit()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
        # Print summary
        print("\nSummary:")
        print(f"  Test chat ID: {chat.id}")
        print(f"  Messages created: {len(messages_created)}")
        print(f"  Messages retrieved: {len(history)}")
        print(f"  Message types: user, bot, button")
        print(f"  Token usage tracked: Yes")
        print(f"  Chronological order: Yes")
        print(f"  Metadata support: Yes")


if __name__ == "__main__":
    asyncio.run(test_chat_history_endpoint())
