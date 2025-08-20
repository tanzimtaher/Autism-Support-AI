"""
Conversational UI for Autism Support App
Provides a conversational interface instead of form-based navigation.
"""

import streamlit as st
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our conversation engine
from knowledge.empathetic_conversation_engine import EmpatheticConversationEngine

# Page configuration
st.set_page_config(
    page_title="Chat with Autism Support Assistant",
    page_icon="💬",
    layout="wide"
)

# Initialize conversation engine
@st.cache_resource
def get_conversation_engine():
    return EmpatheticConversationEngine()

engine = get_conversation_engine()

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
    
    # Get conversation start from engine
    start_result = engine.start_conversation(st.session_state.user_profile)
    
    # Initialize conversation state - now we store the conversation_id
    st.session_state.conversation_id = start_result["conversation_id"]
    st.session_state.conversation_state = start_result["conversation_state"]
    
    # Add initial message to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": start_result["message"],
        "tone": start_result["tone"]
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
    
    # Process through conversation engine
    response_result = engine.process_user_input(
        user_input, 
        st.session_state.conversation_id
    )
    
    # Handle errors
    if "error" in response_result:
        st.error(response_result["error"])
        return
    
    # Add response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response_result["message"],
        "tone": response_result["tone"]
    })
    
    # Show safety alert if present
    if response_result.get("safety_alert"):
        st.error("🚨 **SAFETY ALERT** 🚨")
        if response_result.get("immediate_actions"):
            for action in response_result["immediate_actions"]:
                st.error(f"• {action}")
    
    # Show helpful resources if available
    if response_result.get("helpful_resources"):
        resources_text = "**Helpful Resources:**\n"
        for resource in response_result["helpful_resources"]:
            resources_text += f"• **{resource['name']}**: {resource['description']}\n"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": resources_text,
            "tone": "informative"
        })

def show_conversation_summary():
    """Show a summary of the current conversation."""
    if not hasattr(st.session_state, 'conversation_id') or not st.session_state.conversation_id:
        st.warning("No active conversation to summarize.")
        return
    
    summary = engine.get_conversation_summary(st.session_state.conversation_id)
    
    st.subheader("📋 Conversation Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Family Information:**")
        family_info = summary.get('family_information', {})
        st.write(f"• Parent Name: {family_info.get('parent_name', 'Not specified')}")
        st.write(f"• Role: {family_info.get('role', 'unknown').replace('_', ' ').title()}")
        st.write(f"• Child Name: {family_info.get('child_name', 'Not specified')}")
        st.write(f"• Child Age: {family_info.get('child_age', 'unknown')}")
        st.write(f"• Child Gender: {family_info.get('child_gender', 'Not specified')}")
        st.write(f"• Diagnosis Status: {family_info.get('diagnosis_status', 'unknown').replace('_', ' ').title()}")
    
    with col2:
        st.markdown("**Progress:**")
        progress_info = summary.get('conversation_progress', {})
        st.write(f"• Current Step: {progress_info.get('current_step', 'Entry Point')}")
        st.write(f"• Completed Steps: {len(progress_info.get('completed_steps', []))}")
        st.write(f"• Conversation Length: {progress_info.get('conversation_length', 0)} messages")
    
    st.markdown("**Next Recommendations:**")
    recommendations = summary.get("recommendations", {})
    for rec in recommendations.get("next_steps", []):
        st.write(f"• {rec}")
    
    # Show specific details if available
    specific_details = summary.get("specific_details", {})
    if specific_details.get("concerns_mentioned"):
        st.markdown("**Concerns Mentioned:**")
        for concern in specific_details["concerns_mentioned"]:
            st.write(f"• {concern}")
    
    if specific_details.get("challenges_strengths"):
        st.markdown("**Challenges & Strengths:**")
        for item in specific_details["challenges_strengths"]:
            st.write(f"• {item}")
    
    # Export conversation option
    if st.button("📥 Export Conversation"):
        export_conversation(summary)

def export_conversation(summary):
    """Export conversation summary and history as PDF."""
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph("Autism Support Conversation Summary", title_style))
    story.append(Spacer(1, 20))
    
    # User Profile Section
    story.append(Paragraph("User Profile", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    family_info = summary.get('family_information', {})
    profile_data = [
        ['Parent Name', family_info.get('parent_name', 'Not specified')],
        ['Role', family_info.get('role', 'unknown').replace('_', ' ').title()],
        ['Child Name', family_info.get('child_name', 'Not specified')],
        ['Child Age', family_info.get('child_age', 'unknown')],
        ['Child Gender', family_info.get('child_gender', 'Not specified')],
        ['Diagnosis Status', family_info.get('diagnosis_status', 'unknown').replace('_', ' ').title()],
    ]
    
    profile_table = Table(profile_data, colWidths=[2*inch, 4*inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 20))
    
    # Progress Section
    story.append(Paragraph("Progress", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    progress_info = summary.get('conversation_progress', {})
    progress_data = [
        ['Current Step', progress_info.get('current_step', 'Entry Point')],
        ['Completed Steps', str(len(progress_info.get('completed_steps', [])))],
        ['Conversation Length', str(progress_info.get('conversation_length', 0))]
    ]
    
    progress_table = Table(progress_data, colWidths=[2*inch, 4*inch])
    progress_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(progress_table)
    story.append(Spacer(1, 20))
    
    # Chat History Section
    story.append(Paragraph("Chat History", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    for i, message in enumerate(st.session_state.chat_history):
        role = "You" if message["role"] == "user" else "Assistant"
        content = message["content"]
        
        # Truncate long messages for PDF
        if len(content) > 200:
            content = content[:200] + "..."
        
        story.append(Paragraph(f"<b>{role}:</b>", styles['Normal']))
        story.append(Paragraph(content, styles['Normal']))
        story.append(Spacer(1, 8))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Create download button for PDF
    st.download_button(
        label="📥 Download Conversation as PDF",
        data=buffer.getvalue(),
        file_name="autism_support_conversation.pdf",
        mime="application/pdf",
        key="download_pdf"
    )
    
    # Also provide JSON option
    export_data = {
        "summary": summary,
        "chat_history": st.session_state.chat_history,
        "timestamp": str(st.session_state.get("conversation_state", {}).get("timestamp", ""))
    }
    
    json_str = json.dumps(export_data, indent=2)
    st.download_button(
        label="📄 Download as JSON",
        data=json_str,
        file_name="autism_support_conversation.json",
        mime="application/json",
        key="download_json"
    )
    
    st.success("Export options ready! Choose PDF or JSON format.")

def browse_topics_directly():
    """Navigate back to the main app for topic browsing."""
    # Clear conversation state to return to main app
    st.session_state.conversation_state = None
    st.session_state.conversation_id = None
    st.session_state.chat_history = []
    st.session_state.user_profile = None
    st.session_state.conversation_mode = False
    
    # Navigate back to main app - use st.experimental_rerun instead of switch_page
    st.experimental_rerun()

if __name__ == "__main__":
    main()
