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
    # Try local storage first, then fallback to in-memory
    try:
        # Use local storage directory
        storage_path = os.path.join(os.getcwd(), "qdrant_storage")
        client = QdrantClient(path=storage_path)
        client.get_collections()
        print(f"✅ Connected to local Qdrant storage at {storage_path}")
        return client
    except Exception as e:
        print(f"⚠️ Local storage failed, using in-memory: {e}")
        try:
            # Fallback to in-memory storage
            client = QdrantClient(":memory:")
            print("✅ Using in-memory Qdrant storage")
            return client
        except Exception as e2:
            print(f"❌ Failed to create Qdrant client: {e2}")
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

def search_with_diversity(
    collection_name: str, 
    query_vector: List[float], 
    user_id: Optional[str] = None,
    k: int = 8,
    min_sources: int = 2
) -> List[Dict]:
    """Search with diversity awareness to ensure results from different sources."""
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
        
        # Get more candidates than needed for diversity selection
        candidates = qdr.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            with_payload=True,
            limit=k * 3  # Get 3x more candidates
        )
        
        if not candidates:
            return []
        
        # Apply diversity selection
        selected = []
        sources_seen = set()
        
        # First pass: select top results from different sources
        for hit in candidates:
            if len(selected) >= k:
                break
                
            # Extract source from payload
            source = "unknown"
            if hit.payload:
                source = hit.payload.get("source", "unknown")
                if not source:
                    source = hit.payload.get("filename", "unknown")
            
            # Add if we need more sources or this source is underrepresented
            if source not in sources_seen or len(sources_seen) < min_sources:
                selected.append({
                    "score": float(hit.score),
                    "payload": hit.payload or {},
                    "id": hit.id,
                    "source": source
                })
                sources_seen.add(source)
        
        # Second pass: fill remaining slots with best remaining results
        remaining = [hit for hit in candidates if hit.id not in [s["id"] for s in selected]]
        for hit in remaining:
            if len(selected) >= k:
                break
            selected.append({
                "score": float(hit.score),
                "payload": hit.payload or {},
                "id": hit.id,
                "source": hit.payload.get("source", "unknown") if hit.payload else "unknown"
            })
        
        # Sort by score and return
        selected.sort(key=lambda x: x["score"], reverse=True)
        return selected[:k]
        
    except Exception as e:
        print(f"❌ Diversity search error: {e}")
        return []
