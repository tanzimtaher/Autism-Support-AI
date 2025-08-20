"""
Guided Conversation UI for Autism Support App
Provides proactive, guided conversations that orchestrate the user experience.
"""

import streamlit as st
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our intelligent conversation manager
from knowledge.intelligent_conversation_manager import IntelligentConversationManager

# Page configuration
st.set_page_config(
    page_title="Guided Autism Support",
    page_icon="🎯",
    layout="wide"
)

# Initialize intelligent conversation manager
@st.cache_resource
def get_intelligent_manager():
    return IntelligentConversationManager()

manager = get_intelligent_manager()

def main():
    st.title("🎯 Intelligent Autism Support")
    st.markdown("I'll intelligently guide you through autism support using my knowledge base and real-time information. Let me ask you a few questions to understand your situation and provide the most relevant help.")
    
    # Initialize session state
    if "guided_conversation_id" not in st.session_state:
        st.session_state.guided_conversation_id = None
    if "guided_chat_history" not in st.session_state:
        st.session_state.guided_chat_history = []
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None
    if "flow_progress" not in st.session_state:
        st.session_state.flow_progress = {}
    
    # User profile collection (if not already collected)
    if not st.session_state.user_profile:
        collect_user_profile()
    else:
        # Show guided conversation interface
        show_guided_conversation_interface()
    
    # Sidebar for additional options
    with st.sidebar:
        st.markdown("### Guided Conversation Options")
        
        if st.button("🔄 Start New Intelligent Session"):
            st.session_state.guided_conversation_id = None
            st.session_state.guided_chat_history = []
            st.session_state.user_profile = None
            st.session_state.current_context = None
            st.session_state.available_paths = []
            st.rerun()
        
        if st.button("📋 View Intelligent Summary"):
            if st.session_state.guided_conversation_id:
                show_guided_summary()
        
        if st.button("🔍 Switch to Free Chat"):
            st.switch_page("pages/conversational_ui.py")

def collect_user_profile():
    """Collect user profile information for guided conversation."""
    st.subheader("Let's get started with your guided session")
    
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
    
    if st.button("🚀 Start Guided Session"):
        st.session_state.user_profile = {
            "role": role,
            "diagnosis_status": diagnosis_status,
            "child_age": child_age,
            "primary_concern": primary_concern
        }
        
        # Start guided conversation
        start_guided_conversation()
        st.rerun()

def start_guided_conversation():
    """Start the intelligent guided conversation with the user profile."""
    if not st.session_state.user_profile:
        return
    
    # Get intelligent conversation start from manager
    start_result = manager.start_conversation(st.session_state.user_profile)
    
    # Initialize guided conversation state
    st.session_state.guided_conversation_id = start_result["conversation_id"]
    st.session_state.current_context = start_result["context_path"]
    st.session_state.available_paths = start_result["available_paths"]
    
    # Add initial message to chat history
    st.session_state.guided_chat_history.append({
        "role": "assistant",
        "content": start_result["response"],
        "context_path": start_result["context_path"],
        "next_suggestions": start_result["next_suggestions"]
    })

def show_guided_conversation_interface():
    """Show the intelligent guided conversation interface."""
    if not st.session_state.guided_conversation_id:
        st.error("Guided conversation not initialized. Please start over.")
        return
    
    # Show current context and available paths
    if st.session_state.get("current_context"):
        st.subheader(f"🎯 Current Topic: {st.session_state.current_context}")
        
        # Show available conversation paths
        if st.session_state.get("available_paths"):
            st.markdown("**🛤️ Available conversation paths:**")
            cols = st.columns(3)
            for i, path in enumerate(st.session_state.available_paths[:6]):  # Show up to 6 paths
                col_idx = i % 3
                with cols[col_idx]:
                    if st.button(f"Explore: {path}", key=f"path_{path}"):
                        # Navigate to selected path
                        response_result = manager.process_user_response(
                            f"Navigate to {path}", 
                            selected_path=path
                        )
                        st.session_state.current_context = response_result["context_path"]
                        st.session_state.available_paths = response_result["available_paths"]
                        st.rerun()
    
    # Display intelligent chat history
    st.markdown("### 🤖 Our Intelligent Conversation")
    
    for message in st.session_state.guided_chat_history:
        if message["role"] == "assistant":
            # Show AI response with context
            st.success(f"**🤖 AI Assistant:** {message['content']}")
            if message.get("context_path"):
                st.caption(f"Context: {message['context_path']}")
            if message.get("next_suggestions"):
                st.markdown("**💡 Suggested next steps:**")
                for suggestion in message["next_suggestions"][:3]:  # Show top 3
                    st.markdown(f"- {suggestion}")
        else:
            st.write(f"**👤 You:** {message['content']}")
        st.write("---")
    
    # User input
    user_input = st.chat_input("Ask me anything about autism support...")
    
    if user_input:
        # Add user message to history
        st.session_state.guided_chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Process user input through intelligent manager
        process_intelligent_input(user_input)
        
        # Rerun to update the display
        st.rerun()

def process_intelligent_input(user_input):
    """Process user input through the intelligent conversation manager."""
    if not st.session_state.guided_conversation_id:
        st.error("Guided conversation not initialized. Please start over.")
        return
    
    # Process through intelligent conversation manager
    response_result = manager.process_user_response(user_input)
    
    # Add response to chat history
    st.session_state.guided_chat_history.append({
        "role": "assistant",
        "content": response_result["response"],
        "context_path": response_result["context_path"],
        "next_suggestions": response_result["next_suggestions"],
        "confidence": response_result.get("confidence", 0.0),
        "sources": response_result.get("sources", [])
    })
    
    # Update session state
    st.session_state.current_context = response_result["context_path"]
    st.session_state.available_paths = response_result["available_paths"]

def show_guided_summary():
    """Show a summary of the intelligent guided conversation."""
    if not st.session_state.guided_conversation_id:
        st.warning("No active guided conversation to summarize.")
        return
    
    summary = manager.get_conversation_summary()
    
    st.subheader("📋 Intelligent Conversation Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Conversation Overview:**")
        st.write(f"• Topics Discussed: {len(summary['topics_discussed'])}")
        st.write(f"• Conversation Length: {summary['conversation_length']} messages")
        st.write(f"• Final Context: {summary['final_context']}")
    
    with col2:
        st.markdown("**User Profile:**")
        profile = summary['user_profile']
        st.write(f"• Role: {profile.get('role', 'unknown').replace('_', ' ').title()}")
        st.write(f"• Diagnosis Status: {profile.get('diagnosis_status', 'unknown').replace('_', ' ').title()}")
        if profile.get('child_age'):
            st.write(f"• Child Age: {profile['child_age']}")
    
    # Show topics discussed
    if summary.get('topics_discussed'):
        st.markdown("**Topics Discussed:**")
        for topic in summary['topics_discussed']:
            st.write(f"• {topic}")
    
    # Show AI-generated summary
    if summary.get('summary'):
        st.markdown("**AI-Generated Summary:**")
        st.info(summary['summary'])
    
    # Show next recommendations
    if summary.get('next_recommendations'):
        st.markdown("**Recommended Next Steps:**")
        for rec in summary['next_recommendations']:
            st.write(f"• {rec}")

if __name__ == "__main__":
    main()
