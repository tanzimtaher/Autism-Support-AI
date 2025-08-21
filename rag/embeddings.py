"""
Embeddings module for Autism Support App
Handles text-to-vector conversion using OpenAI or local models.
"""

import os
from typing import List

def embed(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    provider = os.getenv("EMBED_PROVIDER", "openai")
    
    if provider == "openai":
        return _embed_openai(texts)
    else:
        return _embed_local(texts)

def _embed_openai(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI."""
    try:
        from openai import OpenAI
        import streamlit as st
        
        # Get API key from Streamlit secrets
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key found")
            return []
        
        client = OpenAI(api_key=api_key)
        model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        
        response = client.embeddings.create(
            model=model,
            input=texts
        )
        
        return [d.embedding for d in response.data]
        
    except Exception as e:
        print(f"❌ OpenAI embedding error: {e}")
        return []

def _embed_local(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using local model (fallback)."""
    try:
        from sentence_transformers import SentenceTransformer
        
        # Use a lightweight model for local processing
        model = SentenceTransformer("intfloat/e5-small-v2")
        embeddings = model.encode(texts, convert_to_numpy=False)
        
        return embeddings.tolist()
        
    except Exception as e:
        print(f"❌ Local embedding error: {e}")
        return []

def embed_single(text: str) -> List[float]:
    """Generate embedding for a single text."""
    embeddings = embed([text])
    return embeddings[0] if embeddings else []
