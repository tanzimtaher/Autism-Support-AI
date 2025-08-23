import streamlit as st
import openai, pymongo
import math
import sys
import os
import json
from pathlib import Path
from pymongo import MongoClient
from rag.query_engine import query_index
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import our intelligent conversation manager
from knowledge.intelligent_conversation_manager import IntelligentConversationManager

# Add these constants after the imports
MAX_CHAT_HISTORY = 25
MAX_HISTORY_TOKENS = 8000

# ---- keys & db
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
mongo = MongoClient("mongodb://localhost:27017/")["autism_ai"]["knowledge"]

# Initialize the conversation manager
@st.cache_resource
def get_conversation_manager():
    return IntelligentConversationManager()

manager = get_conversation_manager()

def ensure_consistent_user_id():
    """Ensure user ID is consistent across the application."""
    if not st.session_state.get("user_profile"):
        return "default"
    
    user_id = st.session_state.user_profile.get("user_id", "default")
    
    # If user_id is a random UUID (8 characters), use "default" instead
    if len(user_id) == 8 and user_id.isalnum():
        st.session_state.user_profile["user_id"] = "default"
        return "default"
    
    return user_id

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
    """Start with true conversational AI that leverages RAG for personalized responses."""
    
    # Check if we have existing documents with patient context
    user_id = ensure_consistent_user_id()
    existing_patient_info = parse_patient_documents(user_id)
    
    # Initialize conversational state
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "conversation_stage" not in st.session_state:
        st.session_state.conversation_stage = "personalized_opening"
    
    # If conversation hasn't started, begin with personalized greeting
    if not st.session_state.conversation_started:
        # Create personalized, empathetic opening based on RAG data
        if existing_patient_info and existing_patient_info.get("name"):
            # Use specific patient information for personalized response
            patient_name = existing_patient_info.get("name", "your child")
            age = existing_patient_info.get("age") or existing_patient_info.get("current_age")
            diagnosis = existing_patient_info.get("diagnosis", "")
            concerns = existing_patient_info.get("concerns", [])
            
            # Format age properly
            if age is not None and age != "":
                age_display = f"{age} years old"
            else:
                age_display = "a child"
            
            # Create empathetic, personalized opening
            opening_message = f"Hi there! 👋 I'm so glad you're here. I've been looking through Tucker's information, and I want you to know that I understand this journey can feel overwhelming at times.\n\nI can see that Tucker is {age_display} and has been diagnosed with {diagnosis}. I also noticed some concerns about {', '.join(concerns[:2]) if concerns else 'development and communication'}.\n\nI'm here to walk alongside you and Tucker on this journey. Every child is unique, and Tucker's specific needs and strengths matter. What would you like to focus on today? Are there particular challenges you're facing, or resources you're looking for to support Tucker's development?\n\nJust tell me what's on your mind - I'm here to listen and help."
            
            # Pre-populate user profile with RAG data
            st.session_state.user_profile = {
                "role": "parent_caregiver",
                "diagnosis_status": "diagnosed_yes" if diagnosis else "diagnosed_no",
                "child_age": age,
                "primary_concern": concerns[0] if concerns else "general",
                "patient_name": patient_name,
                "patient_info": existing_patient_info
            }
        else:
            # Generic but warm opening for new users
            opening_message = "Hi there! 👋 I'm so glad you're here. I know that seeking support for autism can feel overwhelming, and I want you to know that you're not alone on this journey.\n\nI'm here to listen, understand, and provide personalized guidance. Every family's situation is unique, and I want to understand yours so I can offer the most relevant support.\n\nCould you tell me a bit about your situation? Are you seeking support for yourself or for a child? What brings you here today?\n\nJust share what feels comfortable - I'm here to help."
        
        # Add opening message to chat history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": opening_message,
            "conversation_type": "personalized_opening"
        })
        st.session_state.conversation_started = True
    
    # Display pure chat interface
    st.markdown("### 💬 Let's talk")
    
    # Show chat history
    for message in st.session_state.chat_history:
        if message["role"] == "assistant":
            st.markdown(f"**🤖 AI Assistant:** {message['content']}")
        else:
            st.markdown(f"**👤 You:** {message['content']}")
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat history
        add_message_to_history({
            "role": "user",
            "content": user_input
        })
        
        # For the first few exchanges, use personalized responses based on Tucker's info
        print(f"🔍 DEBUG: Current conversation_stage: {st.session_state.get('conversation_stage', 'NOT_SET')}")
        if st.session_state.conversation_stage == "personalized_opening":
            print(f"🔍 DEBUG: Using personalized opening mode for message: '{user_input}'")
            try:
                print(f"🔍 Processing first message: '{user_input}'")
                user_id = ensure_consistent_user_id()
                patient_info = parse_patient_documents(user_id)
                print(f"🔍 Patient info found: {bool(patient_info)}")
                
                # Generate fast personalized response using cached context
                print(f"🔍 About to call generate_fast_personalized_response")
                personalized_response = generate_fast_personalized_response(user_input, st.session_state.user_profile)
                
                # Check if we need to transition to full RAG mode
                if personalized_response is None:
                    print(f"🔍 Complex query detected - transitioning to full RAG mode")
                    st.session_state.conversation_stage = "main_conversation"
                    
                    # Initialize conversation manager without adding default message
                    if not st.session_state.conversation_id:
                        start_unified_conversation(add_default_message=False)
                    
                    # Process through full RAG system
                    with st.spinner("🤔 Thinking..."):
                        try:
                            user_id = ensure_consistent_user_id()
                            patient_info = parse_patient_documents(user_id)
                            enhanced_query = enhance_user_query_with_patient_context(user_input, patient_info)
                            
                            # Process enhanced user input through intelligent manager
                            process_unified_input(enhanced_query)
                        except Exception as e:
                            print(f"⚠️ Could not enhance query with patient context: {e}")
                            # Fallback to original processing
                            process_unified_input(user_input)
                    
                    st.rerun()
                    return
                
                print(f"🔍 Generated response length: {len(personalized_response)}")
                
                # Add personalized response to chat history
                add_message_to_history({
                    "role": "assistant",
                    "content": personalized_response,
                    "conversation_type": "personalized_response"
                })
                print(f"🔍 Added response to chat history. Total messages: {len(st.session_state.chat_history)}")
                
                # Check if user is ready to move to main conversation
                if any(word in user_input.lower() for word in ["ready", "start", "begin", "continue", "okay", "yes", "help", "support"]):
                    st.session_state.conversation_stage = "main_conversation"
                    # Initialize conversation manager without adding default message
                    if not st.session_state.conversation_id:
                        start_unified_conversation(add_default_message=False)
                
            except Exception as e:
                print(f"⚠️ Could not generate personalized response: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to generic response
                fallback_response = "Thank you for sharing that with me. I want to make sure I understand your situation so I can provide the most helpful support. Could you tell me a bit more about what you're looking for?"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": fallback_response,
                    "conversation_type": "fallback_response"
                })
        else:
            print(f"🔍 DEBUG: NOT in personalized opening mode. Stage: {st.session_state.get('conversation_stage', 'NOT_SET')}")
            print(f"🔍 DEBUG: This message will go through intelligent manager instead")
            
            # Main conversation mode - use intelligent manager
            if not st.session_state.conversation_id:
                start_unified_conversation(add_default_message=False)
            
            with st.spinner("🤔 Thinking..."):
                try:
                    user_id = ensure_consistent_user_id()
                    patient_info = parse_patient_documents(user_id)
                    enhanced_query = enhance_user_query_with_patient_context(user_input, patient_info)
                    
                    # Process enhanced user input through intelligent manager
                    process_unified_input(enhanced_query)
                except Exception as e:
                    print(f"⚠️ Could not enhance query with patient context: {e}")
                    # Fallback to original processing
                    process_unified_input(user_input)
        
        st.rerun()




def start_unified_conversation(add_default_message=True):
    """Start the unified intelligent conversation."""
    if not st.session_state.user_profile:
        return
    
    # Get conversation start from manager
    start_result = manager.start_conversation(st.session_state.user_profile)
    
    # Initialize conversation state
    st.session_state.conversation_id = start_result["conversation_id"]
    print(f"✅ Conversation initialized with ID: {st.session_state.conversation_id}")
    
    # Only add initial message to chat history if requested
    if add_default_message:
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
        
        # Add patient context cache management
        st.markdown("### 🧠 Patient Context Cache")
        if st.button("🔄 Refresh Patient Context"):
            st.session_state.patient_context_cache = None
            st.session_state.patient_context_timestamp = None
            st.success("Patient context cache cleared. Will refresh on next interaction.")
        
        if st.session_state.patient_context_cache:
            cache_age = datetime.now() - st.session_state.patient_context_timestamp
            st.info(f"Cache age: {cache_age.seconds // 60} minutes")
            if st.session_state.patient_context_cache.get('name'):
                st.write(f"Patient: {st.session_state.patient_context_cache.get('name')}")
            if st.session_state.patient_context_cache.get('age'):
                st.write(f"Age: {st.session_state.patient_context_cache.get('age')} years")
        
        if st.button("📚 View My Documents"):
            show_user_documents()
        
        if st.button("🗑️ Clear All Documents"):
            clear_user_documents()
        
        # Debug section
        st.markdown("---")
        st.markdown("### 🔧 Debug")
        
        if st.button("🐛 Show RAG Debug Info"):
            show_rag_debug_info()
        
        if st.button("🔧 Check System Status"):
            check_system_status()
        
        if st.button("🧪 Test RAG Functionality"):
            test_rag_functionality()
        
        if st.button("📋 Show Patient Summary"):
            user_id = ensure_consistent_user_id()
            patient_info = parse_patient_documents(user_id)
            if patient_info:
                st.subheader("📋 Patient Information Summary")
                summary = create_patient_summary(patient_info)
                st.markdown(summary)
                
                # Show raw patient info for debugging
                with st.expander("🔍 Raw Patient Data"):
                    st.json(patient_info)
            else:
                st.warning("No patient information found in documents.")
        
    # Topic browsing option
    st.markdown("---")
    st.markdown("### 🔍 Browse Topics")
    
    if st.button("📖 Browse Specific Topics"):
        st.session_state.browse_mode = True
        st.rerun()
    
    # Main conversation area
    st.subheader("Our Conversation")
    
    # Display chat history with adaptive styling and transparency
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
            
            # Add transparency section
            if message.get("sources") or message.get("mode") or message.get("context_path"):
                with st.expander("🔍 How I made this decision", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📚 Sources Used:**")
                        sources = message.get("sources", [])
                        if sources:
                            for i, source in enumerate(sources[:3], 1):
                                source_name = source.get("source", "Unknown")
                                if source_name == "user_upload":
                                    st.markdown(f"• 📄 Your document: {source.get('filename', 'Unknown file')}")
                                else:
                                    st.markdown(f"• 📖 Knowledge base: {source_name}")
                        else:
                            st.markdown("• 📖 General knowledge base")
                    
                    with col2:
                        st.markdown("**🧠 Decision Process:**")
                        mode = message.get("mode", "unknown")
                        if mode == "mongo_only":
                            st.markdown("• Used structured guidance")
                        elif mode == "blend":
                            st.markdown("• Combined guidance + your documents")
                        elif mode == "vector_only":
                            st.markdown("• Searched knowledge base")
                        
                        confidence = message.get("confidence", 0.8)
                        st.markdown(f"• Confidence: {confidence:.0%}")
                    
                    # Show context path
                    if message.get("context_path"):
                        context_path = message["context_path"]
                        context_label = get_user_friendly_context_label(context_path)
                        st.markdown(f"**📍 Current Topic:** {context_label}")
            
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
    
    if user_input and user_input.strip():
        # Store the user input to process
        current_input = user_input.strip()
        
        # Add user message to history
        add_message_to_history({
            "role": "user",
            "content": current_input
        })
        
        # Show processing indicator and process the input
        with st.spinner("🤔 Thinking..."):
            # Enhance query with patient context if available
            try:
                user_id = ensure_consistent_user_id()
                patient_info = parse_patient_documents(user_id)
                enhanced_query = enhance_user_query_with_patient_context(current_input, patient_info)
                
                # Process enhanced user input through intelligent manager
                process_unified_input(enhanced_query)
            except Exception as e:
                print(f"⚠️ Could not enhance query with patient context: {e}")
                # Fallback to original processing
                process_unified_input(current_input)
        
        # Rerun to update the display after processing is complete
        st.rerun()

def process_unified_input(user_input):
    """Process user input through the intelligent conversation manager."""
    if not st.session_state.conversation_id:
        st.error("Conversation not initialized. Please start over.")
        print(f"❌ No conversation_id found. Session state: {st.session_state.get('conversation_id')}")
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
    add_message_to_history({
        "role": "assistant",
        "content": response_result["response"],
        "context_path": response_result["context_path"],
        "conversation_type": conversation_type,
        "next_suggestions": response_result.get("next_suggestions"),
        "confidence": response_result.get("confidence", 0.0),
        "sources": response_result.get("sources", [])
    })
    
    # Show safety alert if present
    if response_result.get("safety_warning"):
        st.error("🚨 **SAFETY ALERT** ��")
        st.error(response_result["safety_warning"])

def handle_screening_response(user_input):
    """Handle user response to screening questions."""
    # Store the response
    if "screening_responses" not in st.session_state:
        st.session_state.screening_responses = {}
    
    current_step = st.session_state.current_screening_step
    current_question = st.session_state.screening_questions[current_step]
    st.session_state.screening_responses[current_question] = user_input
    
    # Add user response to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "conversation_type": "screening_response"
    })
    
    # Move to next question or complete screening
    st.session_state.current_screening_step += 1
    
    if st.session_state.current_screening_step >= len(st.session_state.screening_questions):
        # Screening complete - generate assessment
        assessment = generate_screening_assessment(st.session_state.screening_responses)
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": assessment,
            "conversation_type": "screening_complete",
            "confidence": 0.8,
            "sources": []
        })
        # Reset screening
        st.session_state.screening_questions = []
        st.session_state.current_screening_step = 0
    else:
        # Ask next question
        next_question = st.session_state.screening_questions[st.session_state.current_screening_step]
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": next_question,
            "conversation_type": "screening_question",
            "confidence": 1.0,
            "sources": []
        })

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
                # User hasn't selected a category yet, so we can't proceed
                return
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
            
        elif category_doc:
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
    else:
        st.warning("No categories found for your selection. Please try a different diagnosis status.")
        if st.button("Reset Selection"):
            st.session_state.browse_selections = {}
            st.rerun()

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



def show_rag_debug_info():
    """Show RAG debug information for troubleshooting."""
    st.subheader("🔧 RAG System Debug Information")
    
    # Get current user ID
    user_id = ensure_consistent_user_id()
    st.write(f"**Current User ID:** {user_id}")
    
    # Check vector store documents
    vector_docs = get_vector_store_documents(user_id)
    st.write(f"**Documents in Vector Store:** {len(vector_docs)}")
    
    if vector_docs:
        st.write("**Available Documents:**")
        for doc in vector_docs:
            st.write(f"• {doc['filename']} ({doc['chunks']} chunks)")
    else:
        st.warning("No documents found in vector store")
    
    # Check physical files
    user_docs_dir = Path(f"data/user_docs/{user_id}")
    if user_docs_dir.exists():
        physical_files = list(user_docs_dir.glob("*"))
        st.write(f"**Physical Files:** {len(physical_files)}")
        for file in physical_files:
            st.write(f"• {file.name}")
    else:
        st.warning("No physical files directory found")
    
    # Test RAG search
    if st.button("🧪 Test RAG Search"):
        try:
            from rag.ingest_user_docs import search_user_documents
            test_results = search_user_documents(user_id, "test query", 3)
            st.write(f"**Test Search Results:** {len(test_results)}")
            for result in test_results:
                st.write(f"• Score: {result.get('score', 0):.3f} - {result.get('payload', {}).get('filename', 'Unknown')}")
        except Exception as e:
            st.error(f"RAG search failed: {e}")


def check_system_status():
    """Check the status of various system components."""
    st.subheader("🔧 System Status Check")
    
    # Check OpenAI connection
    try:
        import openai
        client = openai.OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))
        # Test with a simple call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        st.success("✅ OpenAI API: Connected")
    except Exception as e:
        st.error(f"❌ OpenAI API: Connection failed - {str(e)}")
    
    # Check MongoDB connection
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        client.admin.command('ping')
        st.success("✅ MongoDB: Connected")
    except Exception as e:
        st.error(f"❌ MongoDB: Connection failed - {str(e)}")
    
    # Check Qdrant connection
    try:
        from rag.qdrant_client import ensure_collection
        qdr = ensure_collection("test_collection", size=1536)
        if qdr:
            st.success("✅ Qdrant Vector Store: Connected")
        else:
            st.error("❌ Qdrant Vector Store: Connection failed")
    except Exception as e:
        st.error(f"❌ Qdrant Vector Store: Connection failed - {str(e)}")
    
    # Check user documents
    user_id = ensure_consistent_user_id()
    
    # Try to get documents using the same method as the RAG system
    try:
        from rag.ingest_user_docs import search_user_documents
        # Use a simple query to find all documents (empty query should return all)
        vector_docs = search_user_documents(user_id, "", 10)  # Empty query, limit 10
        if vector_docs:
            st.success(f"📄 User Documents: {len(vector_docs)} documents found")
            # Show document names for debugging
            with st.expander("📋 Document Details", expanded=False):
                for doc in vector_docs[:3]:  # Show first 3 documents
                    filename = doc.get("payload", {}).get("filename", "Unknown")
                    st.write(f"• {filename}")
        else:
            st.warning(f"📄 User Documents: No documents found for user '{user_id}'")
    except Exception as e:
        st.error(f"❌ Error checking user documents: {e}")
        # Fallback to the old method
        try:
            vector_docs = get_vector_store_documents(user_id)
            st.info(f"📄 User Documents: {len(vector_docs)} documents found (fallback method)")
        except Exception as e2:
            st.error(f"❌ Fallback method also failed: {e2}")


def test_rag_functionality():
    """Test RAG functionality to debug issues."""
    st.subheader("🧪 RAG Functionality Test")
    
    # Test user document search
    user_id = ensure_consistent_user_id()
    st.write(f"**Testing User ID:** {user_id}")
    
    # Test vector store documents
    vector_docs = get_vector_store_documents(user_id)
    st.write(f"**Vector Store Documents:** {len(vector_docs)}")
    
    if vector_docs:
        st.write("**Available Documents:**")
        for doc in vector_docs:
            st.write(f"• {doc['filename']} ({doc['chunks']} chunks)")
    
    # Test RAG search
    test_query = st.text_input("Test Query:", value="autism diagnosis")
    
    if st.button("🔍 Test RAG Search"):
        try:
            from rag.ingest_user_docs import search_user_documents
            from retrieval.retrieval_router import RetrievalRouter
            from knowledge.knowledge_adapter import KnowledgeAdapter
            
            # Test user document search
            user_results = search_user_documents(user_id, test_query, 3)
            st.write(f"**User Document Results:** {len(user_results)}")
            
            for i, result in enumerate(user_results, 1):
                payload = result.get("payload", {})
                st.write(f"{i}. {payload.get('filename', 'Unknown')} - Score: {result.get('score', 0):.3f}")
                st.write(f"   Content: {payload.get('content', '')[:100]}...")
            
            # Test retrieval router
            ka = KnowledgeAdapter()
            router = RetrievalRouter(ka)
            test_profile = {"user_id": user_id, "diagnosis_status": "diagnosed_yes"}
            mode, results = router.route(test_query, test_profile, "diagnosed_yes.support_affording")
            
            st.write(f"**Router Mode:** {mode}")
            st.write(f"**Total Results:** {len(results)}")
            
            # Show results by source
            user_docs = [r for r in results if r.get("payload", {}).get("source") == "user_upload"]
            shared_docs = [r for r in results if r.get("payload", {}).get("source") != "user_upload"]
            
            st.write(f"**User Documents:** {len(user_docs)}")
            st.write(f"**Shared Knowledge:** {len(shared_docs)}")
            
        except Exception as e:
            st.error(f"RAG test failed: {e}")
            import traceback
            st.code(traceback.format_exc())


def parse_patient_documents(user_id: str = "default") -> dict:
    """Parse patient documents to extract key information."""
    try:
        vector_docs = get_vector_store_documents(user_id)
        if not vector_docs:
            return {}
        
        patient_info = {
            "name": None,
            "age": None,
            "diagnosis": None,
            "concerns": [],
            "evaluation_date": None,
            "key_findings": [],
            "recommendations": []
        }
        
        # Extract information from each document
        for doc in vector_docs:
            filename = doc.get("filename", "").lower()
            
            # Look for diagnosis/evaluation documents
            if any(keyword in filename for keyword in ["diagnosis", "evaluation", "assessment", "report"]):
                # Extract key information from content samples
                for sample in doc.get("content_samples", []):
                    content = sample.lower()
                    
                    # Extract name
                    if not patient_info["name"]:
                        name_patterns = [
                            r"patient name[:\s]+([a-zA-Z\s]+)",
                            r"name[:\s]+([a-zA-Z\s]+)",
                            r"([a-zA-Z]+)\s+[a-zA-Z]+\s+[a-zA-Z]+"  # First Middle Last pattern
                        ]
                        for pattern in name_patterns:
                            import re
                            match = re.search(pattern, content)
                            if match:
                                patient_info["name"] = match.group(1).strip().title()
                                break
                    
                    # Extract age
                    if not patient_info["age"]:
                        age_patterns = [
                            r"(\d+)\s*(?:year|yr)s?\s*old",
                            r"age[:\s]+(\d+)",
                            r"(\d+)\s*(?:years?|yrs?)"
                        ]
                        for pattern in age_patterns:
                            match = re.search(pattern, content)
                            if match:
                                patient_info["age"] = int(match.group(1))
                                break
                    
                    # Extract diagnosis
                    if not patient_info["diagnosis"]:
                        if "autism" in content or "asd" in content:
                            patient_info["diagnosis"] = "Autism Spectrum Disorder"
                        elif "diagnosis" in content:
                            # Look for diagnosis section
                            diagnosis_section = content.split("diagnosis")[-1][:500]
                            patient_info["diagnosis"] = diagnosis_section.strip()
                    
                    # Extract concerns
                    concern_keywords = ["concern", "difficulty", "challenge", "issue", "problem"]
                    for keyword in concern_keywords:
                        if keyword in content and keyword not in patient_info["concerns"]:
                            patient_info["concerns"].append(keyword)
                    
                    # Extract key findings
                    if "finding" in content or "result" in content:
                        findings_section = content.split("finding")[-1][:300]
                        if findings_section.strip():
                            patient_info["key_findings"].append(findings_section.strip())
        
        return patient_info
        
    except Exception as e:
        print(f"❌ Error parsing patient documents: {e}")
        return {}

def create_patient_summary(patient_info: dict) -> str:
    """Create a human-readable summary of patient information."""
    if not patient_info:
        return "No patient information available."
    
    summary_parts = []
    
    if patient_info.get("name"):
        summary_parts.append(f"**Patient Name:** {patient_info['name']}")
    
    if patient_info.get("age"):
        summary_parts.append(f"**Age:** {patient_info['age']} years old")
    
    if patient_info.get("diagnosis"):
        summary_parts.append(f"**Diagnosis:** {patient_info['diagnosis']}")
    
    if patient_info.get("concerns"):
        concerns_text = ", ".join(patient_info["concerns"][:3])  # Limit to 3 concerns
        summary_parts.append(f"**Main Concerns:** {concerns_text}")
    
    if patient_info.get("key_findings"):
        findings_text = "; ".join(patient_info["key_findings"][:2])  # Limit to 2 findings
        summary_parts.append(f"**Key Findings:** {findings_text}")
    
    if summary_parts:
        return "\n".join(summary_parts)
    else:
        return "Limited patient information available."

def enhance_user_query_with_patient_context(user_query: str, patient_info: dict) -> str:
    """Enhance user query with patient context for better RAG retrieval."""
    if not patient_info:
        return user_query
    
    enhanced_query = user_query
    
    # Add patient context to query
    if patient_info.get("name"):
        enhanced_query += f" Patient: {patient_info['name']}"
    
    if patient_info.get("age"):
        enhanced_query += f" Age: {patient_info['age']} years"
    
    if patient_info.get("diagnosis"):
        enhanced_query += f" Diagnosis: {patient_info['diagnosis']}"
    
    if patient_info.get("concerns"):
        concerns = ", ".join(patient_info["concerns"][:2])
        enhanced_query += f" Concerns: {concerns}"
    
    return enhanced_query

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
# New session state variables for true conversational AI
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False
if "conversation_stage" not in st.session_state:
    st.session_state.conversation_stage = "personalized_opening"

if "chat_onboarding_complete" not in st.session_state:
    st.session_state.chat_onboarding_complete = False
if "onboarding_data" not in st.session_state:
    st.session_state.onboarding_data = {}
# New session state variables for pure chat onboarding
if "chat_onboarding_complete" not in st.session_state:
    st.session_state.chat_onboarding_complete = False

# New session state variables for conversational onboarding
if "onboarding_step" not in st.session_state:
    st.session_state.onboarding_step = 0
if "onboarding_data" not in st.session_state:
    st.session_state.onboarding_data = {}

# Add these session state variables in the session state section (around line 1850)
if "patient_context_cache" not in st.session_state:
    st.session_state.patient_context_cache = None
if "patient_context_timestamp" not in st.session_state:
    st.session_state.patient_context_timestamp = None
if "patient_context_ttl" not in st.session_state:
    st.session_state.patient_context_ttl = 3600  # 1 hour cache

# Add these functions after the existing functions (around line 450)
def get_cached_patient_context(user_id, force_refresh=False):
    """Get patient context with intelligent caching."""
    current_time = datetime.now()
    
    # Check if we have valid cached data
    if (not force_refresh and 
        st.session_state.patient_context_cache and 
        st.session_state.patient_context_timestamp and
        (current_time - st.session_state.patient_context_timestamp).seconds < st.session_state.patient_context_ttl):
        
        print(f"🔍 Using cached patient context (age: {st.session_state.patient_context_cache.get('age', 'NOT_FOUND')})")
        return st.session_state.patient_context_cache
    
    # Extract fresh patient context
    print(f"🔍 Extracting fresh patient context for user: {user_id}")
    try:
        from utils.patient_utils import parse_patient_documents
        patient_info = parse_patient_documents(user_id)
        
        if patient_info and patient_info.get('name') and patient_info.get('age'):
            # Cache the successful extraction
            st.session_state.patient_context_cache = patient_info
            st.session_state.patient_context_timestamp = current_time
            print(f"✅ Cached patient context: {patient_info.get('name')} ({patient_info.get('age')} years old)")
            return patient_info
        else:
            print(f"⚠️ Patient context extraction failed or incomplete: {patient_info}")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting patient context: {e}")
        return None

def generate_fast_personalized_response(user_input, user_profile):
    """Generate fast personalized response without expensive operations."""
    user_input_lower = user_input.lower()
    
    # Get cached patient context (fast)
    user_id = ensure_consistent_user_id()
    patient_info = get_cached_patient_context(user_id)
    
    # Simple greeting patterns - these can use fast responses
    if any(word in user_input_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
        if patient_info and patient_info.get("name") and patient_info.get("age"):
            name = patient_info.get("name")
            age = patient_info.get("age")
            diagnosis = patient_info.get("diagnosis", "Autism Spectrum Disorder")
            
            return f"Hello! 👋 It's wonderful to hear from you. I'm here to support you and {name} on this journey.\n\nBased on what I know about {name}, who is {age} years old with {diagnosis}, I can help you with:\n• Specific strategies for development and communication\n• Resources tailored to {name}'s age and needs\n• Guidance on next steps and support options\n• Answering any questions you have about {name}'s development\n\nWhat would you like to focus on today? You can ask me anything - I'm here to help you and {name} thrive."
        else:
            return "Hello! 👋 It's wonderful to hear from you. I'm here to support you and your child on this journey.\n\nI can help you with:\n• Understanding autism and developmental milestones\n• Finding resources and support services\n• Practical strategies for daily challenges\n• Emotional support and guidance\n\nWhat would you like to focus on today? Just tell me what's on your mind - I'm here to help."
    
    # Transition keywords - these should move to full RAG mode
    if any(word in user_input_lower for word in ["ready", "start", "begin", "continue", "okay", "yes"]):
        return "Perfect! I'm ready to provide you with personalized support. What specific area would you like to explore first?"
    
    # Complex queries that need full RAG - return None to trigger RAG mode
    complex_keywords = [
        "recommendation", "schooling", "education", "therapy", "treatment", "resources",
        "help with", "how to", "what should", "advice", "strategy", "plan", "support",
        "services", "providers", "assessment", "evaluation", "goals", "progress",
        "challenges", "difficulties", "behavior", "communication", "social", "learning"
    ]
    
    if any(keyword in user_input_lower for keyword in complex_keywords):
        print(f"🔍 Complex query detected: '{user_input}' - routing to full RAG")
        return None  # This will trigger full RAG processing
    
    # Default empathetic response for simple queries
    return "Thank you for sharing that with me. I want to make sure I understand your situation so I can provide the most helpful support. Could you tell me a bit more about what you're looking for?"

# Add this function after the existing functions
def manage_chat_history():
    """Manage chat history to prevent unlimited growth and extract insights."""
    try:
        if len(st.session_state.chat_history) > MAX_CHAT_HISTORY:
            # Extract insights from old messages before trimming
            old_messages = st.session_state.chat_history[:-20]
            
            # Try to extract insights using memory manager
            try:
                user_id = ensure_consistent_user_id()
                from knowledge.conversation_memory_manager import ConversationMemoryManager
                memory_manager = ConversationMemoryManager(user_id)
                insights = memory_manager.extract_and_store_insights(old_messages)
                
                if insights:
                    # Create summary marker
                    summary_marker = {
                        "role": "system",
                        "content": f"Previous conversation insights stored: {len(insights.get('topics_discussed', []))} topics, {len(insights.get('user_concerns', []))} concerns",
                        "type": "memory_summary",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Keep only recent messages and add summary
                    st.session_state.chat_history = [summary_marker] + st.session_state.chat_history[-20:]
                    print(f"✅ Chat history trimmed to {len(st.session_state.chat_history)} messages, insights extracted")
                else:
                    # Simple trim without insights
                    st.session_state.chat_history = st.session_state.chat_history[-20:]
                    print(f"✅ Chat history trimmed to {len(st.session_state.chat_history)} messages")
                    
            except Exception as e:
                print(f"⚠️ Could not extract insights, simple trim: {e}")
                st.session_state.chat_history = st.session_state.chat_history[-20:]
                
    except Exception as e:
        print(f"⚠️ Error managing chat history: {e}")

def add_message_to_history(message):
    """Add message to chat history with smart management."""
    st.session_state.chat_history.append(message)
    
    # Manage history size
    manage_chat_history()

# ---- main app
st.title("Autism Support Assistant")
st.markdown("Hi! I'm here to help guide you through autism support and resources. I know this journey can feel overwhelming, and I'm here to listen and help.")

# Check if user profile exists, if not collect it
if not st.session_state.user_profile:
    collect_user_profile()
elif st.session_state.conversation_stage == "personalized_opening":
    # Stay in personalized opening mode
    collect_user_profile()
elif not st.session_state.conversation_id:
    # Initialize conversation with intelligent manager without adding default message
    start_unified_conversation(add_default_message=False)
    show_unified_conversation_interface()
else:
    # Show unified conversation interface
    show_unified_conversation_interface()