#!/usr/bin/env python3
"""
Test script for the Conversation Memory Persistence System
Tests all components to ensure they're working correctly.
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_memory_manager():
    """Test the ConversationMemoryManager class."""
    print("🧪 Testing ConversationMemoryManager...")
    
    try:
        from knowledge.conversation_memory_manager import ConversationMemoryManager
        
        # Create memory manager
        test_user_id = "test_user_123"
        memory_manager = ConversationMemoryManager(test_user_id)
        print(f"✅ Memory manager created for user: {test_user_id}")
        
        # Test storing chat messages
        test_message = {
            "role": "user",
            "content": "My child struggles with social interactions",
            "timestamp": datetime.now().isoformat(),
            "conversation_type": "general",
            "context_path": "social_skills",
            "sources": [],
            "next_suggestions": []
        }
        
        result = memory_manager.store_chat_message(test_message)
        print(f"✅ Chat message stored: {result}")
        
        # Test storing assistant message
        assistant_message = {
            "role": "assistant",
            "content": "Social skills can be challenging. Let me help you with some strategies.",
            "timestamp": datetime.now().isoformat(),
            "conversation_type": "general",
            "context_path": "social_skills",
            "sources": [{"source": "knowledge_base", "type": "guidance"}],
            "next_suggestions": ["Learn more about social skills", "Find local support groups"]
        }
        
        result = memory_manager.store_chat_message(assistant_message)
        print(f"✅ Assistant message stored: {result}")
        
        # Test insight extraction
        test_conversation = [test_message, assistant_message]
        insights = memory_manager.extract_and_store_insights(test_conversation)
        print(f"✅ Insights extracted: {len(insights.get('topics_discussed', []))} topics")
        
        # Test memory retrieval
        context = memory_manager.retrieve_relevant_context("social skills", limit=3)
        print(f"✅ Memory context retrieved: {len(context.get('chat_history', []))} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qdrant_memory_collections():
    """Test Qdrant memory collection functions."""
    print("\n🧪 Testing Qdrant Memory Collections...")
    
    try:
        from rag.qdrant_client import ensure_memory_collections, store_conversation_memory, search_conversation_memory
        
        test_user_id = "test_user_456"
        
        # Test collection creation
        ensure_memory_collections(test_user_id)
        print(f"✅ Memory collections ensured for user: {test_user_id}")
        
        # Test storing memory
        test_memory_data = {
            "type": "chat_history",
            "content": "Test conversation about autism support",
            "data": {"topic": "autism", "concern": "communication"},
            "timestamp": datetime.now().isoformat()
        }
        
        result = store_conversation_memory(test_user_id, "chat_history", test_memory_data)
        print(f"✅ Memory stored: {result}")
        
        # Test searching memory
        results = search_conversation_memory(test_user_id, "autism support", limit=2)
        print(f"✅ Memory search results: {len(results)} items found")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_intelligent_conversation_manager():
    """Test the IntelligentConversationManager with memory integration."""
    print("\n🧪 Testing IntelligentConversationManager Memory Integration...")
    
    try:
        from knowledge.intelligent_conversation_manager import IntelligentConversationManager
        
        # Create manager
        manager = IntelligentConversationManager()
        print("✅ IntelligentConversationManager created")
        
        # Test with user profile
        test_profile = {
            "user_id": "test_user_789",
            "role": "parent_caregiver",
            "child_age": "6-12",
            "diagnosis_status": "diagnosed_yes"
        }
        
        # Test conversation start
        start_result = manager.start_conversation(test_profile)
        print(f"✅ Conversation started: {start_result.get('conversation_id', 'N/A')}")
        
        # Test user response processing
        user_input = "My child needs help with communication skills"
        response_result = manager.process_user_response(user_input)
        print(f"✅ User response processed: {len(response_result.get('response', ''))} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Intelligent conversation manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_response_synthesis_with_memory():
    """Test response synthesis engine with memory context."""
    print("\n🧪 Testing Response Synthesis with Memory Context...")
    
    try:
        from knowledge.response_synthesis_engine import ResponseSynthesisEngine
        
        # Create engine
        engine = ResponseSynthesisEngine()
        print("✅ ResponseSynthesisEngine created")
        
        # Test synthesis with memory context
        test_query = "What strategies help with autism communication?"
        test_profile = {"user_id": "test_user_999"}
        test_history = [
            {"role": "user", "content": "My child has autism"},
            {"role": "assistant", "content": "I understand. Let me help you."}
        ]
        
        # This will test the memory context integration
        response = engine._llm_synthesize(
            user_query=test_query,
            mongodb_content={"response": "Communication strategies for autism"},
            web_content=[],
            user_profile=test_profile,
            conversation_history=test_history,
            vector_results=[]
        )
        
        print(f"✅ Response synthesized: {len(response)} chars")
        return True
        
    except Exception as e:
        print(f"❌ Response synthesis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests and provide summary."""
    print("🚀 Starting Conversation Memory System Tests...\n")
    
    tests = [
        ("Memory Manager", test_memory_manager),
        ("Qdrant Memory Collections", test_qdrant_memory_collections),
        ("Intelligent Conversation Manager", test_intelligent_conversation_manager),
        ("Response Synthesis with Memory", test_response_synthesis_with_memory)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Conversation memory system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)


