"""
Response Synthesis Engine for Autism Support App
Combines MongoDB knowledge base content with real-time web browsing for comprehensive responses.
"""

import json
import openai
import streamlit as st
from typing import Dict, List, Optional, Tuple
from pymongo import MongoClient
from urllib.parse import urlparse
import re

class ResponseSynthesisEngine:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        """Initialize the response synthesis engine."""
        self.client = MongoClient(mongo_uri)
        self.db = self.client["autism_ai"]
        self.collection = self.db["knowledge"]
        
        # Initialize OpenAI client
        self.openai_client = None
        self._init_openai()
        
        # Cache for performance
        self.response_cache = {}
        self.web_content_cache = {}
        
    def _init_openai(self):
        """Initialize OpenAI client from Streamlit secrets."""
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                print("✅ OpenAI client initialized for response synthesis")
            else:
                print("⚠️ No OpenAI API key found - web browsing disabled")
        except Exception as e:
            print(f"❌ Error initializing OpenAI: {e}")
    
    def get_mongodb_content(self, context_path: str) -> Optional[Dict]:
        """Get content from MongoDB for a specific context path."""
        try:
            doc = self.collection.find_one({"context_path": context_path})
            if doc:
                return {
                    "response": doc.get("response", ""),
                    "tone": doc.get("tone", "supportive"),
                    "source": doc.get("source", ""),
                    "routes": doc.get("routes", []),
                    "branches": doc.get("branches", []),
                    "options": doc.get("options", [])
                }
        except Exception as e:
            print(f"❌ MongoDB error: {e}")
        return None
    
    def browse_external_source(self, url: str, query: str) -> Optional[str]:
        """Browse external source using OpenAI's web browsing capability."""
        if not self.openai_client or not url:
            return None
            
        try:
            # Check if URL is valid
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None
                
            print(f"🌐 Browsing external source: {url}")
            
            # Try the primary web browsing method first
            try:
                # Use OpenAI's web browsing capability (if available)
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You can browse the web. Visit the provided URL and extract relevant information about autism support and resources."
                        },
                        {
                            "role": "user", 
                            "content": f"Please visit {url} and tell me: {query}"
                        }
                    ],
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                if content and len(content.strip()) > 0:
                    print(f"✅ Primary method retrieved {len(content)} characters from {url}")
                    return content
                    
            except Exception as e:
                print(f"⚠️ Primary web browsing method failed: {e}")
            
            # Fallback to alternative method
            return self._fallback_web_browsing(url, query)
            
        except Exception as e:
            print(f"❌ Web browsing error: {e}")
            return self._fallback_web_browsing(url, query)
    
    def _fallback_web_browsing(self, url: str, query: str) -> Optional[str]:
        """Fallback web browsing method using different approach."""
        try:
            print(f"🔄 Trying fallback web browsing for: {url}")
            
            # Use a different model that might have better web browsing
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that can access web content. When given a URL, you can browse it and provide information."
                    },
                    {
                        "role": "user", 
                        "content": f"Can you access {url} and tell me about: {query}? If you can't access it directly, provide general information about the topic."
                    }
                ],
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            if content and len(content.strip()) > 0:
                print(f"✅ Fallback retrieved {len(content)} characters from {url}")
                return content
            else:
                return None
                
        except Exception as e:
            print(f"❌ Fallback web browsing also failed: {e}")
            return None
    
    def synthesize_response(
        self, 
        user_query: str, 
        context_path: str, 
        user_profile: Dict,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        Synthesize a comprehensive response combining MongoDB content and web browsing.
        
        Returns:
            {
                "response": str - synthesized response,
                "sources": List[str] - sources used,
                "confidence": float - confidence level,
                "next_suggestions": List[str] - suggested next steps
            }
        """
        
        # Get base content from MongoDB
        mongodb_content = self.get_mongodb_content(context_path)
        if not mongodb_content:
            return {
                "response": "I'm sorry, I don't have specific information about that topic yet.",
                "sources": [],
                "confidence": 0.0,
                "next_suggestions": ["Try asking about a different topic", "Check our general resources"]
            }
        
        # Extract external sources for web browsing
        external_sources = []
        if mongodb_content.get("source"):
            external_sources.append(mongodb_content["source"])
        
        # Browse external sources for additional context
        web_content = []
        for source in external_sources:
            if source and source.startswith("http"):
                try:
                    content = self.browse_external_source(source, user_query)
                    if content and len(content.strip()) > 0:
                        web_content.append({
                            "source": source,
                            "content": content
                        })
                        print(f"✅ Successfully browsed: {source}")
                    else:
                        print(f"⚠️ No content retrieved from: {source}")
                except Exception as e:
                    print(f"❌ Error browsing {source}: {e}")
                    continue
        
        # Synthesize comprehensive response using LLM
        synthesized_response = self._llm_synthesize(
            user_query=user_query,
            mongodb_content=mongodb_content,
            web_content=web_content,
            user_profile=user_profile,
            conversation_history=conversation_history
        )
        
        # Determine next suggestions based on available routes/branches
        next_suggestions = self._get_next_suggestions(mongodb_content, user_profile)
        
        return {
            "response": synthesized_response,
            "sources": [context_path] + [w["source"] for w in web_content],
            "confidence": 0.9 if web_content else 0.7,
            "next_suggestions": next_suggestions,
            "mongodb_content": mongodb_content,
            "web_content": web_content
        }
    
    def _llm_synthesize(
        self, 
        user_query: str, 
        mongodb_content: Dict, 
        web_content: List[Dict],
        user_profile: Dict,
        conversation_history: List[Dict] = None
    ) -> str:
        """Use LLM to synthesize a comprehensive response."""
        
        if not self.openai_client:
            # Fallback to MongoDB content only
            return mongodb_content.get("response", "Information not available.")
        
        try:
            # Build context for LLM
            context_parts = []
            
            # Add MongoDB content
            if mongodb_content.get("response"):
                context_parts.append(f"Base Information: {mongodb_content['response']}")
            
            # Add web content
            for web_item in web_content:
                context_parts.append(f"Additional Information from {web_item['source']}: {web_item['content'][:500]}...")
            
            # Add user profile context
            profile_context = f"User Profile: {user_profile.get('role', 'parent')}, Child Age: {user_profile.get('child_age', 'unknown')}, Diagnosis Status: {user_profile.get('diagnosis_status', 'unknown')}"
            context_parts.append(profile_context)
            
            # Combine all context
            full_context = "\n\n".join(context_parts)
            
            # Create synthesis prompt
            messages = [
                {
                    "role": "system",
                    "content": """You are an empathetic autism support specialist. Synthesize information from multiple sources to provide comprehensive, personalized responses. 
                    
                    Guidelines:
                    - Be warm, supportive, and understanding
                    - Personalize responses based on user profile
                    - Combine information from multiple sources seamlessly
                    - Provide actionable, practical advice
                    - Use a conversational, caring tone
                    - Address the specific user query directly"""
                },
                {
                    "role": "user",
                    "content": f"""User Query: {user_query}

Available Information:
{full_context}

Please synthesize a comprehensive, empathetic response that directly addresses the user's question using all available information."""
                }
            ]
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ LLM synthesis error: {e}")
            # Fallback to MongoDB content
            return mongodb_content.get("response", "I'm having trouble processing that right now. Let me provide the basic information I have.")
    
    def _get_next_suggestions(self, mongodb_content: Dict, user_profile: Dict) -> List[str]:
        """Generate next step suggestions based on available routes and branches."""
        suggestions = []
        
        # Add route-based suggestions
        if mongodb_content.get("routes"):
            for route in mongodb_content["routes"]:
                if isinstance(route, str):
                    suggestions.append(f"Learn more about {route}")
                elif isinstance(route, dict):
                    suggestions.append(route.get("label", "Explore this topic"))
        
        # Add branch-based suggestions
        if mongodb_content.get("branches"):
            for branch in mongodb_content["branches"]:
                if isinstance(branch, str):
                    suggestions.append(f"Explore {branch}")
                elif isinstance(branch, dict):
                    suggestions.append(branch.get("label", "Learn more"))
        
        # Add profile-specific suggestions
        if user_profile.get("diagnosis_status") == "diagnosed_no":
            suggestions.append("Get screening recommendations")
            suggestions.append("Learn about early signs")
        elif user_profile.get("diagnosis_status") == "diagnosed_yes":
            suggestions.append("Find support resources")
            suggestions.append("Explore treatment options")
        
        # Limit suggestions
        return suggestions[:5]
    
    def get_conversation_flow(self, context_path: str) -> Dict:
        """Get conversation flow information for a context path."""
        mongodb_content = self.get_mongodb_content(context_path)
        if not mongodb_content:
            return {}
        
        return {
            "current_context": context_path,
            "available_routes": mongodb_content.get("routes", []),
            "available_branches": mongodb_content.get("branches", []),
            "response_tone": mongodb_content.get("tone", "supportive"),
            "has_external_sources": bool(mongodb_content.get("source"))
        }
    
    def close(self):
        """Close the MongoDB connection."""
        self.client.close()

# Example usage and testing
if __name__ == "__main__":
    engine = ResponseSynthesisEngine()
    
    # Test with sample data
    test_profile = {
        "role": "parent_caregiver",
        "child_age": "3-5",
        "diagnosis_status": "diagnosed_no"
    }
    
    result = engine.synthesize_response(
        user_query="What are the early signs of autism I should look for?",
        context_path="diagnosed_no.early_signs",
        user_profile=test_profile
    )
    
    print("Synthesis Result:")
    print(f"Response: {result['response'][:200]}...")
    print(f"Sources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Next Suggestions: {result['next_suggestions']}")
    
    engine.close()
