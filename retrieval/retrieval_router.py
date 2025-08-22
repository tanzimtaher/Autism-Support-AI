"""
Retrieval Router for Autism Support App
Routes queries between MongoDB structured data and vector search.
"""

from typing import Dict, Tuple, List
# from app.services.knowledge_adapter import KnowledgeAdapter  # Commented out - class doesn't exist
from rag.qdrant_client import search_with_user_filter
from rag.embeddings import embed_single

class RetrievalRouter:
    """Routes queries between structured MongoDB and vector search."""
    
    def __init__(self, ka=None):  # ka parameter made optional since KnowledgeAdapter doesn't exist
        self.ka = ka
        # self.safety = set(ka.get_safety_rules().get("critical_terms", []))  # Commented out - ka doesn't exist
        self.safety = set()  # Empty set for now

    def route(self, user_query: str, user_profile: Dict, context_path: str) -> Tuple[str, List]:
        """
        Route query to appropriate knowledge sources.
        
        Returns:
            Tuple of (mode, results) where mode is:
            - "mongo_only": Use only structured MongoDB data
            - "blend": Combine MongoDB + vector search
            - "vector_only": Use only vector search
        """
        
        # 1) Safety first - check for critical terms
        if any(term.lower() in user_query.lower() for term in self.safety):
            print(f"🚨 Safety term detected in query: {user_query}")
            return "mongo_only", []

        # 2) If inside a guided step, prefer mongo + enrich with vector
        if context_path and any(flow in context_path for flow in ["diagnosed_no", "diagnosed_yes", "adult_self"]):
            print(f"🔄 Guided conversation detected: {context_path}")
            # Get vector results to enrich the guided response
            vector_results = self._get_vector_results(user_query, user_profile, limit=3)
            return "blend", vector_results

        # 3) Otherwise semantic-first with optional guided hints
        print(f"🔍 Free-form query detected: {user_query}")
        vector_results = self._get_vector_results(user_query, user_profile, limit=6)
        return "vector_only", vector_results

    def _get_vector_results(self, query: str, user_profile: Dict, limit: int = 6) -> List:
        
        try:
            # Generate embedding for query
            query_vector = embed_single(query)
            if not query_vector:
                print("❌ Failed to generate embedding")
                return []
            
            # Get user ID for filtering
            user_id = user_profile.get("user_id", "public")
            
            all_results = []
            
            # 1. Search shared knowledge base with diversity
            from rag.qdrant_client import search_with_diversity
            shared_results = search_with_diversity(
                collection_name="kb_autism_support",
                query_vector=query_vector,
                user_id=user_id,
                k=limit // 2,  # Half from shared KB
                min_sources=2  # Ensure at least 2 different sources
            )
            all_results.extend(shared_results)
            
            # 2. Search user's private documents (if user has documents)
            if user_id != "public":
                from rag.ingest_user_docs import search_user_documents
                try:
                    user_results = search_user_documents(user_id, query, limit // 2)
                    if user_results:
                        print(f"✅ Found {len(user_results)} user document results")
                        all_results.extend(user_results)
                    else:
                        print(f"⚠️ No user document results found for user {user_id}")
                except Exception as e:
                    print(f"❌ Error searching user documents: {e}")
                    # Try alternative search method
                    try:
                        from rag.qdrant_client import search_with_user_filter
                        user_results = search_with_user_filter(
                            collection_name=f"user_docs_{user_id}",
                            query_vector=query_vector,
                            user_id=user_id,
                            k=limit // 2
                        )
                        if user_results:
                            print(f"✅ Found {len(user_results)} user document results (alternative method)")
                            all_results.extend(user_results)
                    except Exception as e2:
                        print(f"❌ Alternative user document search also failed: {e2}")
            
            # Sort by score and limit
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            all_results = all_results[:limit]
            
            # Log diversity information
            sources = set()
            for result in all_results:
                if result.get("payload"):
                    source = result["payload"].get("source", "unknown")
                    if not source:
                        source = result["payload"].get("filename", "unknown")
                    sources.add(source)
            
            print(f"✅ Found {len(all_results)} vector results from {len(sources)} sources ({len(shared_results)} shared, {len(user_results) if user_id != 'public' else 0} private)")
            return all_results
            
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []

    def get_safety_warning(self, query: str) -> str:
        """Get safety warning if critical terms detected."""
        detected_terms = [term for term in self.safety if term.lower() in query.lower()]
        if detected_terms:
            return f"⚠️ Safety Alert: Detected critical terms: {', '.join(detected_terms)}. Please contact a healthcare professional immediately."
        return ""

    def get_guided_hint(self, context_path: str) -> Dict:
        """Get a short guided hint from the current context."""
        # try:
        #     node = self.ka.get_node(context_path)  # Commented out - ka doesn't exist
        #     if node:
        #         return {
        #             "label": node.get("label", "Continue"),
        #             "next_steps": self.ka.get_available_paths(context_path)[:3]  # Commented out - ka doesn't exist
        #         }
        # except Exception as e:
        #     print(f"❌ Error getting guided hint: {e}")
        
        return {"label": "Continue", "next_steps": []}
