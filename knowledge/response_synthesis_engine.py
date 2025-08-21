"""
Response Synthesis Engine for Autism Support App
Combines MongoDB knowledge base content with real-time web browsing for comprehensive responses.
"""

import json
import openai
import streamlit as st
import requests
from bs4 import BeautifulSoup
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
        
        # Define web browsing tool
        self.web_fetch_tool = {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "Fetch a URL and return clean text content for autism support resources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Absolute URL to fetch"}
                    },
                    "required": ["url"]
                }
            }
        }
        
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
    
    def web_fetch(self, url: str) -> Dict:
        """Fetch a URL and return clean text content."""
        try:
            # Keep it simple & safe
            headers = {"User-Agent": "AutismSupportApp/1.0"}
            r = requests.get(url, headers=headers, timeout=12)
            r.raise_for_status()
            
            # Parse HTML and extract clean text
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Strip script/style and get text
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            
            text = " ".join(soup.get_text(separator=" ").split())
            
            # Return bounded payload
            return {
                "content": text[:20000],  # Limit to 20K chars
                "status": r.status_code,
                "url": url,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Web fetch error for {url}: {e}")
            return {
                "content": f"Failed to fetch content from {url}: {str(e)}",
                "status": 0,
                "url": url,
                "success": False
            }
    
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
        """Browse external source using OpenAI native web search with custom scraping fallback."""
        if not self.openai_client or not url:
            return None
            
        try:
            # Check if URL is valid
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None
                
            print(f"🌐 Browsing external source: {url}")
            
            # Try OpenAI native web search first (PRIMARY METHOD)
            try:
                print("🔍 Trying OpenAI native web search...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-search-preview",  # Native web search model
                    web_search_options={},  # Enable web search
                    messages=[
                        {
                            "role": "user",
                            "content": f"Search for information about: {query}. Focus on autism support, screening, and resources."
                        }
                    ],
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                if content and len(content.strip()) > 0:
                    print(f"✅ OpenAI native web search: {len(content)} characters")
                    print(f"   First 100 chars: {content[:100]}...")
                    return content
                else:
                    print("⚠️ OpenAI native web search returned empty content")
                    
            except Exception as e:
                print(f"⚠️ OpenAI native web search failed: {e}")
            
            # Fallback to our custom web scraping (FALLBACK METHOD)
            print("🔄 Falling back to custom web scraping...")
            return self._custom_web_scraping(url, query)
            
        except Exception as e:
            print(f"❌ Web browsing error: {e}")
            return None
    
    def _custom_web_scraping(self, url: str, query: str) -> Optional[str]:
        """Custom web scraping fallback using requests and BeautifulSoup."""
        try:
            print(f"🔄 Custom web scraping for: {url}")
            
            # Use our existing web_fetch function
            result = self.web_fetch(url)
            
            if result.get("success") and result.get("content"):
                print(f"✅ Custom scraping: {len(result['content'])} characters")
                return result["content"]
            else:
                print(f"⚠️ Custom scraping failed: {result.get('content', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Custom web scraping error: {e}")
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
            # Provide a helpful response even when no specific content is found
            diagnosis_status = user_profile.get("diagnosis_status", "unknown")
            role = user_profile.get("role", "parent")
            
            if diagnosis_status == "diagnosed_no":
                response = "I understand you're looking for information about autism support. Since your child hasn't been diagnosed yet, I'd recommend starting with developmental screening and monitoring. Would you like to learn more about early signs, screening options, or finding evaluation services?"
            elif diagnosis_status == "diagnosed_yes":
                response = "I'm here to help you with autism support resources. Since your child has been diagnosed, I can help you find treatment options, support services, educational resources, and community connections. What specific area would you like to explore?"
            else:
                response = "I'm here to help you with autism support and resources. I can provide information about screening, diagnosis, treatment options, support services, and educational resources. What would you like to learn more about?"
            
            return {
                "response": response,
                "sources": [],
                "confidence": 0.5,
                "next_suggestions": ["Learn about screening options", "Find support resources", "Explore treatment options"]
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
            
            # Add conversation history context for continuity
            if conversation_history:
                recent_history = conversation_history[-3:]  # Last 3 exchanges
                history_context = "Recent Conversation History:\n"
                for msg in recent_history:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    content = msg.get("content", "")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", "")
                    history_context += f"{role}: {content}\n"
                context_parts.append(history_context)
            
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
            # Fallback to MongoDB content with better response
            base_response = mongodb_content.get("response", "")
            if base_response:
                return base_response
            else:
                return "I'm here to help you with autism support. Let me provide some general guidance based on your situation. What specific questions do you have about autism support or resources?"
    
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
    
    def test_web_browsing_methods(self, query: str = "autism screening guidelines") -> Dict:
        """Test both web browsing methods to compare performance."""
        print("🧪 Testing Web Browsing Methods")
        print("=" * 40)
        
        results = {}
        
        # Test OpenAI native web search
        try:
            print("\n🔍 Testing OpenAI Native Web Search...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-search-preview",
                web_search_options={},
                messages=[{
                    "role": "user",
                    "content": f"Search for information about: {query}"
                }],
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            if content:
                results["openai_native"] = {
                    "success": True,
                    "content_length": len(content),
                    "content_preview": content[:200] + "...",
                    "method": "OpenAI Native Web Search"
                }
                print(f"✅ OpenAI native: {len(content)} characters")
            else:
                results["openai_native"] = {
                    "success": False,
                    "error": "Empty content returned"
                }
                print("❌ OpenAI native: Empty content")
                
        except Exception as e:
            results["openai_native"] = {
                "success": False,
                "error": str(e)
            }
            print(f"❌ OpenAI native failed: {e}")
        
        # Test custom web scraping with a known working URL
        try:
            print("\n🔄 Testing Custom Web Scraping...")
            test_url = "https://www.cdc.gov/ncbddd/actearly/screening.html"
            result = self.web_fetch(test_url)
            
            if result.get("success") and result.get("content"):
                results["custom_scraping"] = {
                    "success": True,
                    "content_length": len(result["content"]),
                    "content_preview": result["content"][:200] + "...",
                    "method": "Custom Web Scraping",
                    "url": test_url
                }
                print(f"✅ Custom scraping: {len(result['content'])} characters")
            else:
                results["custom_scraping"] = {
                    "success": False,
                    "error": result.get("content", "Unknown error")
                }
                print(f"❌ Custom scraping failed: {result.get('content', 'Unknown error')}")
                
        except Exception as e:
            results["custom_scraping"] = {
                "success": False,
                "error": str(e)
            }
            print(f"❌ Custom scraping error: {e}")
        
        # Summary
        print(f"\n📊 Test Results Summary:")
        print(f"   OpenAI Native: {'✅' if results.get('openai_native', {}).get('success') else '❌'}")
        print(f"   Custom Scraping: {'✅' if results.get('custom_scraping', {}).get('success') else '❌'}")
        
        return results
    
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
