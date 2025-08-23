"""
Conversation Memory Manager for Autism Support App
Manages persistent storage and retrieval of conversation memory, insights, and user preferences.
"""

import json
import re
from typing import Dict, List, Optional, Set
from datetime import datetime
from rag.qdrant_client import store_conversation_memory, search_conversation_memory

class ConversationMemoryManager:
    """Manages conversation memory persistence and retrieval."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.collections = [
            "chat_history",
            "insights", 
            "prefs",
            "learning"
        ]
    
    def store_chat_message(self, message: Dict) -> bool:
        """Store a chat message in the chat history collection."""
        try:
            # Extract key information from message
            memory_data = {
                "role": message.get("role", "unknown"),
                "content": message.get("content", ""),
                "timestamp": message.get("timestamp", datetime.now().isoformat()),
                "conversation_type": message.get("conversation_type", "general"),
                "context_path": message.get("context_path", ""),
                "sources": message.get("sources", []),
                "next_suggestions": message.get("next_suggestions", [])
            }
            
            return store_conversation_memory(self.user_id, "chat_history", memory_data)
            
        except Exception as e:
            print(f"❌ Error storing chat message: {e}")
            return False
    
    def extract_and_store_insights(self, conversation: List[Dict]) -> Dict:
        """Extract insights from conversation and store them."""
        try:
            insights = {
                "topics_discussed": self._extract_topics(conversation),
                "user_concerns": self._extract_concerns(conversation),
                "successful_strategies": self._extract_strategies(conversation),
                "patient_progress": self._extract_progress(conversation),
                "user_preferences": self._extract_preferences(conversation),
                "extraction_timestamp": datetime.now().isoformat(),
                "conversation_count": len(conversation)
            }
            
            # Store insights
            store_conversation_memory(self.user_id, "insights", insights)
            
            # Store individual insights in their respective collections
            if insights["user_preferences"]:
                store_conversation_memory(self.user_id, "prefs", insights["user_preferences"])
            
            if insights["successful_strategies"]:
                store_conversation_memory(self.user_id, "learning", insights["successful_strategies"])
            
            print(f"✅ Extracted and stored insights: {len(insights['topics_discussed'])} topics, {len(insights['user_concerns'])} concerns")
            return insights
            
        except Exception as e:
            print(f"❌ Error extracting insights: {e}")
            return {}
    
    def _extract_topics(self, conversation: List[Dict]) -> List[str]:
        """Extract main topics discussed in conversation."""
        topics = set()
        
        # Common autism-related topics
        autism_topics = [
            "screening", "diagnosis", "therapy", "education", "behavior", 
            "communication", "social skills", "sensory issues", "medication",
            "IEP", "school", "family support", "resources", "treatment"
        ]
        
        for message in conversation:
            content = message.get("content", "").lower()
            for topic in autism_topics:
                if topic in content:
                    topics.add(topic)
        
        return list(topics)
    
    def _extract_concerns(self, conversation: List[Dict]) -> List[str]:
        """Extract user concerns and worries."""
        concerns = []
        
        # Look for concern indicators
        concern_indicators = [
            "worried", "concerned", "struggling", "difficult", "challenging",
            "problem", "issue", "trouble", "hard", "frustrated", "overwhelmed"
        ]
        
        for message in conversation:
            if message.get("role") == "user":
                content = message.get("content", "").lower()
                for indicator in concern_indicators:
                    if indicator in content:
                        # Extract the sentence containing the concern
                        sentences = re.split(r'[.!?]', content)
                        for sentence in sentences:
                            if indicator in sentence:
                                concerns.append(sentence.strip())
                                break
        
        return list(set(concerns))[:10]  # Limit to top 10 concerns
    
    def _extract_strategies(self, conversation: List[Dict]) -> List[str]:
        """Extract successful strategies and recommendations."""
        strategies = []
        
        # Look for strategy indicators
        strategy_indicators = [
            "worked", "helped", "effective", "successful", "improved",
            "better", "strategy", "technique", "approach", "method"
        ]
        
        for message in conversation:
            if message.get("role") == "assistant":
                content = message.get("content", "").lower()
                for indicator in strategy_indicators:
                    if indicator in content:
                        # Extract the sentence containing the strategy
                        sentences = re.split(r'[.!?]', content)
                        for sentence in sentences:
                            if indicator in sentence:
                                strategies.append(sentence.strip())
                                break
        
        return list(set(strategies))[:10]  # Limit to top 10 strategies
    
    def _extract_progress(self, conversation: List[Dict]) -> Dict:
        """Extract patient progress information."""
        progress = {
            "milestones": [],
            "improvements": [],
            "challenges": [],
            "goals": []
        }
        
        for message in conversation:
            content = message.get("content", "").lower()
            
            # Look for progress indicators
            if any(word in content for word in ["improved", "better", "progress", "milestone"]):
                progress["improvements"].append(content[:200])
            
            if any(word in content for word in ["goal", "target", "aim", "objective"]):
                progress["goals"].append(content[:200])
        
        return progress
    
    def _extract_preferences(self, conversation: List[Dict]) -> Dict:
        """Extract user preferences and learning patterns."""
        preferences = {
            "communication_style": [],
            "information_format": [],
            "topic_interests": [],
            "response_length": []
        }
        
        for message in conversation:
            if message.get("role") == "user":
                content = message.get("content", "").lower()
                
                # Communication style preferences
                if any(word in content for word in ["detailed", "simple", "step-by-step", "overview"]):
                    preferences["communication_style"].append(content[:100])
                
                # Information format preferences
                if any(word in content for word in ["list", "explanation", "example", "resource"]):
                    preferences["information_format"].append(content[:100])
        
        return preferences
    
    def retrieve_relevant_context(self, query: str, limit: int = 5) -> Dict:
        """Retrieve relevant context from all memory collections."""
        try:
            # Search all memory collections
            results = search_conversation_memory(self.user_id, query, limit=limit)
            
            # Organize results by type
            context = {
                "chat_history": [],
                "insights": [],
                "preferences": [],
                "learning": []
            }
            
            for result in results:
                memory_type = result.get("payload", {}).get("type", "unknown")
                if memory_type in context:
                    context[memory_type].append({
                        "content": result.get("payload", {}).get("content", ""),
                        "data": result.get("payload", {}).get("data", {}),
                        "score": result.get("score", 0),
                        "timestamp": result.get("payload", {}).get("timestamp", "")
                    })
            
            return context
            
        except Exception as e:
            print(f"❌ Error retrieving memory context: {e}")
            return {}
    
    def get_user_preferences(self) -> Dict:
        """Get stored user preferences."""
        try:
            results = search_conversation_memory(self.user_id, "user preferences", memory_type="prefs", limit=3)
            if results:
                return results[0].get("payload", {}).get("data", {})
            return {}
        except Exception as e:
            print(f"❌ Error getting user preferences: {e}")
            return {}
    
    def get_learning_patterns(self) -> List[str]:
        """Get stored learning patterns and successful strategies."""
        try:
            results = search_conversation_memory(self.user_id, "successful strategies", memory_type="learning", limit=5)
            strategies = []
            for result in results:
                data = result.get("payload", {}).get("data", {})
                if isinstance(data, list):
                    strategies.extend(data)
                elif isinstance(data, str):
                    strategies.append(data)
            return strategies[:10]
        except Exception as e:
            print(f"❌ Error getting learning patterns: {e}")
            return []
