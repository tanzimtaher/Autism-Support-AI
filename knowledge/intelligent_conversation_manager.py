"""
Intelligent Conversation Manager for Autism Support App
Integrates Response Synthesis Engine with guided conversation flows for dynamic, intelligent conversations.
"""

import json
from typing import Dict, List, Optional, Tuple
from .response_synthesis_engine import ResponseSynthesisEngine
from .context_traversal_engine import ContextTraversalEngine

# Add new imports for dual-index system
from app.services.knowledge_adapter import KnowledgeAdapter
from retrieval.retrieval_router import RetrievalRouter

class IntelligentConversationManager:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        """Initialize the intelligent conversation manager."""
        self.response_engine = ResponseSynthesisEngine(mongo_uri)
        self.context_engine = ContextTraversalEngine(mongo_uri)
        
        # Add new dual-index components
        self.knowledge_adapter = KnowledgeAdapter()
        self.retrieval_router = RetrievalRouter(self.knowledge_adapter)
        
        # Conversation state
        self.current_context_path = None
        self.conversation_history = []
        self.user_profile = {}
        self.available_paths = []
        
        # Generate user ID if not exists
        if "user_id" not in self.user_profile:
            self.user_profile["user_id"] = "default"
        
    def start_conversation(self, user_profile: Dict) -> Dict:
        """Start a new intelligent conversation based on user profile."""
        self.user_profile.update(user_profile)
        self.conversation_history = []
        
        # Use knowledge adapter for initial context
        initial_path = self.knowledge_adapter.get_initial_context(self.user_profile)
        self.current_context_path = initial_path
        
        # Get initial response using synthesis engine
        initial_response = self.response_engine.synthesize_response(
            user_query="Start conversation",
            context_path=initial_path,
            user_profile=self.user_profile
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
        
        # Extract and remember user-provided facts
        self._extract_and_remember_facts(user_input)
        
        # Add user input to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": self._get_timestamp()
        })
        
        # Check for safety terms first
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
        mode, vector_results = self.retrieval_router.route(
            user_input, 
            self.user_profile, 
            next_context
        )
        
        # Generate response based on routing mode
        if mode == "mongo_only":
            # Use only structured MongoDB data
            response = self.response_engine.synthesize_response(
                user_query=user_input,
                context_path=next_context,
                user_profile=self.user_profile,
                conversation_history=self.conversation_history
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
        
        # Add response to history
        self.conversation_history.append({
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
    
    def _synthesize_blended_response(self, user_input: str, context_path: str, vector_results: List) -> Dict:
        """Synthesize response combining MongoDB structure with vector search."""
        # Get MongoDB content
        mongo_content = self.response_engine.get_mongodb_content(context_path)
        
        # Create enhanced context by modifying the user input to include vector results
        enhanced_input = f"""
        {user_input}
        
        Additional Context from Vector Search:
        {self._format_vector_results(vector_results)}
        """
        
        # Generate enhanced response using the existing API
        return self.response_engine.synthesize_response(
            user_query=enhanced_input,
            context_path=context_path,
            user_profile=self.user_profile,
            conversation_history=self.conversation_history
        )
    
    def _synthesize_vector_response(self, user_input: str, context_path: str, vector_results: List) -> Dict:
        """Synthesize response using vector search with guided hints."""
        # Get guided hint from current context
        guided_hint = self.retrieval_router.get_guided_hint(context_path)
        
        # Create enhanced input combining vector results with guided hint
        enhanced_input = f"""
        {user_input}
        
        Vector Search Results:
        {self._format_vector_results(vector_results)}
        
        Guided Hint: {guided_hint.get('label', 'Continue')}
        Next Steps: {', '.join(guided_hint.get('next_steps', []))}
        """
        
        # Generate response using the existing API
        return self.response_engine.synthesize_response(
            user_query=enhanced_input,
            context_path=context_path,
            user_profile=self.user_profile,
            conversation_history=self.conversation_history
        )
    
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
            conversation_history=self.conversation_history
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
