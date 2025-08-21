"""
Admin Document Upload for Autism Support App
Admin-only interface for uploading expert documents to improve the general knowledge base.
"""

import streamlit as st
from pathlib import Path
import os
import sys
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Define where uploaded files go
UPLOAD_DIR = Path("data/admin_uploaded_docs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="📄 Admin Document Upload", layout="wide")
st.title("📄 Admin Document Upload")
st.markdown("**Expert Access Only** - Upload autism and child development documents to improve the general knowledge base.")

# Admin access control
def check_admin_access():
    """Check if user has admin access."""
    # For now, use a simple password check
    # In production, this should be proper authentication
    admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        password = st.text_input("Enter admin password:", type="password")
        if st.button("Login"):
            if password == admin_password:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("❌ Invalid password. Admin access required.")
                return False
        return False
    
    return True

def main():
    if not check_admin_access():
        return
    
    st.success("✅ Admin access granted")
    
    # Logout option
    if st.sidebar.button("🚪 Logout"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    st.markdown("""
    ### 📋 Upload Guidelines
    
    **Purpose**: Upload expert documents to improve the general knowledge base for all users.
    
    **Acceptable Documents**:
    - ✅ Autism research papers
    - ✅ Child development guidelines
    - ✅ Screening and assessment tools
    - ✅ Therapy and intervention guides
    - ✅ Educational resources
    - ✅ Policy documents and guidelines
    
    **Document Requirements**:
    - 📄 PDF or TXT format
    - 📝 Clear, authoritative content
    - 🔒 No patient-specific information
    - 📊 Evidence-based when possible
    """)
    
    # Upload interface
    uploaded_files = st.file_uploader(
        label="Upload expert documents (PDF, TXT)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="Select one or more documents to upload"
    )
    
    # Preview uploads
    if uploaded_files:
        st.subheader("📁 Uploaded Files")
        for uploaded_file in uploaded_files:
            st.markdown(f"✅ **{uploaded_file.name}** ({uploaded_file.size} bytes)")
            file_path = UPLOAD_DIR / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
    
    # Ingestion options
    if uploaded_files:
        st.subheader("⚙️ Document Processing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Process & Ingest to Qdrant"):
                process_documents()
        
        with col2:
            if st.button("🧹 Clear Upload Directory"):
                clear_upload_directory()
    
    # Show current documents
    show_current_documents()

def process_documents():
    """Process uploaded documents and ingest into Qdrant."""
    try:
        from rag.ingest_shared_kb import main as ingest_main
        
        st.info("🔄 Processing documents...")
        
        # First, process the uploaded documents
        from rag.process_admin_docs import process_admin_documents
        processed_count = process_admin_documents(str(UPLOAD_DIR))
        
        if processed_count > 0:
            st.success(f"✅ Processed {processed_count} documents")
            
            # Then ingest into Qdrant
            st.info("📤 Ingesting into Qdrant...")
            if ingest_main():
                st.success("✅ Documents successfully ingested into Qdrant!")
            else:
                st.error("❌ Failed to ingest documents into Qdrant")
        else:
            st.warning("⚠️ No documents to process")
            
    except Exception as e:
        st.error(f"❌ Processing failed: {e}")
        st.text(traceback.format_exc())

def clear_upload_directory():
    """Clear the upload directory."""
    try:
        import shutil
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            st.success("✅ Upload directory cleared")
        else:
            st.info("📁 Upload directory is already empty")
    except Exception as e:
        st.error(f"❌ Failed to clear directory: {e}")

def show_current_documents():
    """Show currently uploaded documents."""
    st.subheader("📚 Current Documents")
    
    if UPLOAD_DIR.exists():
        files = list(UPLOAD_DIR.glob("*"))
        if files:
            for file in files:
                if file.is_file():
                    size = file.stat().st_size
                    st.markdown(f"📄 **{file.name}** ({size} bytes)")
        else:
            st.info("📁 No documents uploaded yet")
    else:
        st.info("📁 Upload directory not found")

if __name__ == "__main__":
    main()
