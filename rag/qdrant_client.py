"""
Qdrant Client for Autism Support App
Replaces LlamaIndex with production-ready vector database.
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchAny
from typing import List, Dict, Optional

def get_qdrant():
    """Get Qdrant client connection."""
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY") or None
    
    try:
        client = QdrantClient(host=host, port=port, api_key=api_key)
        # Test connection
        client.get_collections()
        print(f"✅ Connected to Qdrant at {host}:{port}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        return None

def ensure_collection(name: str, size: int = 1536):
    """Ensure collection exists with proper configuration."""
    qdr = get_qdrant()
    if not qdr:
        return None
    
    try:
        # Check if collection exists
        collections = qdr.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if name not in collection_names:
            # Create new collection
            qdr.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )
            print(f"✅ Created collection: {name}")
        else:
            print(f"✅ Collection exists: {name}")
        
        return qdr
    except Exception as e:
        print(f"❌ Error with collection {name}: {e}")
        return None

def search_with_user_filter(
    collection_name: str, 
    query_vector: List[float], 
    user_id: Optional[str] = None,
    k: int = 8
) -> List[Dict]:
    """Search with optional user filtering."""
    qdr = get_qdrant()
    if not qdr:
        return []
    
    try:
        # Build filter for user isolation
        query_filter = None
        if user_id:
            query_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchAny(any=[user_id, "public"]))]
            )
        
        # Perform search
        results = qdr.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=k
        )
        
        # Format results
        formatted_results = []
        for hit in results:
            formatted_results.append({
                "score": float(hit.score),
                "payload": hit.payload or {},
                "id": hit.id
            })
        
        return formatted_results
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []
