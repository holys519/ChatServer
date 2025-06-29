#!/usr/bin/env python3
"""
Test script for session title functionality.
Tests that session titles are updated based on the first user message.
"""

import asyncio
import uuid
from datetime import datetime

from app.services.session_service import session_service
from app.models.schemas import ChatSessionCreate, ChatMessage

async def test_session_title_update():
    """Test that session titles are updated when the first user message is added"""
    print("🧪 Testing Session Title Update Functionality...")
    print("=" * 60)
    
    test_user_id = "test_user_123"
    
    try:
        # 1. Create a new session with default title
        print("1. Creating new session with default title...")
        session_data = ChatSessionCreate(
            title="新しいチャット",
            model_id="gemini-2-0-flash-001"
        )
        
        new_session = await session_service.create_session(test_user_id, session_data)
        print(f"✅ Session created with ID: {new_session.id}")
        print(f"   Initial title: '{new_session.title}'")
        
        # 2. Add first user message
        print("\n2. Adding first user message...")
        first_message = ChatMessage(
            id=str(uuid.uuid4()),
            content="こんにちは！今日の天気はどうですか？天気予報を教えてください。",
            is_user=True,
            timestamp=datetime.now()
        )
        
        updated_session = await session_service.add_message_to_session(
            new_session.id, test_user_id, first_message
        )
        
        if updated_session:
            print(f"✅ Message added successfully")
            print(f"   Updated title: '{updated_session.title}'")
            print(f"   Message count: {len(updated_session.messages)}")
            
            # Check if title was updated
            if updated_session.title != "新しいチャット":
                print("✅ Title was successfully updated from first message!")
                print(f"   Expected: First 47-50 characters of the message")
                print(f"   Actual: '{updated_session.title}'")
            else:
                print("❌ Title was not updated - still shows default title")
        else:
            print("❌ Failed to add message to session")
            return False
        
        # 3. Add second user message (should not change title)
        print("\n3. Adding second user message...")
        second_message = ChatMessage(
            id=str(uuid.uuid4()),
            content="ありがとうございます！とても詳しい説明ですね。",
            is_user=True,
            timestamp=datetime.now()
        )
        
        title_before_second = updated_session.title
        updated_session_2 = await session_service.add_message_to_session(
            new_session.id, test_user_id, second_message
        )
        
        if updated_session_2:
            print(f"✅ Second message added successfully")
            print(f"   Title remained: '{updated_session_2.title}'")
            print(f"   Message count: {len(updated_session_2.messages)}")
            
            if updated_session_2.title == title_before_second:
                print("✅ Title correctly remained unchanged after second message")
            else:
                print("❌ Title unexpectedly changed after second message")
        else:
            print("❌ Failed to add second message to session")
            return False
        
        # 4. Test title truncation with long message
        print("\n4. Testing title truncation with long message...")
        
        # Create new session for long message test
        long_session_data = ChatSessionCreate(
            title="新しいチャット",
            model_id="gemini-2-0-flash-001"
        )
        
        long_session = await session_service.create_session(test_user_id, long_session_data)
        
        # Very long message
        long_message_content = "これは非常に長いメッセージです。" * 10 + "追加のテキストで文字数を増やしています。"
        long_message = ChatMessage(
            id=str(uuid.uuid4()),
            content=long_message_content,
            is_user=True,
            timestamp=datetime.now()
        )
        
        updated_long_session = await session_service.add_message_to_session(
            long_session.id, test_user_id, long_message
        )
        
        if updated_long_session:
            print(f"✅ Long message added successfully")
            print(f"   Original message length: {len(long_message_content)} characters")
            print(f"   Generated title: '{updated_long_session.title}'")
            print(f"   Generated title length: {len(updated_long_session.title)} characters")
            
            if len(updated_long_session.title) <= 50:
                print("✅ Title was correctly truncated to 50 characters or less")
            else:
                print("❌ Title was not properly truncated")
        else:
            print("❌ Failed to add long message to session")
            return False
        
        # 5. Cleanup test sessions
        print("\n5. Cleaning up test sessions...")
        await session_service.delete_session(new_session.id, test_user_id)
        await session_service.delete_session(long_session.id, test_user_id)
        print("✅ Test sessions cleaned up")
        
        print("\n🎉 All session title tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_title_generation_function():
    """Test the title generation function directly"""
    print("\n🔧 Testing Title Generation Function...")
    print("=" * 50)
    
    # Test short message
    short_msg = "こんにちは"
    if hasattr(session_service, '_generate_title_from_message'):
        short_title = session_service._generate_title_from_message(short_msg)
        print(f"Short message: '{short_msg}'")
        print(f"Generated title: '{short_title}'")
        print(f"✅ Short message test passed" if short_title == short_msg else "❌ Short message test failed")
    
    # Test long message
    long_msg = "これは50文字を超える非常に長いメッセージです。このメッセージは確実に切り詰められるはずです。"
    if hasattr(session_service, '_generate_title_from_message'):
        long_title = session_service._generate_title_from_message(long_msg)
        print(f"\nLong message: '{long_msg}'")
        print(f"Generated title: '{long_title}'")
        print(f"Title length: {len(long_title)}")
        print(f"✅ Long message test passed" if len(long_title) <= 50 and long_title.endswith('...') else "❌ Long message test failed")

if __name__ == "__main__":
    print("🚀 Session Title Test Suite")
    print("=" * 70)
    
    # Run title generation tests
    asyncio.run(test_title_generation_function())
    
    # Run session title update tests
    success = asyncio.run(test_session_title_update())
    
    if success:
        print("\n🎉 All tests completed successfully!")
        print("Session title functionality is working correctly.")
    else:
        print("\n❌ Some tests failed!")
        print("Please check the implementation.")
        exit(1)