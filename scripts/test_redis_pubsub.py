#!/usr/bin/env python3
# Test Redis Pub/Sub Connection and Message Flow
# Usage: python scripts/test_redis_pubsub.py

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.redis.event_manager import redis_event_manager
from config.settings import settings


async def test_connection():
    """Test Redis connection"""
    print("🔍 Testing Redis connection...")
    try:
        await redis_event_manager.connect()
        is_healthy = await redis_event_manager.health_check()
        if is_healthy:
            print("✅ Redis connection successful!")
            return True
        else:
            print("❌ Redis health check failed!")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_publish():
    """Test publishing event"""
    print("\n📤 Testing event publishing...")
    try:
        session_id = 123
        event = {
            "session_id": session_id,
            "user_message": "Test message",
            "request_id": "test-uuid-1234",
            "type": "intent_detected"
        }
        
        channel = await redis_event_manager.get_channel_pattern(session_id, "intent")
        subscribers = await redis_event_manager.publish(channel, event)
        
        print(f"✅ Event published to channel: {channel}")
        print(f"   Subscribers notified: {subscribers}")
        return True
    except Exception as e:
        print(f"❌ Publish failed: {e}")
        return False


async def test_rendering_event():
    """Test rendering progress event"""
    print("\n📊 Testing rendering progress event...")
    try:
        session_id = 123
        subscribers = await redis_event_manager.publish_rendering_event(
            session_id=session_id,
            progress=50,
            status="rendering"
        )
        print(f"✅ Rendering event published")
        print(f"   Subscribers notified: {subscribers}")
        return True
    except Exception as e:
        print(f"❌ Rendering event failed: {e}")
        return False


async def test_ready_event():
    """Test tree ready event"""
    print("\n🌳 Testing tree ready event...")
    try:
        session_id = 123
        tree_data = {
            "id": "root",
            "name": "Python Programming",
            "children": [
                {"id": "1", "name": "Basics", "status": "completed"},
                {"id": "2", "name": "Advanced", "status": "in_progress"}
            ]
        }
        
        subscribers = await redis_event_manager.publish_ready_event(
            session_id=session_id,
            tree_data=tree_data
        )
        print(f"✅ Tree ready event published")
        print(f"   Subscribers notified: {subscribers}")
        return True
    except Exception as e:
        print(f"❌ Ready event failed: {e}")
        return False


async def test_error_event():
    """Test error event"""
    print("\n⚠️  Testing error event...")
    try:
        session_id = 123
        subscribers = await redis_event_manager.publish_error_event(
            session_id=session_id,
            error_message="Test error occurred",
            error_type="processing_error"
        )
        print(f"✅ Error event published")
        print(f"   Subscribers notified: {subscribers}")
        return True
    except Exception as e:
        print(f"❌ Error event failed: {e}")
        return False


async def test_channel_pattern():
    """Test channel name generation"""
    print("\n🔗 Testing channel pattern generation...")
    try:
        session_id = 456
        
        intent_channel = await redis_event_manager.get_channel_pattern(session_id, "intent")
        render_channel = await redis_event_manager.get_channel_pattern(session_id, "render")
        ready_channel = await redis_event_manager.get_channel_pattern(session_id, "ready")
        error_channel = await redis_event_manager.get_channel_pattern(session_id, "error")
        
        print(f"✅ Channel patterns generated:")
        print(f"   Intent: {intent_channel}")
        print(f"   Render: {render_channel}")
        print(f"   Ready:  {ready_channel}")
        print(f"   Error:  {error_channel}")
        return True
    except Exception as e:
        print(f"❌ Channel pattern test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Redis Pub/Sub Test Suite")
    print("=" * 60)
    print(f"\n📍 Redis URL: {settings.REDIS_URL}")
    
    tests_passed = 0
    tests_total = 0
    
    try:
        # Test connection
        tests_total += 1
        if await test_connection():
            tests_passed += 1
        
        # Test channel pattern
        tests_total += 1
        if await test_channel_pattern():
            tests_passed += 1
        
        # Test publishing different event types
        tests_total += 1
        if await test_publish():
            tests_passed += 1
        
        tests_total += 1
        if await test_rendering_event():
            tests_passed += 1
        
        tests_total += 1
        if await test_ready_event():
            tests_passed += 1
        
        tests_total += 1
        if await test_error_event():
            tests_passed += 1
        
    finally:
        await redis_event_manager.disconnect()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{tests_total} passed")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
