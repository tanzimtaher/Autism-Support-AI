"""
Build a vector index using ONLY Llama-Index’s built-in disk store.
No external vector-DB, no onnxruntime, no chromadb.
"""

import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Where the persisted index will live
VECTOR_DIR = "vector_index/"          # ← folder will be created if missing

def build_index_from_documents(
        documents_path: str = "documents/",
        persist_dir:   str = VECTOR_DIR) -> bool:
    """Ingest docs → embed → save on disk."""
    docs = SimpleDirectoryReader(documents_path).load_data()
    if not docs:
        print("⚠️  No documents found – skipping index build.")
        return False

    os.makedirs(persist_dir, exist_ok=True)

    # Configure LLM + embedding once
    Settings.llm         = OpenAI(model="gpt-4o-mini")
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    # Build & persist
    index = VectorStoreIndex.from_documents(docs)
    index.storage_context.persist(persist_dir=persist_dir)

    print(f"✅  Index built and stored in “{persist_dir}”.")
    return True


# CLI helper
if __name__ == "__main__":
    build_index_from_documents()
