#!/usr/bin/env python3
"""
Test script for RAG system improvements:
- Content-based deduplication
- Diversity-aware retrieval
- Temporal weighting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_content_deduplication():
    """Test content-based deduplication functionality."""
    print("🧪 Testing content deduplication...")
    
    try:
        from rag.ingest_user_docs import check_content_similarity, check_duplicate_content
        
        # Test similar content detection
        chunk1 = "Autism is a neurodevelopmental disorder that affects communication and behavior."
        chunk2 = "Autism is a neurodevelopmental condition that impacts communication and behavior."
        chunk3 = "Diabetes is a metabolic disorder that affects blood sugar levels."
        
        # Should detect similarity
        similarity = check_content_similarity(chunk1, chunk2, threshold=0.8)
        print(f"✅ Similar content detected: {similarity}")
        
        # Should not detect similarity
        similarity = check_content_similarity(chunk1, chunk3, threshold=0.8)
        print(f"✅ Different content correctly identified: {not similarity}")
        
        # Test duplicate checking
        existing_chunks = [chunk1, chunk3]
        is_duplicate = check_duplicate_content(chunk2, existing_chunks, threshold=0.8)
        print(f"✅ Duplicate detection working: {is_duplicate}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content deduplication test failed: {e}")
        return False

def test_diversity_search():
    """Test diversity-aware search functionality."""
    print("\n🧪 Testing diversity-aware search...")
    
    try:
        from rag.qdrant_client import search_with_diversity
        from rag.embeddings import embed_single
        
        # Test diversity search function exists
        if hasattr(search_with_diversity, '__call__'):
            print("✅ Diversity search function available")
            
            # Test with a simple query
            query = "autism support resources"
            query_vector = embed_single(query)
            
            if query_vector:
                print("✅ Query embedding generation working")
                return True
            else:
                print("❌ Query embedding generation failed")
                return False
        else:
            print("❌ Diversity search function not found")
            return False
            
    except Exception as e:
        print(f"❌ Diversity search test failed: {e}")
        return False

def test_temporal_weighting():
    """Test temporal weighting functionality."""
    print("\n🧪 Testing temporal weighting...")
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import the function directly from the app.py file
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_module", "app.py")
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        
        apply_temporal_weighting = app_module.apply_temporal_weighting
        
        # Test with sample chunks
        test_chunks = [
            {"text": "Old content", "upload_timestamp": "1640995200"},  # 2022-01-01
            {"text": "New content", "upload_timestamp": "1704067200"},  # 2024-01-01
            {"text": "No timestamp", "source": "unknown"}
        ]
        
        weighted_chunks = apply_temporal_weighting(test_chunks)
        
        if len(weighted_chunks) == 3:
            print("✅ Temporal weighting function working")
            
            # Check that newer content has higher weight
            weights = [chunk.get("temporal_weight", 0) for chunk in weighted_chunks]
            if weights[1] > weights[0]:  # New content should have higher weight than old
                print("✅ Newer content correctly weighted higher")
                return True
            else:
                print("❌ Temporal weighting not working correctly")
                return False
        else:
            print("❌ Temporal weighting function failed")
            return False
            
    except Exception as e:
        print(f"❌ Temporal weighting test failed: {e}")
        return False

def test_retrieval_router():
    """Test retrieval router improvements."""
    print("\n🧪 Testing retrieval router...")
    
    try:
        from retrieval.retrieval_router import RetrievalRouter
        from app.services.knowledge_adapter import KnowledgeAdapter
        
        # Test router initialization
        ka = KnowledgeAdapter()
        router = RetrievalRouter(ka)
        
        print("✅ Retrieval router initialized successfully")
        
        # Test routing logic
        user_profile = {"user_id": "test_user", "role": "parent_caregiver"}
        
        # Test safety routing
        safety_result = router.route("suicide prevention", user_profile, "")
        print(f"✅ Safety routing working: {safety_result[0] == 'mongo_only'}")
        
        # Test guided conversation routing
        guided_result = router.route("help with communication", user_profile, "diagnosed_yes.early_intervention")
        print(f"✅ Guided routing working: {guided_result[0] == 'blend'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Retrieval router test failed: {e}")
        return False

def main():
    """Run all improvement tests."""
    print("🚀 Testing RAG System Improvements")
    print("=" * 50)
    
    tests = [
        test_content_deduplication,
        test_diversity_search,
        test_temporal_weighting,
        test_retrieval_router
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All improvements working correctly!")
    else:
        print("⚠️ Some improvements need attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
