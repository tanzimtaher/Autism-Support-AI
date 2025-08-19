"""
Load the on-disk Llama-Index store and run similarity queries.
"""

import os
from llama_index.core import load_index_from_storage, StorageContext, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
# rag/query_engine.py  (built-in disk store version)
from typing import Dict, List

VECTOR_DIR = "vector_index/"  # must match build_index.py

# Global LLM / embedding
Settings.llm         = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")


def query_index(query: str, k: int = 4, debug: bool = True) -> Dict:
    """
    Returns:
        {
            "answer": str – generated response,
            "chunks": [ {"text": ..., "source": ...}, ... ]
        }
    """
    storage_ctx = StorageContext.from_defaults(persist_dir=VECTOR_DIR)
    index       = load_index_from_storage(storage_ctx)

    engine   = index.as_query_engine(similarity_top_k=k)
    resp     = engine.query(query)

    chunks = []
    for i, node in enumerate(resp.source_nodes, 1):
        snippet = node.text.strip().replace("\n", " ")
        source  = node.metadata.get("file_name", "Unknown")
        if debug:
            print(f"[DEBUG] [{i}] source={source} ➤ {snippet[:80]}…")
        chunks.append({"text": snippet, "source": source})

    return {
        "answer": resp.response,
        "chunks": chunks
    }


# CLI test
if __name__ == "__main__":
    while True:
        q = input("🔍 Ask (or 'exit'): ")
        if q.lower() == "exit":
            break
        print("\n🧠", query_index(q), "\n")
