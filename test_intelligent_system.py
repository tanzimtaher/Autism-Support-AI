"""
Test the Intelligent Conversation System
Simple test to verify the new system works.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from knowledge.response_synthesis_engine import ResponseSynthesisEngine
        print("✅ ResponseSynthesisEngine imported successfully")
        
        from knowledge.context_traversal_engine import ContextTraversalEngine
        print("✅ ContextTraversalEngine imported successfully")
        
        from knowledge.intelligent_conversation_manager import IntelligentConversationManager
        print("✅ IntelligentConversationManager imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of the intelligent system."""
    try:
        from knowledge.intelligent_conversation_manager import IntelligentConversationManager
        
        # Create manager instance
        manager = IntelligentConversationManager()
        print("✅ IntelligentConversationManager created successfully")
        
        # Test user profile
        test_profile = {
            "role": "parent_caregiver",
            "child_age": "3-5",
            "diagnosis_status": "diagnosed_no"
        }
        
        # Test conversation start
        start_result = manager.start_conversation(test_profile)
        print(f"✅ Conversation started: {start_result['conversation_id']}")
        print(f"   Context: {start_result['context_path']}")
        print(f"   Response: {start_result['response'][:100]}...")
        
        # Test user response processing
        user_input = "I'm concerned about my child's speech development"
        response_result = manager.process_user_response(user_input)
        print(f"✅ User response processed")
        print(f"   New context: {response_result['context_path']}")
        print(f"   Response: {response_result['response'][:100]}...")
        
        # Test conversation summary
        summary = manager.get_conversation_summary()
        print(f"✅ Conversation summary generated")
        print(f"   Topics: {len(summary['topics_discussed'])}")
        print(f"   Length: {summary['conversation_length']}")
        
        # Clean up
        manager.close()
        print("✅ Manager closed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Intelligent Conversation System")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("❌ Import tests failed")
        return False
    
    print()
    
    # Test functionality
    if not test_basic_functionality():
        print("❌ Functionality tests failed")
        return False
    
    print()
    print("🎉 All tests passed! Intelligent system is working.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
