"""
Conversational UI for Autism Support App
Provides a conversational interface using the new dual-index system.
"""

import streamlit as st
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our new conversation manager
from knowledge.intelligent_conversation_manager import IntelligentConversationManager

# Page configuration
st.set_page_config(
    page_title="Chat with Autism Support Assistant",
    page_icon="💬",
    layout="wide"
)

# Initialize conversation manager
@st.cache_resource
def get_conversation_manager():
    return IntelligentConversationManager()

manager = get_conversation_manager()

def main():
    st.title("💬 Autism Support Assistant")
    st.markdown("Hi! I'm here to help guide you through autism support and resources. I know this journey can feel overwhelming, and I'm here to listen and help.")
    
    # Initialize session state
    if "conversation_mode" not in st.session_state:
        st.session_state.conversation_mode = False
    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = None
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None
    
    # User profile collection (if not already collected)
    if not st.session_state.user_profile:
        collect_user_profile()
    else:
        # Show conversation interface
        show_conversation_interface()
    
    # Sidebar for additional options
    with st.sidebar:
        st.markdown("### Additional Options")
        
        if st.button("🔄 Start New Conversation"):
            st.session_state.conversation_state = None
            st.session_state.chat_history = []
            st.session_state.user_profile = None
            st.rerun()
        
        if st.button("📋 View Conversation Summary"):
            if st.session_state.conversation_state:
                show_conversation_summary()
        
        if st.button("🔍 Browse Topics Directly"):
            browse_topics_directly()

def collect_user_profile():
    """Collect user profile information for routing."""
    st.subheader("Let's get started")
    
    col1, col2 = st.columns(2)
    
    with col1:
        role = st.radio(
            "I am a:",
            ["parent_caregiver", "adult_self"],
            format_func=lambda x: "Parent/Caregiver" if x == "parent_caregiver" else "Adult (Self)"
        )
        
        diagnosis_status = st.radio(
            "Diagnosis status:",
            ["diagnosed_no", "diagnosed_yes"],
            format_func=lambda x: "No diagnosis yet" if x == "diagnosed_no" else "Has autism diagnosis"
        )
    
    with col2:
        if role == "parent_caregiver":
            child_age = st.selectbox(
                "Child's age:",
                ["0-3", "3-5", "6-12", "13-17", "18+"]
            )
            age_display = child_age
        else:
            child_age = "18+"
            age_display = "Adult"
        
        st.info(f"Age: {age_display}")
    
    # Additional context for better routing
    if role == "parent_caregiver" and diagnosis_status == "diagnosed_no":
        primary_concern = st.selectbox(
            "Primary concern:",
            ["developmental_delays", "communication", "social_behavior", "other"],
            format_func=lambda x: x.replace("_", " ").title()
        )
    else:
        primary_concern = "general"
    
    if st.button("Start Conversation"):
        st.session_state.user_profile = {
            "role": role,
            "diagnosis_status": diagnosis_status,
            "child_age": child_age,
            "primary_concern": primary_concern
        }
        
        # Start conversation
        start_conversation()
        st.rerun()

def start_conversation():
    """Start the conversation with the user profile."""
    if not st.session_state.user_profile:
        return
    
    # Get conversation start from manager
    start_result = manager.start_conversation(st.session_state.user_profile)
    
    # Initialize conversation state - store the conversation_id and context
    st.session_state.conversation_id = start_result["conversation_id"]
    st.session_state.conversation_state = {
        "context_path": start_result["context_path"],
        "available_paths": start_result["available_paths"]
    }
    
    # Add initial message to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": start_result["response"],
        "context_path": start_result["context_path"]
    })
    
    # No more conversation starters - just empathetic questions

def show_conversation_interface():
    """Show the main conversation interface."""
    if not st.session_state.conversation_state:
        st.error("Conversation not initialized. Please start over.")
        return
    
    # Display chat history
    st.subheader("Conversation")
    
    for message in st.session_state.chat_history:
        if message["role"] == "assistant":
            # Apply tone-based styling for empathetic conversation
            tone = message.get("tone", "neutral")
            if tone in ["urgent", "urgent_caring"]:
                st.error(message["content"])
            elif tone in ["supportive", "empathetic_supportive", "warm_supportive"]:
                st.success(message["content"])
            elif tone in ["informative", "helpful"]:
                st.info(message["content"])
            else:
                st.write(message["content"])
        else:
            st.write(f"**You:** {message['content']}")
    
    # User input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Process user input
        process_user_input(user_input)
        
        # Rerun to update the display
        st.rerun()

def process_user_input(user_input):
    """Process user input and get response."""
    if not hasattr(st.session_state, 'conversation_id') or not st.session_state.conversation_id:
        st.error("Conversation not initialized. Please start over.")
        return
    
    # Process through conversation manager
    response_result = manager.process_user_response(user_input)
    
    # Handle errors
    if "error" in response_result:
        st.error(response_result["error"])
        return
    
    # Add response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response_result["response"],
        "context_path": response_result["context_path"]
    })
    
    # Update conversation state
    st.session_state.conversation_state = {
        "context_path": response_result["context_path"],
        "available_paths": response_result["available_paths"]
    }
    
    # Show safety alert if present
    if response_result.get("safety_warning"):
        st.error("🚨 **SAFETY ALERT** 🚨")
        st.error(response_result["safety_warning"])
    
    # Show next suggestions if available
    if response_result.get("next_suggestions"):
        suggestions_text = "**Next Steps:**\n"
        for suggestion in response_result["next_suggestions"][:3]:
            suggestions_text += f"• {suggestion}\n"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": suggestions_text,
            "tone": "informative"
        })

def show_conversation_summary():
    """Show a summary of the current conversation."""
    if not hasattr(st.session_state, 'conversation_id') or not st.session_state.conversation_id:
        st.warning("No active conversation to summarize.")
        return
    
    summary = manager.get_conversation_summary()
    
    st.subheader("📋 Conversation Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**User Profile:**")
        user_profile = summary.get('user_profile', {})
        st.write(f"• Role: {user_profile.get('role', 'unknown').replace('_', ' ').title()}")
        st.write(f"• Child Age: {user_profile.get('child_age', 'unknown')}")
        st.write(f"• Diagnosis Status: {user_profile.get('diagnosis_status', 'unknown').replace('_', ' ').title()}")
        if user_profile.get('child_name'):
            st.write(f"• Child Name: {user_profile['child_name']}")
        if user_profile.get('concerns'):
            st.write(f"• Concerns: {', '.join(user_profile['concerns'])}")
    
    with col2:
        st.markdown("**Progress:**")
        st.write(f"• Current Context: {summary.get('final_context', 'Entry Point')}")
        st.write(f"• Topics Discussed: {len(summary.get('topics_discussed', []))}")
        st.write(f"• Conversation Length: {summary.get('conversation_length', 0)} messages")
    
    st.markdown("**Next Recommendations:**")
    recommendations = summary.get("next_recommendations", [])
    if recommendations:
        for rec in recommendations:
            st.write(f"• {rec}")
    else:
        st.write("• Continue with current conversation flow")
    
    # Show topics discussed
    topics = summary.get("topics_discussed", [])
    if topics:
        st.markdown("**Topics Discussed:**")
        for topic in topics:
            st.write(f"• {topic}")
    
    # Export conversation option
    if st.button("📥 Export Conversation"):
        export_conversation(summary)

def export_conversation(summary):
    """Export conversation summary and history as JSON."""
    # Create export data
    export_data = {
        "summary": summary,
        "chat_history": st.session_state.chat_history,
        "user_profile": st.session_state.user_profile,
        "conversation_id": st.session_state.conversation_id,
        "timestamp": str(st.session_state.get("conversation_state", {}).get("context_path", ""))
    }
    
    # Export as JSON
    json_str = json.dumps(export_data, indent=2)
    st.download_button(
        label="📄 Download Conversation as JSON",
        data=json_str,
        file_name="autism_support_conversation.json",
        mime="application/json",
        key="download_json"
    )
    
    st.success("✅ Export ready! Download the JSON file to save your conversation.")
    
    # Show a preview of what's being exported
    with st.expander("📋 Export Preview"):
        st.json(export_data)

def browse_topics_directly():
    """Navigate back to the main app for topic browsing."""
    # Clear conversation state to return to main app
    st.session_state.conversation_state = None
    st.session_state.conversation_id = None
    st.session_state.chat_history = []
    st.session_state.user_profile = None
    st.session_state.conversation_mode = False
    
    # Navigate back to main app
    st.rerun()

if __name__ == "__main__":
    main()
