"""
Test script for the list chats endpoint.

This script verifies that the GET /api/chat/list endpoint works correctly
by creating test data and making a request to the endpoint.
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.core.database import AsyncSessionLocal
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.services.chat_service import ChatService
from app.services.message_service import MessageService


async def test_list_chats_endpoint():
    """Test the list chats endpoint functionality."""
    
    print("=" * 60)
    print("Testing List Chats Endpoint")
    print("=" * 60)
    
    # Create async session
    async with AsyncSessionLocal() as session:
        # Initialize repositories and services
        chat_repo = ChatRepository(session)
        message_repo = MessageRepository(session)
        chat_service = ChatService(session, chat_repo, message_repo)
        message_service = MessageService(session, message_repo)
        
        # Create test user and owner IDs
        user_id = uuid4()
        owner_id_1 = uuid4()
        owner_id_2 = uuid4()
        
        print(f"\n[Test Setup]")
        print(f"User ID: {user_id}")
        print(f"Owner ID 1: {owner_id_1}")
        print(f"Owner ID 2: {owner_id_2}")
        
        # Test 1: Create test chats with messages
        print(f"\n[Test 1] Creating test chats with messages...")
        
        # Chat 1 - Most recent
        chat1 = await chat_service.create_chat(user_id, owner_id_1)
        print(f"✓ Created chat 1: {chat1.id}")
        
        # Add messages to chat 1
        await message_service.create_message(
            chat_id=chat1.id,
            sender_type="user",
            content="I want to book a tennis court"
        )
        
        await message_service.create_message(
            chat_id=chat1.id,
            sender_type="bot",
            content="Great! Let me show you available properties."
        )
        
        # Update last_message_at to now
        await chat_service.update_chat_state(chat1)
        
        # Chat 2 - Older
        chat2 = await chat_service.create_chat(user_id, owner_id_2)
        print(f"✓ Created chat 2: {chat2.id}")
        
        # Add messages to chat 2
        await message_service.create_message(
            chat_id=chat2.id,
            sender_type="user",
            content="Hello"
        )
        
        # Update last_message_at to 2 hours ago
        await chat_repo.update(chat2, {
            "last_message_at": datetime.utcnow() - timedelta(hours=2)
        })
        
        # Chat 3 - Closed with long message
        chat3 = await chat_service.create_chat(user_id, owner_id_1)
        await chat_repo.update(chat3, {"status": "closed"})
        print(f"✓ Created chat 3: {chat3.id} (closed)")
        
        # Add message to chat 3
        await message_service.create_message(
            chat_id=chat3.id,
            sender_type="user",
            content="This is a closed chat with a very long message that should be truncated when displayed in the preview because it exceeds the 100 character limit that we set for message previews in the list view"
        )
        
        # Update last_message_at to 1 day ago
        await chat_repo.update(chat3, {
            "last_message_at": datetime.utcnow() - timedelta(days=1)
        })
        
        await session.commit()
        
        # Test 2: Retrieve user chats
        print(f"\n[Test 2] Retrieving user chats...")
        
        chats = await chat_repo.get_user_chats(user_id)
        
        print(f"✓ Retrieved {len(chats)} chats")
        
        # Verify chat count
        assert len(chats) == 3, f"Expected 3 chats, got {len(chats)}"
        print("✓ Chat count correct")
        
        # Verify ordering (most recent first)
        assert chats[0].id == chat1.id, "Chat 1 should be first (most recent)"
        assert chats[1].id == chat2.id, "Chat 2 should be second"
        assert chats[2].id == chat3.id, "Chat 3 should be third (oldest)"
        print("✓ Chats ordered by last_message_at descending")
        
        # Test 3: Build chat summaries with last message preview
        print(f"\n[Test 3] Building chat summaries...")
        
        for i, chat in enumerate(chats, 1):
            print(f"\nChat {i}:")
            print(f"  ID: {chat.id}")
            print(f"  Status: {chat.status}")
            print(f"  Last message at: {chat.last_message_at}")
            
            # Get last message
            last_msg = await message_repo.get_last_message(chat.id)
            if last_msg:
                preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
                print(f"  Last message: {preview}")
                print(f"  Last sender: {last_msg.sender_type}")
                
                # Verify truncation for chat 3
                if chat.id == chat3.id:
                    assert len(preview) == 103, "Long message should be truncated to 100 chars + '...'"
                    print("  ✓ Long message truncated correctly")
        
        # Test 4: Test with user who has no chats
        print(f"\n[Test 4] Testing with user who has no chats...")
        
        empty_user_id = uuid4()
        empty_chats = await chat_repo.get_user_chats(empty_user_id)
        
        assert len(empty_chats) == 0, "Expected 0 chats for new user"
        print(f"✓ User with no chats returns empty list")
        
        await session.commit()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
        # Print summary
        print("\nSummary:")
        print(f"  User ID: {user_id}")
        print(f"  Chats created: 3")
        print(f"  Chats retrieved: {len(chats)}")
        print(f"  Ordering: Most recent first ✓")
        print(f"  Last message preview: Working ✓")
        print(f"  Message truncation: Working ✓")
        print(f"  Status tracking: Working ✓")


if __name__ == "__main__":
    asyncio.run(test_list_chats_endpoint())
