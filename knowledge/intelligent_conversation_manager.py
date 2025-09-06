"""
Intelligent Conversation Manager for Autism Support App
Integrates Response Synthesis Engine with guided conversation flows for dynamic, intelligent conversations.
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from .response_synthesis_engine import ResponseSynthesisEngine
from .context_traversal_engine import ContextTraversalEngine

# Add new imports for dual-index system
from .knowledge_adapter import KnowledgeAdapter
from retrieval.retrieval_router import RetrievalRouter
from .conversation_memory_manager import ConversationMemoryManager

class IntelligentConversationManager:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        """Initialize the intelligent conversation manager."""
        self.response_engine = ResponseSynthesisEngine(mongo_uri)
        self.context_engine = ContextTraversalEngine(mongo_uri)
        
        # Add new dual-index components
        self.knowledge_adapter = KnowledgeAdapter()
        # Create a minimal retrieval router for safety checks
        try:
            self.retrieval_router = RetrievalRouter()
        except Exception as e:
            print(f"⚠️ Could not initialize retrieval router: {e}")
            self.retrieval_router = None
        
        # Conversation state
        self.current_context_path = None
        self.conversation_history = []
        self.user_profile = {}
        self.available_paths = []
        
        # Conversation memory for context continuity
        self.conversation_memory = {
            "patient_info": {},
            "discussed_topics": set(),
            "user_concerns": [],
            "recommendations_given": []
        }
        
        # Initialize memory manager (will be set when user_profile is available)
        self.memory_manager = None
        
        # Generate user ID if not exists
        if "user_id" not in self.user_profile:
            self.user_profile["user_id"] = "default"
        
    def start_conversation(self, user_profile: Dict) -> Dict:
        """Start a new intelligent conversation based on user profile."""
        self.user_profile.update(user_profile)
        self.conversation_history = []
        
        # Initialize memory manager for this user
        self._initialize_memory_manager()
        
        # Use knowledge adapter for initial context
        initial_path = self.knowledge_adapter.get_initial_context(self.user_profile)
        self.current_context_path = initial_path
        
        # Get initial response using synthesis engine
        initial_response = self.response_engine.synthesize_response(
            user_query="Start conversation",
            context_path=initial_path,
            user_profile=self.user_profile,
            vector_results=[]
        )
        
        # Get available conversation paths using knowledge adapter
        self.available_paths = self.knowledge_adapter.get_available_paths(initial_path)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": initial_response["response"],
            "context_path": initial_path,
            "sources": initial_response["sources"],
            "next_suggestions": initial_response["next_suggestions"]
        })
        
        return {
            "response": initial_response["response"],
            "context_path": initial_path,
            "next_suggestions": initial_response["next_suggestions"],
            "available_paths": self.available_paths,
            "conversation_id": self._generate_conversation_id()
        }
    
    def process_user_response(self, user_input: str, selected_path: str = None) -> Dict:
        """Process user input and generate intelligent response."""
        
        try:
            # Extract and remember user-provided facts
            self._extract_and_remember_facts(user_input)
            
            # Add user input to history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": self._get_timestamp()
            })
        
            # Store user message in conversation memory
            self._store_conversation_memory({
                "role": "user",
                "content": user_input,
                "timestamp": self._get_timestamp()
            })
            
            # Extract insights periodically (every 10 messages)
            if len(self.conversation_history) % 10 == 0:
                self._extract_and_store_insights()
            
            # Check for safety terms first
            safety_warning = ""
            if self.retrieval_router:
                safety_warning = self.retrieval_router.get_safety_warning(user_input)
                if safety_warning:
                    return {
                        "response": safety_warning,
                        "context_path": self.current_context_path,
                        "next_suggestions": [],
                        "available_paths": self.available_paths,
                        "confidence": 1.0,
                        "sources": [],
                        "safety_warning": True
                    }
        
            # Determine next context path
            if selected_path:
                next_context = selected_path
            else:
                next_context = self._determine_next_context(user_input)
        
            # Update current context
            self.current_context_path = next_context
        
            # Use retrieval router to decide knowledge source
            mode, vector_results = "vector_only", []
            if self.retrieval_router:
                try:
                    mode, vector_results = self.retrieval_router.route(
                        user_input, 
                        self.user_profile, 
                        next_context
                    )
                except Exception as e:
                    print(f"⚠️ Retrieval router failed: {e}")
                    mode, vector_results = "vector_only", []
        
            # Generate response based on routing mode
            if mode == "mongo_only":
                # Use only structured MongoDB data
                response = self.response_engine.synthesize_response(
                    user_query=user_input,
                    context_path=next_context,
                    user_profile=self.user_profile,
                        conversation_history=self.conversation_history,
                        vector_results=[]
                )
            elif mode == "blend":
                # Combine MongoDB + vector search
                response = self._synthesize_blended_response(
                    user_input, next_context, vector_results
                )
            else:  # vector_only
                # Use vector search with guided hints
                response = self._synthesize_vector_response(
                    user_input, next_context, vector_results
                )
        
            # Update available paths
            self.available_paths = self.knowledge_adapter.get_available_paths(next_context)
                
            # Update conversation memory
            self._update_conversation_memory(user_input, response)
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response["response"],
                "context_path": next_context,
                "sources": response["sources"],
                "next_suggestions": response["next_suggestions"],
                "timestamp": self._get_timestamp()
            })
            
            # Store assistant response in conversation memory
            self._store_conversation_memory({
                "role": "assistant",
                "content": response["response"],
                "context_path": next_context,
                "sources": response["sources"],
                "next_suggestions": response["next_suggestions"],
                "timestamp": self._get_timestamp()
            })
        
            return {
                "response": response["response"],
                "context_path": next_context,
                "next_suggestions": response["next_suggestions"],
                "available_paths": self.available_paths,
                "confidence": response.get("confidence", 0.8),
                "sources": response["sources"],
                "mode": mode
            }
        
        except Exception as e:
            print(f"❌ Error processing user response: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "context_path": self.current_context_path,
                "next_suggestions": [],
                "available_paths": [],
                "confidence": 0.0,
                "sources": [],
                "mode": "error"
            }
    
    def _synthesize_blended_response(self, user_input: str, context_path: str, vector_results: List) -> Dict:
        """Synthesize response combining MongoDB structure with vector search."""
        # Get MongoDB content
        mongo_content = self.response_engine.get_mongodb_content(context_path)
        
        # Separate user documents from general knowledge
        user_doc_results = []
        general_results = []
        
        for result in vector_results:
            payload = result.get("payload", {})
            if payload.get("source") == "user_upload" or payload.get("type") == "user_document":
                user_doc_results.append(result)
            else:
                general_results.append(result)
        
        # Add patient information to user profile for better personalization
        try:
            from utils.patient_utils import parse_patient_documents
            patient_info = parse_patient_documents(self.user_profile.get("user_id", "default"))
            if patient_info:
                self.user_profile.update(patient_info)
        except Exception as e:
            print(f"⚠️ Could not update user profile with patient info: {e}")
        
        # Generate enhanced response using the existing API with vector results
        return self.response_engine.synthesize_response(
            user_query=user_input,
            context_path=context_path,
            user_profile=self.user_profile,
            conversation_history=self.conversation_history,
            vector_results=vector_results
        )
    
    def _synthesize_vector_response(self, user_input: str, context_path: str, vector_results: List) -> Dict:
        """Synthesize response using vector search with guided hints."""
        # Get guided hint from current context
        guided_hint = {"label": "Continue", "next_steps": []}
        if self.retrieval_router:
            try:
                guided_hint = self.retrieval_router.get_guided_hint(context_path)
            except Exception as e:
                print(f"⚠️ Could not get guided hint: {e}")
                guided_hint = {"label": "Continue", "next_steps": []}
        
        # Generate response using the existing API with vector results
        return self.response_engine.synthesize_response(
            user_query=user_input,
            context_path=context_path,
            user_profile=self.user_profile,
            conversation_history=self.conversation_history,
            vector_results=vector_results
        )

    def _format_user_document_results(self, user_doc_results: List) -> str:
        """Format user document results for LLM context."""
        if not user_doc_results:
            return "No patient-specific documents found."
        
        formatted = []
        for i, result in enumerate(user_doc_results[:3], 1):
            payload = result.get("payload", {})
            filename = payload.get("filename", "Unknown file")
            content = payload.get("content", "")[:300]
            formatted.append(f"{i}. {filename}: {content}...")
        
        return "\n".join(formatted)
    
    def _format_vector_results(self, vector_results: List) -> str:
        """Format vector search results for LLM context."""
        if not vector_results:
            return "No additional context found."
        
        formatted = []
        for i, result in enumerate(vector_results[:3], 1):
            payload = result.get("payload", {})
            formatted.append(f"{i}. {payload.get('label', 'Unknown')}: {payload.get('response', '')[:200]}...")
        
        return "\n".join(formatted)
    
    def _determine_next_context(self, user_input: str) -> str:
        """Intelligently determine the next context based on user input."""
        
        # Try to find direct path matches
        for path in self.available_paths:
            if path.lower() in user_input.lower():
                return path
        
        # Use knowledge adapter to find best match
        best_match = self.knowledge_adapter.get_node(self.current_context_path)
        if best_match and best_match.get("routes"):
            # Check routes for relevance
            for route in best_match["routes"]:
                if isinstance(route, dict) and route.get("keywords"):
                    for keyword in route["keywords"]:
                        if keyword.lower() in user_input.lower():
                            return route.get("next_path", self.current_context_path)
        
        # Fallback to current context
        return self.current_context_path
    
    def _get_available_paths(self, context_path: str) -> List[str]:
        """Get available conversation paths using knowledge adapter."""
        return self.knowledge_adapter.get_available_paths(context_path)
    
    def get_conversation_summary(self) -> Dict:
        """Generate a comprehensive conversation summary."""
        if not self.conversation_history:
            return {"summary": "No conversation history available."}
        
        # Extract key information
        user_responses = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]
        ai_responses = [msg["content"] for msg in self.conversation_history if msg["role"] == "assistant"]
        context_paths = [msg.get("context_path", "") for msg in self.conversation_history if msg.get("context_path")]
        
        # Generate summary using response engine
        summary_prompt = f"""
        Conversation Summary Request:
        
        User Profile: {self.user_profile}
        Topics Discussed: {list(set(context_paths))}
        User Questions: {user_responses}
        AI Responses: {ai_responses}
        
        Please provide a comprehensive summary of this conversation, including:
        1. Key topics discussed
        2. User's main concerns
        3. Information provided
        4. Recommended next steps
        """
        
        summary_response = self.response_engine.synthesize_response(
            user_query=summary_prompt,
            context_path=self.current_context_path or "conversation_summary",
            user_profile=self.user_profile,
            conversation_history=self.conversation_history,
            vector_results=[]
        )
        
        return {
            "summary": summary_response["response"],
            "topics_discussed": list(set(context_paths)),
            "conversation_length": len(self.conversation_history),
            "user_profile": self.user_profile,
            "final_context": self.current_context_path,
            "next_recommendations": summary_response["next_suggestions"]
        }
    
    def suggest_next_topics(self) -> List[Dict]:
        """Suggest relevant next topics based on conversation history."""
        if not self.current_context_path:
            return []
        
        # Get current context content using knowledge adapter
        content = self.knowledge_adapter.get_node(self.current_context_path)
        if not content:
            return []
        
        suggestions = []
        
        # Add route-based suggestions
        if content.get("routes"):
            for route in content["routes"]:
                if isinstance(route, dict):
                    suggestions.append({
                        "topic": route.get("label", "Explore this topic"),
                        "path": route.get("next_path", ""),
                        "description": route.get("description", ""),
                        "type": "route"
                    })
        
        # Add branch-based suggestions
        if content.get("branches"):
            for branch in content["branches"]:
                if isinstance(branch, dict):
                    suggestions.append({
                        "topic": branch.get("label", "Learn more"),
                        "path": branch.get("path", ""),
                        "description": branch.get("description", ""),
                        "type": "branch"
                    })
        
        # Add profile-based suggestions
        if self.user_profile.get("diagnosis_status") == "diagnosed_no":
            suggestions.append({
                "topic": "Get Screening Recommendations",
                "path": "diagnosed_no.screening_tools",
                "description": "Learn about autism screening tools and assessments",
                "type": "profile_based"
            })
        elif self.user_profile.get("diagnosis_status") == "diagnosed_yes":
            suggestions.append({
                "topic": "Find Support Resources",
                "path": "diagnosed_yes.support_resources",
                "description": "Discover local and online support resources",
                "type": "profile_based"
            })
        
        return suggestions[:8]  # Limit to 8 suggestions
    
    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        import uuid
        return str(uuid.uuid4())[:8]

    def _update_conversation_memory(self, user_input: str, response: Dict):
        """Update conversation memory with new information."""
        # Extract patient information
        if "child" in user_input.lower() or "son" in user_input.lower() or "daughter" in user_input.lower():
            # Extract age, name, diagnosis info
            import re
            age_match = re.search(r'(\d+)\s*(?:year|yr)s?\s*old', user_input.lower())
            if age_match:
                self.conversation_memory["patient_info"]["age"] = age_match.group(1)
            
            name_match = re.search(r'(?:my\s+(?:son|daughter|child)\s+)(\w+)', user_input.lower())
            if name_match:
                self.conversation_memory["patient_info"]["name"] = name_match.group(1).capitalize()
        
        # Track discussed topics
        if response.get("context_path"):
            self.conversation_memory["discussed_topics"].add(response["context_path"])
        
        # Track user concerns
        concern_keywords = ["worried", "concerned", "struggling", "difficulty", "problem"]
        if any(keyword in user_input.lower() for keyword in concern_keywords):
            self.conversation_memory["user_concerns"].append(user_input)
        
        # Track recommendations
        if response.get("next_suggestions"):
            self.conversation_memory["recommendations_given"].extend(response["next_suggestions"])
    
    def _get_conversation_context(self) -> str:
        """Get conversation context for LLM synthesis."""
        context_parts = []
        
        if self.conversation_memory["patient_info"]:
            patient_info = ", ".join([f"{k}: {v}" for k, v in self.conversation_memory["patient_info"].items()])
            context_parts.append(f"Patient Information: {patient_info}")
        
        if self.conversation_memory["discussed_topics"]:
            topics = ", ".join(list(self.conversation_memory["discussed_topics"])[:5])
            context_parts.append(f"Previously Discussed: {topics}")
        
        if self.conversation_memory["user_concerns"]:
            concerns = "; ".join(self.conversation_memory["user_concerns"][-3:])
            context_parts.append(f"User Concerns: {concerns}")
        
        return "\n".join(context_parts) if context_parts else "No previous context available."
    
    def _extract_and_remember_facts(self, user_input: str):
        """Extract and remember user-provided facts like age, diagnosis, etc."""
        input_lower = user_input.lower()
        
        # Extract age information
        import re
        age_patterns = [
            r'(?:he\'s|she\'s|child is|kid is|my child is)\s*(\d+)\s*(?:years?\s*old)?',
            r'(\d+)\s*(?:year|yr)s?\s*old',
            r'age\s*(?:is\s*)?(\d+)',
            r'(\d+)\s*(?:years?\s*)?(?:old|of\s*age)'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, input_lower)
            if match:
                age = int(match.group(1))
                # Map age to age band
                if age <= 3:
                    age_band = "0-3"
                elif age <= 5:
                    age_band = "3-5"
                elif age <= 12:
                    age_band = "6-12"
                elif age <= 17:
                    age_band = "13-17"
                else:
                    age_band = "18+"
                
                if self.user_profile.get("child_age") != age_band:
                    self.user_profile["child_age"] = age_band
                    self.user_profile["specific_age"] = age
                    print(f"✅ Remembered: Child age {age} (band: {age_band})")
                break
        
        # Extract diagnosis status
        if any(phrase in input_lower for phrase in ["diagnosed with autism", "has autism", "autism diagnosis", "confirmed autism"]):
            if self.user_profile.get("diagnosis_status") != "diagnosed_yes":
                self.user_profile["diagnosis_status"] = "diagnosed_yes"
                print("✅ Remembered: Child has autism diagnosis")
        
        elif any(phrase in input_lower for phrase in ["not diagnosed", "no diagnosis", "haven't been diagnosed", "waiting for diagnosis"]):
            if self.user_profile.get("diagnosis_status") != "diagnosed_no":
                self.user_profile["diagnosis_status"] = "diagnosed_no"
                print("✅ Remembered: Child not yet diagnosed")
        
        # Extract child name
        name_patterns = [
            r'(?:my\s+(?:son|daughter|child)\s+)(\w+)',
            r'(?:his|her)\s+name\s+is\s+(\w+)',
            r'(\w+)\s+(?:is\s+my\s+(?:son|daughter|child))',
            r'(?:called|named)\s+(\w+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, input_lower)
            if match:
                name = match.group(1).capitalize()
                if self.user_profile.get("child_name") != name:
                    self.user_profile["child_name"] = name
                    print(f"✅ Remembered: Child's name is {name}")
                break
        
        # Extract concerns
        concern_keywords = {
            "speech": ["speech", "talking", "speaking", "language", "words", "communication"],
            "social": ["social", "friends", "playing", "interaction", "eye contact"],
            "behavior": ["behavior", "meltdown", "tantrums", "repetitive", "stimming"],
            "development": ["development", "milestones", "delayed", "behind"]
        }
        
        for concern_type, keywords in concern_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                concerns = self.user_profile.get("concerns", [])
                if concern_type not in concerns:
                    concerns.append(concern_type)
                    self.user_profile["concerns"] = concerns
                    print(f"✅ Remembered: Concern about {concern_type}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def close(self):
        """Close all connections."""
        self.response_engine.close()
        self.context_engine.close()

    def _initialize_memory_manager(self):
        """Initialize the memory manager for the current user."""
        try:
            user_id = self.user_profile.get("user_id", "default")
            self.memory_manager = ConversationMemoryManager(user_id)
            print(f"✅ Memory manager initialized for user: {user_id}")
        except Exception as e:
            print(f"⚠️ Could not initialize memory manager: {e}")
            self.memory_manager = None
    
    def _store_conversation_memory(self, message: Dict):
        """Store a message in conversation memory if memory manager is available."""
        if self.memory_manager:
            try:
                self.memory_manager.store_chat_message(message)
            except Exception as e:
                print(f"⚠️ Error storing conversation memory: {e}")
    
    def _extract_and_store_insights(self):
        """Extract insights from current conversation and store them."""
        if self.memory_manager and len(self.conversation_history) > 10:
            try:
                insights = self.memory_manager.extract_and_store_insights(self.conversation_history)
                print(f"✅ Extracted and stored conversation insights")
                return insights
            except Exception as e:
                print(f"⚠️ Error extracting insights: {e}")
        return {}
    
    def _get_memory_context(self, query: str) -> Dict:
        """Get relevant context from conversation memory."""
        if self.memory_manager:
            try:
                return self.memory_manager.retrieve_relevant_context(query)
            except Exception as e:
                print(f"⚠️ Error retrieving memory context: {e}")
        return {}

# Example usage and testing
if __name__ == "__main__":
    manager = IntelligentConversationManager()
    
    # Test conversation flow
    test_profile = {
        "role": "parent_caregiver",
        "child_age": "3-5",
        "diagnosis_status": "diagnosed_no"
    }
    
    # Start conversation
    start_result = manager.start_conversation(test_profile)
    print("Conversation Started:")
    print(f"Response: {start_result['response'][:200]}...")
    print(f"Context: {start_result['context_path']}")
    print(f"Available Paths: {start_result['available_paths']}")
    
    # Process user response
    user_response = "I'm concerned about my child's speech development"
    response_result = manager.process_user_response(user_response)
    print(f"\nUser Response: {user_response}")
    print(f"AI Response: {response_result['response'][:200]}...")
    print(f"Next Context: {response_result['context_path']}")
    print(f"Mode: {response_result.get('mode', 'unknown')}")
    
    # Get suggestions
    suggestions = manager.suggest_next_topics()
    print(f"\nNext Topic Suggestions: {len(suggestions)} available")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"{i}. {suggestion['topic']} - {suggestion['description']}")
    
    manager.close()
