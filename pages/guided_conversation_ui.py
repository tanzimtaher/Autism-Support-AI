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

# Import our guided conversation engine
from knowledge.guided_conversation_engine import GuidedConversationEngine

# Page configuration
st.set_page_config(
    page_title="Guided Autism Support",
    page_icon="🎯",
    layout="wide"
)

# Initialize guided conversation engine
@st.cache_resource
def get_guided_engine():
    return GuidedConversationEngine()

engine = get_guided_engine()

def main():
    st.title("🎯 Guided Autism Support")
    st.markdown("I'll guide you through this step by step. Let me ask you a few questions to understand your situation and provide the most relevant help.")
    
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
        
        if st.button("🔄 Start New Guided Session"):
            st.session_state.guided_conversation_id = None
            st.session_state.guided_chat_history = []
            st.session_state.user_profile = None
            st.session_state.flow_progress = {}
            st.rerun()
        
        if st.button("📋 View Guided Summary"):
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
    """Start the guided conversation with the user profile."""
    if not st.session_state.user_profile:
        return
    
    # Get guided conversation start from engine
    start_result = engine.start_guided_conversation(st.session_state.user_profile)
    
    # Initialize guided conversation state
    st.session_state.guided_conversation_id = start_result["conversation_id"]
    st.session_state.flow_progress = {
        "flow_name": start_result["flow_name"],
        "current_step": start_result["current_step"],
        "total_steps": start_result["total_steps"]
    }
    
    # Add initial message to chat history
    st.session_state.guided_chat_history.append({
        "role": "assistant",
        "content": start_result["message"],
        "tone": start_result["tone"],
        "step": start_result["current_step"],
        "total_steps": start_result["total_steps"]
    })

def show_guided_conversation_interface():
    """Show the guided conversation interface."""
    if not st.session_state.guided_conversation_id:
        st.error("Guided conversation not initialized. Please start over.")
        return
    
    # Show flow progress
    if st.session_state.flow_progress:
        flow_name = st.session_state.flow_progress["flow_name"]
        current_step = st.session_state.flow_progress["current_step"]
        total_steps = st.session_state.flow_progress["total_steps"]
        
        st.subheader(f"🎯 {flow_name}")
        
        # Progress bar
        progress = current_step / total_steps
        st.progress(progress)
        st.caption(f"Step {current_step} of {total_steps}")
    
    # Display guided chat history
    st.markdown("### Our Conversation")
    
    for message in st.session_state.guided_chat_history:
        if message["role"] == "assistant":
            # Apply tone-based styling for guided conversation
            tone = message.get("tone", "neutral")
            if tone == "empathetic_guide":
                st.success(f"**Guide:** {message['content']}")
            elif tone == "supportive_summary":
                st.info(f"**Guide:** {message['content']}")
            else:
                st.write(f"**Guide:** {message['content']}")
        else:
            st.write(f"**You:** {message['content']}")
    
    # User input
    user_input = st.chat_input("Type your response here...")
    
    if user_input:
        # Add user message to history
        st.session_state.guided_chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Process user input through guided engine
        process_guided_input(user_input)
        
        # Rerun to update the display
        st.rerun()

def process_guided_input(user_input):
    """Process user input through the guided conversation engine."""
    if not st.session_state.guided_conversation_id:
        st.error("Guided conversation not initialized. Please start over.")
        return
    
    # Process through guided conversation engine
    response_result = engine.process_guided_response(
        user_input, 
        st.session_state.guided_conversation_id
    )
    
    # Handle errors
    if "error" in response_result:
        st.error(response_result["error"])
        return
    
    # Add response to chat history
    st.session_state.guided_chat_history.append({
        "role": "assistant",
        "content": response_result["message"],
        "tone": response_result["tone"],
        "step": response_result.get("current_step", 1),
        "total_steps": response_result.get("total_steps", 1)
    })
    
    # Update flow progress
    if "current_step" in response_result:
        st.session_state.flow_progress["current_step"] = response_result["current_step"]
    
    # Handle flow completion
    if response_result.get("flow_completed"):
        st.session_state.flow_progress["completed"] = True
        
        # Show next actions if available
        if "next_actions" in response_result:
            st.session_state.next_actions = response_result["next_actions"]

def show_guided_summary():
    """Show a summary of the guided conversation."""
    if not st.session_state.guided_conversation_id:
        st.warning("No active guided conversation to summarize.")
        return
    
    summary = engine.get_conversation_summary(st.session_state.guided_conversation_id)
    
    st.subheader("📋 Guided Conversation Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Conversation Flow:**")
        st.write(f"• Flow: {summary['flow_name']}")
        st.write(f"• Current Step: {summary['current_step']}")
        st.write(f"• Steps Completed: {summary['steps_completed']}")
    
    with col2:
        st.markdown("**User Profile:**")
        profile = summary['user_profile']
        st.write(f"• Role: {profile.get('role', 'unknown').replace('_', ' ').title()}")
        st.write(f"• Diagnosis Status: {profile.get('diagnosis_status', 'unknown').replace('_', ' ').title()}")
        if profile.get('child_age'):
            st.write(f"• Child Age: {profile['child_age']}")
        if profile.get('child_name'):
            st.write(f"• Child Name: {profile['child_name']}")
    
    # Show step history
    if summary.get('step_history'):
        st.markdown("**Conversation Steps:**")
        for i, step in enumerate(summary['step_history'], 1):
            st.write(f"**Step {i}:** {step['step_id']}")
            st.write(f"Your response: {step['user_response'][:100]}...")
            st.write("---")
    
    # Show extracted information
    if summary.get('extracted_info'):
        st.markdown("**Information Gathered:**")
        for key, value in summary['extracted_info'].items():
            st.write(f"• {key}: {value}")

if __name__ == "__main__":
    main()
