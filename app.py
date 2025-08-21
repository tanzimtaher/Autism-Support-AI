import streamlit as st
import openai, pymongo
import math
import sys
import os
import json
from pathlib import Path
from pymongo import MongoClient
from rag.query_engine import query_index

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our intelligent conversation manager
from knowledge.intelligent_conversation_manager import IntelligentConversationManager

# ---- keys & db
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
mongo = MongoClient("mongodb://localhost:27017/")["autism_ai"]["knowledge"]

# Initialize the conversation manager
@st.cache_resource
def get_conversation_manager():
    return IntelligentConversationManager()

manager = get_conversation_manager()

# ---- helper functions (define these first)
def show_topic_information_with_rag(context_path):
    """Show information about the selected topic with RAG integration."""
    st.subheader("📘 Topic Information")
    
    # Get MongoDB content
    doc = fetch_mongo(context_path)
    rag_chunks, rag_answer = [], ""
    
    # Try to get RAG results for enhanced context
    try:
        rag_result = query_index(context_path)
        rag_answer = rag_result["answer"]
        rag_chunks = rag_result["chunks"]
    except Exception as e:
        print(f"RAG query failed: {e}")
    
    if doc:
        # Show MongoDB content
        st.info(doc["response"])
        
        # If we have RAG results, show them as additional context
        if rag_chunks:
            with st.expander("🔍 Additional Context from Knowledge Base", expanded=False):
                st.markdown("**Enhanced information from our knowledge base:**")
                for i, chunk in enumerate(rag_chunks[:3], 1):  # Show top 3 results
                    text = chunk.get("text", "").strip()
                    source = chunk.get("source", "Unknown")
                    st.markdown(f"**[{i}]** {text[:300]}...\n\n_Source: {source}_")
        
        # Set up conversation history
        st.session_state.chat_history = [{"role": "assistant", "content": doc["response"]}]
        st.session_state.initial_response_shown = True
        
        # Show follow-up chat interface
        st.subheader("💬 Ask Follow-up Questions")
        user_prompt = st.chat_input("Ask a question about this topic...")
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            # Get additional RAG results for the user's question
            try:
                user_rag_result = query_index(user_prompt)
                user_rag_chunks = user_rag_result["chunks"]
            except:
                user_rag_chunks = []
            
            # Combine MongoDB and RAG for response
            base_response = doc["response"]
            tone = doc.get("tone", "supportive")
            answer = llm_synthesize(user_prompt, base_response, user_rag_chunks, tone)
            
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()
            
    else:
        # If no MongoDB content, try RAG only
        if rag_chunks:
            st.info(rag_answer)
            st.session_state.chat_history = [{"role": "assistant", "content": rag_answer}]
            st.session_state.initial_response_shown = True
        else:
            st.warning("Information for this topic is not available yet.")
            st.session_state.chat_history = []
            st.session_state.initial_response_shown = False

def show_topic_information(context_path):
    """Show information about the selected topic."""
    st.subheader("📘 Topic Information")
    
    doc = fetch_mongo(context_path)
    if doc:
        st.info(doc["response"])
        st.session_state.chat_history = [{"role": "assistant", "content": doc["response"]}]
        st.session_state.initial_response_shown = True
    else:
        st.warning("Information for this topic is not available yet.")
        st.session_state.chat_history = []
        st.session_state.initial_response_shown = False

def fetch_mongo(path): 
    return mongo.find_one({"context_path": path})

def get_vector_store_documents(user_id: str = "default"):
    """Get documents that are actually stored in the vector database."""
    try:
        from rag.qdrant_client import ensure_collection
        
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        
        if not qdr:
            return []
        
        # Get all documents from the vector store
        existing_points = qdr.scroll(
            collection_name=collection_name,
            limit=1000,
            with_payload=True
        )[0]
        
        # Group by filename and collect metadata
        doc_info = {}
        for point in existing_points:
            payload = point.payload
            if payload and "filename" in payload:
                filename = payload["filename"]
                if filename not in doc_info:
                    doc_info[filename] = {
                        "filename": filename,
                        "chunks": 0,
                        "content_samples": [],
                        "metadata": payload.get("metadata", {}),
                        "user_id": payload.get("user_id", user_id),
                        "upload_timestamp": payload.get("metadata", {}).get("upload_timestamp", "Unknown"),
                        "file_size": payload.get("metadata", {}).get("file_size", 0)
                    }
                doc_info[filename]["chunks"] += 1
                
                # Store a sample of content (first 100 chars)
                if payload.get("content") and len(doc_info[filename]["content_samples"]) < 3:
                    content_sample = payload["content"][:100] + "..." if len(payload["content"]) > 100 else payload["content"]
                    doc_info[filename]["content_samples"].append(content_sample)
        
        return list(doc_info.values())
        
    except Exception as e:
        print(f"❌ Error getting vector store documents: {e}")
        return []

def delete_document_from_vector_store(filename: str, user_id: str = "default"):
    """Delete a document from the vector store."""
    try:
        from rag.qdrant_client import ensure_collection
        
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        
        if qdr:
            # Delete all chunks for this file
            result = qdr.delete(
                collection_name=collection_name,
                points_selector={"filter": {"must": [{"key": "filename", "match": {"value": filename}}]}}
            )
            
            # Also delete the physical file if it exists
            user_docs_dir = Path(f"data/user_docs/{user_id}")
            file_path = user_docs_dir / filename
            if file_path.exists():
                file_path.unlink()
            
            st.success(f"✅ {filename} removed from knowledge base")
            print(f"🗑️ Deleted {filename} from vector store and disk")
            
    except Exception as e:
        st.error(f"❌ Error deleting {filename}: {e}")
        print(f"❌ Error deleting document: {e}")

def sync_documents_with_vector_store():
    """Sync uploaded documents with vector store - remove files that no longer exist."""
    try:
        user_id = st.session_state.user_profile.get("user_id", "default")
        user_docs_dir = Path(f"data/user_docs/{user_id}")
        
        if not user_docs_dir.exists():
            return 0
        
        # Get documents in vector store
        vector_docs = get_vector_store_documents(user_id)
        vector_filenames = {doc["filename"] for doc in vector_docs}
        
        # Get actual files on disk
        disk_files = {f.name for f in user_docs_dir.glob("*") if f.is_file()}
        
        # Find files that exist in vector store but not on disk
        orphaned_files = vector_filenames - disk_files
        
        if orphaned_files:
            # Remove orphaned documents from vector store
            from rag.qdrant_client import ensure_collection
            collection_name = f"user_docs_{user_id}"
            qdr = ensure_collection(collection_name, size=1536)
            
            if qdr:
                for filename in orphaned_files:
                    # Delete all chunks for this file
                    qdr.delete(
                        collection_name=collection_name,
                        points_selector={"filter": {"must": [{"key": "filename", "match": {"value": filename}}]}}
                    )
                    print(f"🗑️ Removed orphaned document from vector store: {filename}")
        
        return len(orphaned_files)
        
    except Exception as e:
        print(f"❌ Error syncing documents: {e}")
        return 0

def apply_temporal_weighting(rag_chunks, decay_days=365):
    """Apply temporal weighting to prioritize newer content."""
    import time
    
    if not rag_chunks:
        return rag_chunks
    
    current_time = time.time()
    weighted_chunks = []
    
    for chunk in rag_chunks:
        # Get timestamp from chunk metadata if available
        timestamp = chunk.get("upload_timestamp", current_time)
        if isinstance(timestamp, str):
            try:
                timestamp = float(timestamp)
            except:
                timestamp = current_time
        
        # Calculate age in days
        age_days = (current_time - timestamp) / (24 * 3600)
        
        # Apply temporal decay (exponential decay)
        temporal_weight = math.exp(-age_days / decay_days)
        
        # Create weighted chunk
        weighted_chunk = chunk.copy()
        weighted_chunk["temporal_weight"] = temporal_weight
        weighted_chunk["age_days"] = age_days
        weighted_chunks.append(weighted_chunk)
    
    # Sort by temporal weight (newer content first)
    weighted_chunks.sort(key=lambda x: x.get("temporal_weight", 1.0), reverse=True)
    
    return weighted_chunks

def llm_synthesize(user_msg, base_resp, rag_chunks, tone):
    # Use user profile from session state if available
    profile_str = ""
    if st.session_state.user_profile:
        profile = st.session_state.user_profile
        profile_str = f"Role:{profile.get('role', 'parent')}, Age:{profile.get('child_age', 'unknown')}, Diagnosis:{profile.get('diagnosis_status', 'unknown')}"
    
    # Apply temporal weighting to RAG chunks (prioritize newer content)
    weighted_chunks = apply_temporal_weighting(rag_chunks)
    
    sys = f"""You are a concise, empathetic autism-support assistant. 
User profile: {profile_str}
Tone: {tone}
"""
    if base_resp:
        sys += f"\nStructured guidance:\n{base_resp}"
    if rag_chunks:
        sys += "\nRelevant document insights:"
        for i, chunk in enumerate(rag_chunks, 1):
            sys += f"\n[{i}] {chunk['text'][:250]}... (source: {chunk['source']})"

    messages = [
        {"role": "system", "content": sys.strip()},
        {"role": "user", "content": user_msg}
    ]
    return client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, temperature=0.7
    ).choices[0].message.content.strip()

def collect_user_profile():
    """Collect user profile information for intelligent routing."""
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
        # Store in session state
        st.session_state.user_profile = {
            "role": role,
            "diagnosis_status": diagnosis_status,
            "child_age": child_age,
            "primary_concern": primary_concern
        }
        
        # Start intelligent conversation
        start_unified_conversation()
        st.rerun()

def start_unified_conversation():
    """Start the unified intelligent conversation."""
    if not st.session_state.user_profile:
        return
    
    # Get conversation start from manager
    start_result = manager.start_conversation(st.session_state.user_profile)
    
    # Initialize conversation state
    st.session_state.conversation_id = start_result["conversation_id"]
    
    # Add initial message to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": start_result["response"],
        "context_path": start_result["context_path"],
        "conversation_type": "guided"  # Start with guided approach
    })

def show_unified_conversation_interface():
    """Show the unified conversation interface that adapts automatically."""
    
    # Check if we're in browse mode
    if st.session_state.get("browse_mode", False):
        show_topic_browsing()
        return
    
    # Sidebar for additional options
    with st.sidebar:
        st.markdown("### 💬 Conversation Options")
        
        if st.button("🔄 Start New Conversation"):
            st.session_state.chat_history = []
            st.session_state.user_profile = None
            st.session_state.conversation_id = None
            st.session_state.browse_mode = False
            st.session_state.browse_selections = {}
            st.session_state.screening_questions = []
            st.session_state.current_screening_step = 0
            st.rerun()
        
        if st.button("📋 View Conversation Summary"):
            show_conversation_summary()
        
        # Document management
        st.markdown("---")
        st.markdown("### 📎 Document Management")
        
        if st.button("📚 View My Documents"):
            show_user_documents()
        
        if st.button("🗑️ Clear All Documents"):
            clear_user_documents()
        
    # Topic browsing option
    st.markdown("---")
    st.markdown("### 🔍 Browse Topics")
    
    if st.button("📖 Browse Specific Topics"):
        st.session_state.browse_mode = True
        st.rerun()
    
    # Main conversation area
    st.subheader("Our Conversation")
    
    # Display chat history with adaptive styling
    for message in st.session_state.chat_history:
        if message["role"] == "assistant":
            # Apply tone-based styling
            tone = message.get("tone", "neutral")
            conversation_type = message.get("conversation_type", "adaptive")
            
            if conversation_type == "guided":
                st.success(f"**🤖 AI Assistant:** {message['content']}")
                if message.get("next_suggestions"):
                    st.markdown("**💡 Suggested next steps:**")
                    for suggestion in message["next_suggestions"][:3]:
                        st.markdown(f"- {suggestion}")
            else:
                st.info(f"**🤖 AI Assistant:** {message['content']}")
            
            if message.get("context_path"):
                st.caption(f"Context: {message['context_path']}")
        else:
            st.write(f"**👤 You:** {message['content']}")
        st.write("---")
    
    # Document upload section
    with st.expander("📎 Upload Patient Documents", expanded=False):
        st.markdown("""
        **Upload patient-specific documents for personalized guidance:**
        - 📄 Medical reports and evaluations
        - 🧩 Assessment results
        - 📝 Therapy notes
        - 📊 Progress reports
        - 📋 IEP documents
        
        **Privacy**: These documents are stored privately and only used for your conversations.
        """)
        
        uploaded_files = st.file_uploader(
            label="Upload patient documents (PDF, TXT, DOCX)",
            type=["pdf", "txt", "docx"],
            accept_multiple_files=True,
            key="patient_docs_uploader"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} document(s) uploaded")
            
            # Process and store documents
            for uploaded_file in uploaded_files:
                process_patient_document(uploaded_file)
            
            if st.button("🔄 Process Documents for This Conversation"):
                process_uploaded_documents()
    
    # User input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Process user input through intelligent manager
        process_unified_input(user_input)
        
        # Rerun to update the display
        st.rerun()

def process_unified_input(user_input):
    """Process user input through the intelligent conversation manager."""
    if not st.session_state.conversation_id:
        st.error("Conversation not initialized. Please start over.")
        return
    
    # Check if we're in screening mode
    if st.session_state.screening_questions and st.session_state.current_screening_step < len(st.session_state.screening_questions):
        # Handle screening question response
        handle_screening_response(user_input)
        return
    
    # Regular conversation processing
    response_result = manager.process_user_response(user_input)
    
    # Determine conversation type based on response characteristics
    conversation_type = "guided" if response_result.get("next_suggestions") else "free_form"
    
    # Add response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response_result["response"],
        "context_path": response_result["context_path"],
        "conversation_type": conversation_type,
        "next_suggestions": response_result.get("next_suggestions"),
        "confidence": response_result.get("confidence", 0.0)
    })
    
    # Show safety alert if present
    if response_result.get("safety_warning"):
        st.error("🚨 **SAFETY ALERT** ��")
        st.error(response_result["safety_warning"])

def handle_screening_response(user_input):
    """Handle responses to screening questions."""
    # Store the user's response
    if "screening_responses" not in st.session_state:
        st.session_state.screening_responses = []
    
    st.session_state.screening_responses.append(user_input)
    
    # Add user response to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input
    })
    
    # Move to next question or provide assessment
    st.session_state.current_screening_step += 1
    
    if st.session_state.current_screening_step < len(st.session_state.screening_questions):
        # Ask next question
        next_question = st.session_state.screening_questions[st.session_state.current_screening_step]
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": next_question,
            "conversation_type": "guided"
        })
    else:
        # Provide assessment based on responses
        assessment = generate_screening_assessment(st.session_state.screening_responses)
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": assessment,
            "conversation_type": "guided"
        })
        
        # Clear screening state
        st.session_state.screening_questions = []
        st.session_state.current_screening_step = 0

def generate_screening_assessment(responses):
    """Generate assessment based on screening responses."""
    return """Thank you for answering those questions. Based on your responses, I'd like to provide you with some personalized guidance. 

Let me ask you a few more specific questions to better understand your situation and provide the most relevant resources and next steps."""

def get_screening_questions(context_path):
    """Get appropriate screening questions based on context."""
    if "screening" in context_path.lower():
        return [
            "What specific behaviors or concerns have you noticed?",
            "How long have you been observing these behaviors?",
            "Are there any family members with similar conditions?",
            "What is your child's current age?",
            "Have you discussed these concerns with a healthcare provider?"
        ]
    elif "diagnosed_no" in context_path:
        return [
            "What made you decide to seek information about autism?",
            "What specific behaviors are you concerned about?",
            "How old is your child?",
            "Have you noticed any developmental delays?"
        ]
    else:
        return [
            "What specific support are you looking for?",
            "What challenges are you currently facing?",
            "What resources have you already tried?"
        ]

def show_topic_browsing():
    """Show topic browsing interface within the unified UI."""
    # Add a way to exit browse mode
    if st.button("← Back to Conversation"):
        st.session_state.browse_mode = False
        st.session_state.browse_selections = {}
        st.rerun()
    
    st.subheader("🔍 Browse Specific Topics")
    
    # Use session state to maintain selections
    if "diagnosed" not in st.session_state.browse_selections:
        diagnosed = st.radio("Has your child been diagnosed with autism?", ["No", "Yes"])
        if st.button("Continue"):
            st.session_state.browse_selections["diagnosed"] = diagnosed
            st.rerun()
    else:
        diagnosed = st.session_state.browse_selections["diagnosed"]
        st.info(f"Diagnosis Status: {diagnosed}")
        
    base_path = "diagnosed_yes" if diagnosed == "Yes" else "diagnosed_no"
    
    # Get topics from new structure with better labels
    topics = mongo.find({"context_path": {"$regex": f"^{base_path}"}, "type": "content"})
    categories = sorted({doc["context_path"].split(".")[1] for doc in topics if len(doc["context_path"].split(".")) > 1})
    
    # Create user-friendly category labels
    category_labels = {
        "entry_point": "Getting Started",
        "monitor_vs_screen": "Monitoring vs Screening",
        "screening_options": "Screening Options",
        "interpretation_routes": "Understanding Results",
        "not_yet_evaluated": "Not Yet Evaluated",
        "no_dx_but_concerns": "Concerns Without Diagnosis",
        "at_home_resources": "At-Home Resources",
        "legal_emergency_intro": "Legal & Emergency",
        "support_affording": "Affording Support",
        "find_resources": "Finding Resources",
        "legal_and_emergency": "Legal & Emergency Support"
    }
    
    if categories:
        # Display categories with user-friendly labels
        category_options = []
        for cat in categories:
            label = category_labels.get(cat, cat.replace("_", " ").title())
            category_options.append((label, cat))
        
        if "selected_category" not in st.session_state.browse_selections:
            selected_category_label = st.selectbox(
                "Select a category",
                options=[opt[0] for opt in category_options],
                help="Choose the category that best matches your situation"
            )
            
            if st.button("Select Category"):
                selected_category = next(opt[1] for opt in category_options if opt[0] == selected_category_label)
                st.session_state.browse_selections["selected_category"] = selected_category
                st.rerun()
        else:
            selected_category = st.session_state.browse_selections["selected_category"]
            st.info(f"Selected Category: {category_labels.get(selected_category, selected_category.replace('_', ' ').title())}")
        
        # Get the category content to check for options/routes/branches
        category_doc = mongo.find_one({"context_path": f"{base_path}.{selected_category}"})
        
        if category_doc and category_doc.get("options"):
            # Show options if available
            st.subheader("Available Options")
            options = category_doc["options"]
            option_labels = []
            for key, option in options.items():
                label = option.get("label", key.replace("_", " ").title())
                option_labels.append((label, key))
            
            if "selected_option" not in st.session_state.browse_selections:
                selected_option_label = st.selectbox(
                    "Choose an option",
                    options=[opt[0] for opt in option_labels],
                    help="Select a specific option for detailed information"
                )
                
                if st.button("Select Option"):
                    selected_option = next(opt[1] for opt in option_labels if opt[0] == selected_option_label)
                    st.session_state.browse_selections["selected_option"] = selected_option
                    st.rerun()
            else:
                selected_option = st.session_state.browse_selections["selected_option"]
                st.info(f"Selected Option: {selected_option.replace('_', ' ').title()}")
                
                if st.button("Start Conversation About This Topic"):
                    context_path = f"{base_path}.{selected_category}.options.{selected_option}"
                    start_topic_conversation(context_path)
                    st.rerun()
            
        elif category_doc and category_doc.get("routes"):
            # Show routes if available
            st.subheader("Available Routes")
            routes = category_doc["routes"]
            route_labels = []
            for key, route in routes.items():
                label = route.get("label", key.replace("_", " ").title())
                route_labels.append((label, key))
            
            if "selected_route" not in st.session_state.browse_selections:
                selected_route_label = st.selectbox(
                    "Choose a route",
                    options=[opt[0] for opt in route_labels],
                    help="Select a specific route for detailed information"
                )
                
                if st.button("Select Route"):
                    selected_route = next(opt[1] for opt in route_labels if opt[0] == selected_route_label)
                    st.session_state.browse_selections["selected_route"] = selected_route
                    st.rerun()
            else:
                selected_route = st.session_state.browse_selections["selected_route"]
                st.info(f"Selected Route: {selected_route.replace('_', ' ').title()}")
                
                if st.button("Start Conversation About This Topic"):
                    context_path = f"{base_path}.{selected_category}.routes.{selected_route}"
                    start_topic_conversation(context_path)
                    st.rerun()
            
        elif category_doc and category_doc.get("branches"):
            # Show branches if available
            st.subheader("Available Branches")
            branches = category_doc["branches"]
            branch_labels = []
            for key, branch in branches.items():
                label = branch.get("label", key.replace("_", " ").title())
                branch_labels.append((label, key))
            
            if "selected_branch" not in st.session_state.browse_selections:
                selected_branch_label = st.selectbox(
                    "Choose a branch",
                    options=[opt[0] for opt in branch_labels],
                    help="Select a specific branch for detailed information"
                )
                
                if st.button("Select Branch"):
                    selected_branch = next(opt[1] for opt in branch_labels if opt[0] == selected_branch_label)
                    st.session_state.browse_selections["selected_branch"] = selected_branch
                    st.rerun()
            else:
                selected_branch = st.session_state.browse_selections["selected_branch"]
                st.info(f"Selected Branch: {selected_branch.replace('_', ' ').title()}")
                
                if st.button("Start Conversation About This Topic"):
                    context_path = f"{base_path}.{selected_category}.branches.{selected_branch}"
                    start_topic_conversation(context_path)
                    st.rerun()
            
        else:
            # Get subtopics for regular categories
            subtopics = mongo.find({"context_path": {"$regex": f"^{base_path}\\.{selected_category}"}, "type": "content"})
            subkeys = []
            for doc in subtopics:
                path_parts = doc["context_path"].split(".")
                if len(path_parts) > 2:
                    subkeys.append(".".join(path_parts[2:]))
            
            subkeys = sorted(list(set(subkeys)))
            
            if subkeys:
                # Create user-friendly subtopic labels
                subtopic_labels = {
                    "required_docs": "Required Documents",
                    "screening_tools": "Screening Tools",
                    "developmental_milestones": "Developmental Milestones",
                    "red_flags": "Red Flags to Watch For",
                    "next_steps": "Next Steps",
                    "resources": "Resources & Support",
                    "legal_rights": "Legal Rights",
                    "emergency_contacts": "Emergency Contacts"
                }
                
                subtopic_options = ["(none)"] + [subtopic_labels.get(sub, sub.replace("_", " ").title()) for sub in subkeys]
                
                if "selected_subtopic" not in st.session_state.browse_selections:
                    selected_subtopic_label = st.selectbox(
                        "Choose a specific topic (optional)",
                        subtopic_options,
                        help="Select a specific subtopic for more detailed information"
                    )
                    
                    if st.button("Select Subtopic"):
                        if selected_subtopic_label != "(none)":
                            selected_subtopic = next(sub for sub in subkeys if subtopic_labels.get(sub, sub.replace("_", " ").title()) == selected_subtopic_label)
                            st.session_state.browse_selections["selected_subtopic"] = selected_subtopic
                        else:
                            st.session_state.browse_selections["selected_subtopic"] = None
                        st.rerun()
                else:
                    selected_subtopic = st.session_state.browse_selections["selected_subtopic"]
                    if selected_subtopic:
                        st.info(f"Selected Subtopic: {subtopic_labels.get(selected_subtopic, selected_subtopic.replace('_', ' ').title())}")
                        context_path = f"{base_path}.{selected_category}.{selected_subtopic}"
                    else:
                        st.info("No specific subtopic selected")
                        context_path = f"{base_path}.{selected_category}"
                    
                    if st.button("Start Conversation About This Topic"):
                        start_topic_conversation(context_path)
                        st.rerun()
            else:
                if st.button("Start Conversation About This Topic"):
                    context_path = f"{base_path}.{selected_category}"
                    start_topic_conversation(context_path)
                    st.rerun()
    else:
        st.warning("No topics found for this category. The knowledge base may need to be updated.")

def start_topic_conversation(context_path):
    """Start a guided conversation about a specific topic."""
    # Initialize screening questions based on the topic
    st.session_state.screening_questions = get_screening_questions(context_path)
    st.session_state.current_screening_step = 0
    
    # Add initial topic message to conversation
    topic_doc = fetch_mongo(context_path)
    if topic_doc:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"I'd like to help you with {context_path.replace('_', ' ').title()}. Let me ask you a few questions to better understand your situation.",
            "context_path": context_path,
            "conversation_type": "guided"
        })
    
    # Exit browse mode and return to conversation
    st.session_state.browse_mode = False
    st.session_state.browse_selections = {}

def show_conversation_summary():
    """Show an improved conversation summary."""
    if not hasattr(st.session_state, 'conversation_id') or not st.session_state.conversation_id:
        st.warning("No active conversation to summarize.")
        return
    
    summary = manager.get_conversation_summary()
    
    # Improve the summary display
    improved_summary = improve_conversation_summary_display(summary)
    
    st.subheader("📋 Conversation Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**User Profile:**")
        user_profile = improved_summary['user_profile']
        st.write(f"• Role: {user_profile['role']}")
        st.write(f"• Child Age: {user_profile['child_age']}")
        st.write(f"• Diagnosis Status: {user_profile['diagnosis_status']}")
        if user_profile['child_name'] != 'Not specified':
            st.write(f"• Child Name: {user_profile['child_name']}")
        st.write(f"• Concerns: {user_profile['concerns']}")
    
    with col2:
        st.markdown("**Progress:**")
        progress = improved_summary['progress']
        st.write(f"• Current Context: {progress['current_context']}")
        st.write(f"• Topics Discussed: {progress['topics_discussed_count']}")
        st.write(f"• Conversation Length: {progress['conversation_length']} messages")
    
    st.markdown("**Next Recommendations:**")
    recommendations = improved_summary['recommendations']
    for rec in recommendations:
        st.write(f"• {rec}")
    
    # Show topics discussed with user-friendly labels
    topics = improved_summary['topics_discussed']
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
    with st.expander("�� Export Preview"):
        st.json(export_data)

def process_patient_document(uploaded_file):
    """Process and store a patient document."""
    try:
        # Create user-specific document directory
        user_id = st.session_state.user_profile.get("user_id", "default")
        user_docs_dir = Path(f"data/user_docs/{user_id}")
        user_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the file
        file_path = user_docs_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Immediately ingest into vector store
        from rag.ingest_user_docs import ingest_user_documents
        success_count = ingest_user_documents(user_id, str(user_docs_dir))
        
        if success_count > 0:
            st.success(f"✅ {uploaded_file.name} uploaded and processed into knowledge base!")
        else:
            # Check if it was a duplicate
            vector_docs = get_vector_store_documents(user_id)
            if any(doc["filename"] == uploaded_file.name for doc in vector_docs):
                st.info(f"📄 {uploaded_file.name} already exists in knowledge base")
            else:
                st.warning(f"⚠️ {uploaded_file.name} uploaded but not processed")
            
    except Exception as e:
        st.error(f"❌ Error processing {uploaded_file.name}: {e}")

def process_uploaded_documents():
    """Process uploaded documents and add to user's private vector store."""
    try:
        # First sync to remove any orphaned documents
        removed_count = sync_documents_with_vector_store()
        if removed_count > 0:
            st.info(f"🔄 Cleaned up {removed_count} orphaned document(s) from knowledge base")
        
        # Get documents from vector store
        user_id = st.session_state.user_profile.get("user_id", "default")
        vector_docs = get_vector_store_documents(user_id)
        
        if vector_docs:
            st.success(f"✅ {len(vector_docs)} document(s) available in your private knowledge base!")
            st.info("💡 I can now reference information from your documents in our conversation.")
            
            # Show document summary
            with st.expander("📋 Document Summary"):
                for doc in vector_docs:
                    st.write(f"• **{doc['filename']}** ({doc['chunks']} chunks)")
                    if doc['content_samples']:
                        st.write(f"  Sample: {doc['content_samples'][0]}")
        else:
            st.warning("⚠️ No documents found in your knowledge base")
            
    except Exception as e:
        st.error(f"❌ Error processing documents: {e}")

def show_user_documents():
    """Display documents that are actually in the vector store."""
    user_id = st.session_state.user_profile.get("user_id", "default")
    vector_docs = get_vector_store_documents(user_id)
    
    if not vector_docs:
        st.info("No documents found in your knowledge base.")
        return
    
    st.subheader("📚 Documents in Your Knowledge Base")
    st.info(f"Found {len(vector_docs)} document(s) with {sum(doc['chunks'] for doc in vector_docs)} total chunks")
    
    for doc in vector_docs:
        with st.expander(f"📄 {doc['filename']} ({doc['chunks']} chunks)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**File:** {doc['filename']}")
                st.write(f"**Chunks:** {doc['chunks']}")
                st.write(f"**Size:** {doc['file_size']} bytes")
                st.write(f"**Uploaded:** {doc['upload_timestamp']}")
                
                if doc['content_samples']:
                    st.write("**Content Samples:**")
                    for i, sample in enumerate(doc['content_samples'][:2]):
                        st.write(f"  {i+1}. {sample}")
            
            with col2:
                # Check if file still exists on disk
                user_docs_dir = Path(f"data/user_docs/{user_id}")
                file_path = user_docs_dir / doc['filename']
                
                if file_path.exists():
                    st.download_button(
                        label="📥 Download",
                        data=open(file_path, "rb").read(),
                        file_name=doc['filename'],
                        mime=None,
                        key=f"download_{doc['filename']}"
                    )
                    
                    if st.button(f"🗑️ Delete", key=f"delete_{doc['filename']}"):
                        delete_document_from_vector_store(doc['filename'], user_id)
                        st.rerun()
                else:
                    st.warning("⚠️ File missing from disk")
                    if st.button(f"🗑️ Remove from DB", key=f"remove_{doc['filename']}"):
                        delete_document_from_vector_store(doc['filename'], user_id)
                        st.rerun()

def delete_document(filename):
    """Delete a specific document from both session state and vector store."""
    delete_document_from_vector_store(filename, st.session_state.user_profile.get("user_id", "default"))
    
    # Also remove from session state if it exists there
    if st.session_state.get("uploaded_documents"):
        st.session_state.uploaded_documents = [
            doc for doc in st.session_state.uploaded_documents if doc["filename"] != filename
        ]

def clear_user_documents():
    """Clear all documents from both session state and vector store."""
    try:
        user_id = st.session_state.user_profile.get("user_id", "default")
        
        # Clear from vector store
        from rag.qdrant_client import ensure_collection
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        
        if qdr:
            # Delete all documents for this user
            result = qdr.delete(
                collection_name=collection_name,
                points_selector={"filter": {"must": [{"key": "user_id", "match": {"value": user_id}}]}}
            )
        
        # Clear physical files
        user_docs_dir = Path(f"data/user_docs/{user_id}")
        if user_docs_dir.exists():
            for file_path in user_docs_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        
        # Clear session state
        if st.session_state.get("uploaded_documents"):
            st.session_state.uploaded_documents = []
        
        st.success("✅ All documents cleared from knowledge base and storage")
        
    except Exception as e:
        st.error(f"❌ Error clearing documents: {e}")


def get_user_friendly_context_label(context_path):
    """Convert technical context paths to user-friendly labels."""
    if not context_path:
        return "Getting Started"
    
    # Comprehensive mapping of technical paths to user-friendly labels
    context_labels = {
        # Main entry points
        "diagnosed_no.entry_point": "Getting Started - No Diagnosis",
        "diagnosed_yes.entry_point": "Getting Started - With Diagnosis",
        
        # Screening and monitoring
        "diagnosed_no.monitor_vs_screen": "Monitoring vs Screening",
        "diagnosed_no.screening_options": "Screening Options",
        "diagnosed_no.interpretation_routes": "Understanding Screening Results",
        
        # Not yet evaluated paths
        "diagnosed_no.not_yet_evaluated": "Not Yet Evaluated",
        "diagnosed_no.no_dx_but_concerns": "Concerns Without Diagnosis",
        "diagnosed_no.at_home_resources": "At-Home Resources",
        
        # Legal and emergency
        "diagnosed_no.legal_emergency_intro": "Legal & Emergency Support",
        "diagnosed_yes.legal_and_emergency": "Legal & Emergency Support",
        
        # Support and resources
        "diagnosed_yes.support_affording": "Affording Support",
        "diagnosed_yes.find_resources": "Finding Resources",
        
        # Specific topics
        "required_docs": "Required Documents",
        "screening_tools": "Screening Tools",
        "developmental_milestones": "Developmental Milestones",
        "red_flags": "Red Flags to Watch For",
        "next_steps": "Next Steps",
        "resources": "Resources & Support",
        "legal_rights": "Legal Rights",
        "emergency_contacts": "Emergency Contacts",
        
        # Default fallbacks
        "conversation_summary": "Conversation Summary",
        "Entry Point": "Getting Started"
    }
    
    # Try exact match first
    if context_path in context_labels:
        return context_labels[context_path]
    
    # Try partial matches for nested paths
    for key, label in context_labels.items():
        if context_path.startswith(key):
            return label
    
    # Fallback: convert underscores to spaces and title case
    return context_path.replace("_", " ").title()

def improve_conversation_summary_display(summary):
    """Improve the conversation summary display with better formatting and logic."""
    
    # Fix user profile display
    user_profile = summary.get('user_profile', {})
    
    # Clean up diagnosis status
    diagnosis_status = user_profile.get('diagnosis_status', 'unknown')
    if diagnosis_status == 'diagnosed_yes':
        diagnosis_display = "Diagnosed"
    elif diagnosis_status == 'diagnosed_no':
        diagnosis_display = "Not Diagnosed"
    else:
        diagnosis_display = diagnosis_status.replace('_', ' ').title()
    
    # Clean up child name (fix "Has" issue)
    child_name = user_profile.get('child_name', '')
    if child_name and child_name.lower() in ['has', 'yes', 'no', 'unknown']:
        child_name = 'Not specified'
    
    # Clean up role
    role = user_profile.get('role', 'unknown')
    if role == 'parent_caregiver':
        role_display = "Parent/Caregiver"
    else:
        role_display = role.replace('_', ' ').title()
    
    # Clean up concerns
    concerns = user_profile.get('concerns', [])
    if isinstance(concerns, str):
        concerns = [concerns]
    concerns_display = ', '.join(concerns) if concerns else 'Not specified'
    
    # Get user-friendly context label
    context_path = summary.get('final_context', 'Entry Point')
    context_label = get_user_friendly_context_label(context_path)
    
    # Generate better recommendations
    recommendations = summary.get("next_recommendations", [])
    if not recommendations or len(recommendations) == 0:
        # Generate contextual recommendations based on user profile and context
        if diagnosis_status == 'diagnosed_no':
            recommendations = [
                "Schedule a developmental screening",
                "Learn about early intervention services",
                "Connect with local support groups"
            ]
        elif diagnosis_status == 'diagnosed_yes':
            recommendations = [
                "Explore treatment and therapy options",
                "Find local autism support resources",
                "Learn about educational rights and IEPs"
            ]
        else:
            recommendations = [
                "Continue exploring autism support topics",
                "Consider speaking with a healthcare provider",
                "Learn more about developmental milestones"
            ]
    
    # Clean up topics discussed
    topics = summary.get("topics_discussed", [])
    topic_labels = []
    for topic in topics:
        topic_label = get_user_friendly_context_label(topic)
        topic_labels.append(topic_label)
    
    return {
        'user_profile': {
            'role': role_display,
            'child_age': user_profile.get('child_age', 'Not specified'),
            'diagnosis_status': diagnosis_display,
            'child_name': child_name,
            'concerns': concerns_display
        },
        'progress': {
            'current_context': context_label,
            'topics_discussed_count': len(topics),
            'conversation_length': summary.get('conversation_length', 0)
        },
        'recommendations': recommendations,
        'topics_discussed': topic_labels
    }



def get_user_friendly_context_label(context_path):
    """Convert technical context paths to user-friendly labels."""
    if not context_path:
        return "Getting Started"
    
    # Comprehensive mapping of technical paths to user-friendly labels
    context_labels = {
        # Main entry points
        "diagnosed_no.entry_point": "Getting Started - No Diagnosis",
        "diagnosed_yes.entry_point": "Getting Started - With Diagnosis",
        
        # Screening and monitoring
        "diagnosed_no.monitor_vs_screen": "Monitoring vs Screening",
        "diagnosed_no.screening_options": "Screening Options",
        "diagnosed_no.interpretation_routes": "Understanding Screening Results",
        
        # Not yet evaluated paths
        "diagnosed_no.not_yet_evaluated": "Not Yet Evaluated",
        "diagnosed_no.no_dx_but_concerns": "Concerns Without Diagnosis",
        "diagnosed_no.at_home_resources": "At-Home Resources",
        
        # Legal and emergency
        "diagnosed_no.legal_emergency_intro": "Legal & Emergency Support",
        "diagnosed_yes.legal_and_emergency": "Legal & Emergency Support",
        
        # Support and resources
        "diagnosed_yes.support_affording": "Affording Support",
        "diagnosed_yes.find_resources": "Finding Resources",
        
        # Specific topics
        "required_docs": "Required Documents",
        "screening_tools": "Screening Tools",
        "developmental_milestones": "Developmental Milestones",
        "red_flags": "Red Flags to Watch For",
        "next_steps": "Next Steps",
        "resources": "Resources & Support",
        "legal_rights": "Legal Rights",
        "emergency_contacts": "Emergency Contacts",
        
        # Default fallbacks
        "conversation_summary": "Conversation Summary",
        "Entry Point": "Getting Started"
    }
    
    # Try exact match first
    if context_path in context_labels:
        return context_labels[context_path]
    
    # Try partial matches for nested paths
    for key, label in context_labels.items():
        if context_path.startswith(key):
            return label
    
    # Fallback: convert underscores to spaces and title case
    return context_path.replace("_", " ").title()

def improve_conversation_summary_display(summary):
    """Improve the conversation summary display with better formatting and logic."""
    
    # Fix user profile display
    user_profile = summary.get('user_profile', {})
    
    # Clean up diagnosis status
    diagnosis_status = user_profile.get('diagnosis_status', 'unknown')
    if diagnosis_status == 'diagnosed_yes':
        diagnosis_display = "Diagnosed"
    elif diagnosis_status == 'diagnosed_no':
        diagnosis_display = "Not Diagnosed"
    else:
        diagnosis_display = diagnosis_status.replace('_', ' ').title()
    
    # Clean up child name (fix "Has" issue)
    child_name = user_profile.get('child_name', '')
    if child_name and child_name.lower() in ['has', 'yes', 'no', 'unknown']:
        child_name = 'Not specified'
    
    # Clean up role
    role = user_profile.get('role', 'unknown')
    if role == 'parent_caregiver':
        role_display = "Parent/Caregiver"
    else:
        role_display = role.replace('_', ' ').title()
    
    # Clean up concerns
    concerns = user_profile.get('concerns', [])
    if isinstance(concerns, str):
        concerns = [concerns]
    concerns_display = ', '.join(concerns) if concerns else 'Not specified'
    
    # Get user-friendly context label
    context_path = summary.get('final_context', 'Entry Point')
    context_label = get_user_friendly_context_label(context_path)
    
    # Generate better recommendations
    recommendations = summary.get("next_recommendations", [])
    if not recommendations or len(recommendations) == 0:
        # Generate contextual recommendations based on user profile and context
        if diagnosis_status == 'diagnosed_no':
            recommendations = [
                "Schedule a developmental screening",
                "Learn about early intervention services",
                "Connect with local support groups"
            ]
        elif diagnosis_status == 'diagnosed_yes':
            recommendations = [
                "Explore treatment and therapy options",
                "Find local autism support resources",
                "Learn about educational rights and IEPs"
            ]
        else:
            recommendations = [
                "Continue exploring autism support topics",
                "Consider speaking with a healthcare provider",
                "Learn more about developmental milestones"
            ]
    
    # Clean up topics discussed
    topics = summary.get("topics_discussed", [])
    topic_labels = []
    for topic in topics:
        topic_label = get_user_friendly_context_label(topic)
        topic_labels.append(topic_label)
    
    return {
        'user_profile': {
            'role': role_display,
            'child_age': user_profile.get('child_age', 'Not specified'),
            'diagnosis_status': diagnosis_display,
            'child_name': child_name,
            'concerns': concerns_display
        },
        'progress': {
            'current_context': context_label,
            'topics_discussed_count': len(topics),
            'conversation_length': summary.get('conversation_length', 0)
        },
        'recommendations': recommendations,
        'topics_discussed': topic_labels
    }


# ---- session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = "adaptive"  # New unified mode
if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = []
if "initial_response_shown" not in st.session_state:
    st.session_state.initial_response_shown = False
if "context_path" not in st.session_state:
    st.session_state.context_path = None
# New session state variables for browse mode and screening
if "browse_mode" not in st.session_state:
    st.session_state.browse_mode = False
if "browse_selections" not in st.session_state:
    st.session_state.browse_selections = {}
if "screening_questions" not in st.session_state:
    st.session_state.screening_questions = []
if "current_screening_step" not in st.session_state:
    st.session_state.current_screening_step = 0
if "screening_responses" not in st.session_state:
    st.session_state.screening_responses = []

# ---- main app
st.title("Autism Support Assistant")
st.markdown("Hi! I'm here to help guide you through autism support and resources. I know this journey can feel overwhelming, and I'm here to listen and help.")

# Check if user profile exists, if not collect it
if not st.session_state.user_profile:
    collect_user_profile()
else:
    # Show unified conversation interface
    show_unified_conversation_interface()