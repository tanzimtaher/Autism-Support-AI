import streamlit as st
from pathlib import Path
import os
import shutil
import sys
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Define where uploaded files go
UPLOAD_DIR = Path("data/user_uploaded_docs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="📄 Upload Documents", layout="wide")
st.title("📄 Upload & Ingest Documents")

# === Upload interface ===
uploaded_files = st.file_uploader(
    label="Upload one or more documents (PDF, TXT)",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

# === Preview uploads ===
if uploaded_files:
    for uploaded_file in uploaded_files:
        st.markdown(f"✅ Uploaded: `{uploaded_file.name}`")
        file_path = UPLOAD_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

# === Trigger ingestion ===
if st.button("⚙️ Ingest Documents"):
    from rag.build_index import build_index_from_documents

    try:
        build_index_from_documents(documents_path=str(UPLOAD_DIR))
        st.success("✅ Documents ingested and vector store updated.")
    except Exception as e:
        st.error(f"❌ Ingestion failed: {e}")
        st.text(traceback.format_exc())
