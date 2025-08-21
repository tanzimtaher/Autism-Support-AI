"""
Ingest User Documents for Autism Support App
Processes user-specific documents and ingests them into a private vector store.
"""

import json
import uuid
import os
from pathlib import Path
from qdrant_client.models import PointStruct
from .qdrant_client import ensure_collection
from .embeddings import embed
from .process_admin_docs import extract_text_from_file
from typing import List, Dict
import hashlib

def chunk_text(text: str, max_tokens: int = 4000) -> List[str]:
    """Split text into chunks of approximately max_tokens."""
    # Simple chunking by sentences and paragraphs
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # Rough token estimation (1 token ≈ 4 characters)
        if len(current_chunk + sentence) * 0.25 > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += sentence + ". "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Ensure chunks aren't too long
    final_chunks = []
    for chunk in chunks:
        if len(chunk) * 0.25 > max_tokens:
            # Split long chunks by paragraphs
            paragraphs = chunk.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    final_chunks.append(para.strip())
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def check_content_similarity(chunk1: str, chunk2: str, threshold: float = 0.8) -> bool:
    """Check if two chunks are similar using simple text comparison."""
    try:
        # Normalize text
        def normalize(text):
            return ' '.join(text.lower().split())
        
        norm1 = normalize(chunk1)
        norm2 = normalize(chunk2)
        
        # If chunks are identical after normalization
        if norm1 == norm2:
            return True
        
        # Check for significant overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_similarity = len(intersection) / len(union)
        
        # Also check for substring similarity for longer texts
        if len(norm1) > 50 and len(norm2) > 50:
            # Check if one is a significant substring of the other
            if norm1 in norm2 or norm2 in norm1:
                return True
        
        return jaccard_similarity > threshold
        
    except Exception as e:
        print(f"⚠️ Content similarity check failed: {e}")
        return False

def check_duplicate_content(new_chunk: str, existing_chunks: List[str], threshold: float = 0.8) -> bool:
    """Check if new chunk is similar to any existing chunks."""
    for existing in existing_chunks:
        if check_content_similarity(new_chunk, existing, threshold):
            return True
    return False

def ingest_user_documents(user_id: str, docs_dir: str) -> int:
    """
    Ingest user-specific documents into their private vector store.
    
    Args:
        user_id: Unique identifier for the user
        docs_dir: Directory containing user's documents
        
    Returns:
        Number of documents successfully ingested
    """
    print(f"🚀 Starting user document ingestion for user: {user_id}")
    
    try:
        # Ensure user-specific collection exists
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        if not qdr:
            print("❌ Failed to create/connect to user collection")
            return 0
        
        # Check if documents directory exists
        docs_path = Path(docs_dir)
        if not docs_path.exists():
            print(f"❌ User documents directory not found: {docs_dir}")
            return 0
        
        # Get existing documents in the collection to check for duplicates
        existing_docs = set()
        existing_chunks = []
        try:
            # Get all existing documents for this user
            existing_points = qdr.scroll(
                collection_name=collection_name,
                limit=1000,  # Adjust based on expected document count
                with_payload=True
            )[0]
            
            for point in existing_points:
                payload = point.payload
                if payload and "filename" in payload:
                    existing_docs.add(payload["filename"])
                if payload and "content" in payload:
                    existing_chunks.append(payload["content"])
            
            print(f"📋 Found {len(existing_docs)} existing documents and {len(existing_chunks)} chunks in collection")
        except Exception as e:
            print(f"⚠️ Could not check existing documents: {e}")
        
        # Process documents
        documents = []
        new_files = []
        skipped_files = []
        duplicate_chunks = []
        
        for file_path in docs_path.glob("*"):
            if file_path.is_file():
                # Check if this file is already in the collection
                if file_path.name in existing_docs:
                    print(f"⏭️ Skipping duplicate: {file_path.name}")
                    skipped_files.append(file_path.name)
                    continue
                
                try:
                    content = extract_text_from_file(file_path)
                    if content:
                        # Chunk the content to avoid token limits
                        chunks = chunk_text(content)
                        print(f"✅ Processed: {file_path.name} into {len(chunks)} chunks")
                        new_files.append(file_path.name)
                        
                        for i, chunk in enumerate(chunks):
                            # Check for content duplicates
                            if check_duplicate_content(chunk, existing_chunks, threshold=0.8):
                                print(f"🔄 Skipping duplicate content: {file_path.name} chunk {i+1}")
                                duplicate_chunks.append(f"{file_path.name} chunk {i+1}")
                                continue
                            
                            # Create document entry for each chunk
                            doc_entry = {
                                "filename": file_path.name,
                                "content": chunk,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "type": "user_document",
                                "source": "user_upload",
                                "user_id": user_id,
                                "metadata": {
                                    "file_size": file_path.stat().st_size,
                                    "file_type": file_path.suffix.lower(),
                                    "upload_timestamp": str(file_path.stat().st_mtime),
                                    "file_hash": str(hash(file_path.name + str(file_path.stat().st_size) + str(file_path.stat().st_mtime)))
                                }
                            }
                            documents.append(doc_entry)
                            # Add to existing chunks for future duplicate checks
                            existing_chunks.append(chunk)
                    else:
                        print(f"⚠️ No content extracted from: {file_path.name}")
                except Exception as e:
                    print(f"❌ Error processing {file_path.name}: {e}")
        
        if not documents:
            if skipped_files:
                print(f"ℹ️ All files were duplicates. Skipped: {', '.join(skipped_files)}")
            if duplicate_chunks:
                print(f"ℹ️ All chunks were duplicates. Skipped: {', '.join(duplicate_chunks)}")
            else:
                print("⚠️ No documents to ingest")
            return 0
        
        # Prepare texts for embedding
        texts = []
        for doc in documents:
            # Create content for embedding (shorter to avoid token limits)
            content = f"{doc['filename']} (chunk {doc['chunk_index']+1}/{doc['total_chunks']})\n{doc['content'][:2000]}"
            texts.append(content)
        
        # Generate embeddings in batches to avoid rate limits
        print("🔍 Generating embeddings for user documents...")
        batch_size = 10
        all_vectors = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_vectors = embed(batch_texts)
            if batch_vectors:
                all_vectors.extend(batch_vectors)
            else:
                print(f"❌ Failed to generate embeddings for batch {i//batch_size + 1}")
        
        if not all_vectors:
            print("❌ Failed to generate embeddings")
            return 0
        
        # Create points for Qdrant
        points = []
        for doc, vector in zip(documents, all_vectors):
            point_id = uuid.uuid4().hex
            payload = {
                "filename": doc["filename"],
                "content": doc["content"],
                "chunk_index": doc["chunk_index"],
                "total_chunks": doc["total_chunks"],
                "type": "user_document",
                "source": "user_upload",
                "user_id": user_id,
                "file_type": doc["metadata"]["file_type"],
                "upload_timestamp": doc["metadata"]["upload_timestamp"],
                "file_hash": doc["metadata"]["file_hash"]
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
        
        # Insert into Qdrant
        print(f"📤 Inserting {len(points)} new document chunks into Qdrant...")
        qdr.upsert(collection_name=collection_name, points=points)
        
        print(f"✅ Successfully ingested {len(points)} new document chunks")
        if skipped_files:
            print(f"⏭️ Skipped {len(skipped_files)} duplicate files: {', '.join(skipped_files)}")
        if duplicate_chunks:
            print(f"🔄 Skipped {len(duplicate_chunks)} duplicate content chunks")
        
        return len(points)
        
    except Exception as e:
        print(f"❌ User document ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def search_user_documents(user_id: str, query: str, limit: int = 5) -> list:
    """
    Search user's private documents.
    
    Args:
        user_id: Unique identifier for the user
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of search results
    """
    try:
        from .qdrant_client import search_with_user_filter
        from .embeddings import embed_single
        
        # Generate query embedding
        query_vector = embed_single(query)
        if not query_vector:
            return []
        
        # Search user's private collection
        collection_name = f"user_docs_{user_id}"
        results = search_with_user_filter(
            collection_name=collection_name,
            query_vector=query_vector,
            user_id=user_id,  # This ensures only user's documents are searched
            k=limit
        )
        
        return results
        
    except Exception as e:
        print(f"❌ User document search failed: {e}")
        return []

def get_user_documents(user_id: str) -> list:
    """
    Get list of user's uploaded documents.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        List of document information
    """
    try:
        from .qdrant_client import get_qdrant
        
        qdr = get_qdrant()
        if not qdr:
            return []
        
        collection_name = f"user_docs_{user_id}"
        
        # Get all documents for the user
        results = qdr.scroll(
            collection_name=collection_name,
            scroll_filter={"must": [{"key": "user_id", "match": {"value": user_id}}]},
            limit=100
        )
        
        documents = []
        for point in results[0]:
            documents.append({
                "filename": point.payload.get("filename", "Unknown"),
                "file_type": point.payload.get("file_type", "Unknown"),
                "upload_timestamp": point.payload.get("upload_timestamp", ""),
                "content_preview": point.payload.get("content", "")[:200] + "..."
            })
        
        return documents
        
    except Exception as e:
        print(f"❌ Failed to get user documents: {e}")
        return []

def check_existing_documents(user_id: str) -> dict:
    """
    Check what documents already exist in the user's collection.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary with existing document information
    """
    try:
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        if not qdr:
            return {"error": "Could not connect to vector store"}
        
        # Get all existing documents
        existing_points = qdr.scroll(
            collection_name=collection_name,
            limit=1000,
            with_payload=True
        )[0]
        
        # Group by filename
        doc_info = {}
        for point in existing_points:
            payload = point.payload
            if payload and "filename" in payload:
                filename = payload["filename"]
                if filename not in doc_info:
                    doc_info[filename] = {
                        "chunks": 0,
                        "upload_timestamp": payload.get("upload_timestamp", "unknown"),
                        "file_type": payload.get("file_type", "unknown")
                    }
                doc_info[filename]["chunks"] += 1
        
        return {
            "total_documents": len(doc_info),
            "total_chunks": len(existing_points),
            "documents": doc_info
        }
        
    except Exception as e:
        return {"error": f"Failed to check existing documents: {e}"}

def delete_user_document(user_id: str, filename: str) -> bool:
    """
    Delete a specific document from the user's collection.
    
    Args:
        user_id: Unique identifier for the user
        filename: Name of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        if not qdr:
            return False
        
        # Find all points for this filename
        existing_points = qdr.scroll(
            collection_name=collection_name,
            limit=1000,
            with_payload=True,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename",
                        match=models.MatchValue(value=filename)
                    )
                ]
            )
        )[0]
        
        if not existing_points:
            print(f"⚠️ No document found with filename: {filename}")
            return False
        
        # Delete all chunks for this document
        point_ids = [point.id for point in existing_points]
        qdr.delete(collection_name=collection_name, points_selector=point_ids)
        
        print(f"✅ Deleted {len(point_ids)} chunks for document: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to delete document {filename}: {e}")
        return False

def clear_user_documents(user_id: str) -> bool:
    """
    Clear all documents for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        True if successful, False otherwise
    """
    try:
        collection_name = f"user_docs_{user_id}"
        qdr = ensure_collection(collection_name, size=1536)
        if not qdr:
            return False
        
        # Delete all points in the collection
        qdr.delete(collection_name=collection_name, points_selector=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
        ))
        
        print(f"✅ Cleared all documents for user: {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear documents for user {user_id}: {e}")
        return False

if __name__ == "__main__":
    # Test user document ingestion
    test_user_id = "test_user_123"
    test_docs_dir = "data/user_docs/test_user_123"
    
    count = ingest_user_documents(test_user_id, test_docs_dir)
    print(f"Test completed: {count} documents ingested")
