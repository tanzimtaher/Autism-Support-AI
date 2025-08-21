"""
Ingest shared knowledge base into Qdrant
"""

import json
import uuid
import os
from pathlib import Path
from qdrant_client.models import PointStruct
from .qdrant_client import ensure_collection
from .embeddings import embed

COLLECTION_NAME = "kb_autism_support"

def main():
    """Ingest shared knowledge base into Qdrant."""
    print("🚀 Starting shared knowledge base ingestion...")
    
    try:
        # Ensure collection exists
        qdr = ensure_collection(COLLECTION_NAME, size=1536)
        if not qdr:
            print("❌ Failed to create/connect to Qdrant collection")
            return False
        
        # Load structured knowledge
        json_path = Path("knowledge/structured_mongo.json")
        if not json_path.exists():
            print("❌ structured_mongo.json not found")
            return False
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten the knowledge structure
        flat_docs = flatten_knowledge(data)
        print(f"📋 Flattened {len(flat_docs)} knowledge items")
        
        # Prepare texts and metadata
        texts, points = [], []
        for doc in flat_docs:
            # Create content for embedding
            content = f"{doc.get('label', '')}\n{doc.get('response', '')}\nSource:{doc.get('source', '')}"
            texts.append(content)
        
        # Generate embeddings
        print("🔍 Generating embeddings...")
        vectors = embed(texts)
        if not vectors:
            print("❌ Failed to generate embeddings")
            return False
        
        # Create points for Qdrant
        for doc, vector in zip(flat_docs, vectors):
            point_id = uuid.uuid4().hex
            payload = {
                "context_path": doc["context_path"],
                "label": doc.get("label", ""),
                "response": doc.get("response", ""),
                "tone": doc.get("tone", "neutral"),
                "source": doc.get("source", ""),
                "user_id": "public",  # Shared knowledge
                "type": "knowledge_base"
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
        
        # Insert into Qdrant
        print(f"📤 Inserting {len(points)} points into Qdrant...")
        qdr.upsert(collection_name=COLLECTION_NAME, points=points)
        
        print(f"✅ Successfully ingested {len(points)} knowledge items")
        return True
        
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def flatten_knowledge(data, parent_path="", out=None):
    """Recursively flatten the knowledge structure."""
    if out is None:
        out = []
    
    if isinstance(data, dict):
        # Check if this is a content node
        if "label" in data and "response" in data:
            out.append({
                "context_path": parent_path.strip(" ."),
                "label": data.get("label", ""),
                "response": data.get("response", ""),
                "tone": data.get("tone", "neutral"),
                "source": data.get("source", "")
            })
        
        # Recurse into nested structures
        for key, value in data.items():
            if key in ["label", "response", "tone", "source"]:
                continue
            new_path = f"{parent_path}.{key}" if parent_path else key
            flatten_knowledge(value, new_path, out)
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_path = f"{parent_path}[{i}]" if parent_path else f"[{i}]"
            flatten_knowledge(item, new_path, out)
    
    return out

if __name__ == "__main__":
    success = main()
    if success:
        print("🎉 Shared knowledge base ingestion completed!")
    else:
        print("⚠️ Ingestion failed!")
