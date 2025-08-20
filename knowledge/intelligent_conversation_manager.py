"""
Intelligent Conversation Manager for Autism Support App
Integrates Response Synthesis Engine with guided conversation flows for dynamic, intelligent conversations.
"""

import json
from typing import Dict, List, Optional, Tuple
from .response_synthesis_engine import ResponseSynthesisEngine
from .context_traversal_engine import ContextTraversalEngine

class IntelligentConversationManager:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        """Initialize the intelligent conversation manager."""
        self.response_engine = ResponseSynthesisEngine(mongo_uri)
        self.context_engine = ContextTraversalEngine(mongo_uri)
        
        # Conversation state
        self.current_context_path = None
        self.conversation_history = []
        self.user_profile = {}
        self.available_paths = []
        
    def start_conversation(self, user_profile: Dict) -> Dict:
        """Start a new intelligent conversation based on user profile."""
        self.user_profile = user_profile
        self.conversation_history = []
        
        # Determine initial context path
        initial_path = self.context_engine.determine_initial_context(user_profile)
        self.current_context_path = initial_path
        
        # Get initial response using synthesis engine
        initial_response = self.response_engine.synthesize_response(
            user_query="Start conversation",
            context_path=initial_path,
            user_profile=user_profile
        )
        
        # Get available conversation paths
        flow_info = self.response_engine.get_conversation_flow(initial_path)
        self.available_paths = self._get_available_paths(initial_path)
        
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
        
        # Add user input to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": self._get_timestamp()
        })
        
        # Determine next context path
        if selected_path:
            next_context = selected_path
        else:
            next_context = self._determine_next_context(user_input)
        
        # Update current context
        self.current_context_path = next_context
        
        # Generate synthesized response
        response = self.response_engine.synthesize_response(
            user_query=user_input,
            context_path=next_context,
            user_profile=self.user_profile,
            conversation_history=self.conversation_history
        )
        
        # Update available paths
        self.available_paths = self._get_available_paths(next_context)
        
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
            "confidence": response["confidence"],
            "sources": response["sources"]
        }
    
    def _determine_next_context(self, user_input: str) -> str:
        """Intelligently determine the next context based on user input."""
        
        # Try to find direct path matches
        for path in self.available_paths:
            if path.lower() in user_input.lower():
                return path
        
        # Use context engine to find best match
        best_match = self.context_engine.get_context_path_content(self.current_context_path)
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
        """Get available conversation paths from current context."""
        try:
            # Get MongoDB content for current context
            content = self.response_engine.get_mongodb_content(context_path)
            if not content:
                return []
            
            available_paths = []
            
            # Add routes
            if content.get("routes"):
                for route in content["routes"]:
                    if isinstance(route, str):
                        available_paths.append(route)
                    elif isinstance(route, dict):
                        available_paths.append(route.get("next_path", ""))
            
            # Add branches
            if content.get("branches"):
                for branch in content["branches"]:
                    if isinstance(branch, str):
                        available_paths.append(branch)
                    elif isinstance(branch, dict):
                        available_paths.append(branch.get("path", ""))
            
            # Filter out empty paths
            available_paths = [path for path in available_paths if path]
            
            return available_paths
            
        except Exception as e:
            print(f"❌ Error getting available paths: {e}")
            return []
    
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
        
        # Get current context content
        content = self.response_engine.get_mongodb_content(self.current_context_path)
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
    
    # Get suggestions
    suggestions = manager.suggest_next_topics()
    print(f"\nNext Topic Suggestions: {len(suggestions)} available")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"{i}. {suggestion['topic']} - {suggestion['description']}")
    
    manager.close()
