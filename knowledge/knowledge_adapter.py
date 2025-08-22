"""
Knowledge Adapter for Autism Support App
Provides structured conversation flows and intelligent topic routing.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class KnowledgeAdapter:
    def __init__(self):
        """Initialize the knowledge adapter with conversation structure."""
        self.conversation_tree = self._build_conversation_tree()
        self.user_progress = {}
        self.conversation_history = []
        
    def _build_conversation_tree(self) -> Dict:
        """Build the structured conversation tree for autism support."""
        return {
            "general": {
                "label": "General Autism Information",
                "description": "Learn about autism spectrum disorder basics",
                "content": "Autism spectrum disorder (ASD) is a developmental condition that affects communication, social interaction, and behavior. Early intervention can significantly improve outcomes.",
                "routes": [
                    {
                        "keywords": ["screening", "assessment", "evaluate", "check"],
                        "next_path": "screening",
                        "label": "Screening & Assessment",
                        "description": "Learn about autism screening tools and evaluation processes"
                    },
                    {
                        "keywords": ["diagnosis", "diagnosed", "evaluation", "confirmed"],
                        "next_path": "diagnosis",
                        "label": "Diagnosis Process",
                        "description": "Understanding the autism diagnosis process and what to expect"
                    },
                    {
                        "keywords": ["treatment", "therapy", "intervention", "help"],
                        "next_path": "treatment",
                        "label": "Treatment & Therapy",
                        "description": "Explore treatment options and therapeutic interventions"
                    },
                    {
                        "keywords": ["support", "resources", "help", "services"],
                        "next_path": "support",
                        "label": "Support & Resources",
                        "description": "Find support groups, resources, and community services"
                    }
                ],
                "branches": [
                    {
                        "path": "general.what_is_autism",
                        "label": "What is Autism?",
                        "description": "Basic information about autism spectrum disorder"
                    },
                    {
                        "path": "general.signs_symptoms",
                        "label": "Signs & Symptoms",
                        "description": "Common signs and symptoms of autism"
                    },
                    {
                        "path": "general.causes",
                        "label": "Causes & Risk Factors",
                        "description": "Understanding what causes autism"
                    }
                ]
            },
            "screening": {
                "label": "Screening & Assessment",
                "description": "Early detection and evaluation tools",
                "content": "Early screening is crucial for autism detection. Various tools and questionnaires can help identify potential concerns that warrant further evaluation.",
                "routes": [
                    {
                        "keywords": ["age", "young", "baby", "toddler", "preschool"],
                        "next_path": "screening.early_childhood",
                        "label": "Early Childhood (0-5)",
                        "description": "Screening tools for infants and young children"
                    },
                    {
                        "keywords": ["school", "older", "child", "teen"],
                        "next_path": "screening.school_age",
                        "label": "School Age (6-17)",
                        "description": "Assessment tools for school-aged children"
                    },
                    {
                        "keywords": ["adult", "grown", "older"],
                        "next_path": "screening.adult",
                        "label": "Adult Assessment",
                        "description": "Screening tools for adults"
                    }
                ],
                "branches": [
                    {
                        "path": "screening.mchat",
                        "label": "M-CHAT-R",
                        "description": "Modified Checklist for Autism in Toddlers"
                    },
                    {
                        "path": "screening.ados",
                        "label": "ADOS-2",
                        "description": "Autism Diagnostic Observation Schedule"
                    },
                    {
                        "path": "screening.adi_r",
                        "label": "ADI-R",
                        "description": "Autism Diagnostic Interview-Revised"
                    }
                ]
            },
            "diagnosis": {
                "label": "Diagnosis Process",
                "description": "Understanding the evaluation and diagnosis journey",
                "content": "The autism diagnosis process involves comprehensive evaluation by specialists. It typically includes developmental assessment, behavioral observation, and parent interviews.",
                "routes": [
                    {
                        "keywords": ["pediatrician", "doctor", "primary"],
                        "next_path": "diagnosis.pediatrician",
                        "label": "Pediatrician Visit",
                        "description": "What to expect at your first doctor visit"
                    },
                    {
                        "keywords": ["specialist", "psychologist", "neurologist"],
                        "next_path": "diagnosis.specialist",
                        "label": "Specialist Evaluation",
                        "description": "Working with autism specialists"
                    },
                    {
                        "keywords": ["evaluation", "testing", "assessment"],
                        "next_path": "diagnosis.evaluation",
                        "label": "Evaluation Process",
                        "description": "What happens during the evaluation"
                    }
                ],
                "branches": [
                    {
                        "path": "diagnosis.preparation",
                        "label": "Preparing for Evaluation",
                        "description": "How to prepare for your child's evaluation"
                    },
                    {
                        "path": "diagnosis.results",
                        "label": "Understanding Results",
                        "description": "What the diagnosis means and next steps"
                    }
                ]
            },
            "treatment": {
                "label": "Treatment & Therapy",
                "description": "Intervention options and therapeutic approaches",
                "content": "Early intervention is key to improving outcomes for children with autism. Treatment plans are individualized and may include various therapeutic approaches.",
                "routes": [
                    {
                        "keywords": ["early", "young", "baby", "toddler"],
                        "next_path": "treatment.early_intervention",
                        "label": "Early Intervention",
                        "description": "Services for children under 3 years old"
                    },
                    {
                        "keywords": ["speech", "language", "communication"],
                        "next_path": "treatment.speech_therapy",
                        "label": "Speech & Language Therapy",
                        "description": "Improving communication skills"
                    },
                    {
                        "keywords": ["occupational", "ot", "daily", "skills"],
                        "next_path": "treatment.occupational_therapy",
                        "label": "Occupational Therapy",
                        "description": "Developing daily living skills"
                    },
                    {
                        "keywords": ["behavioral", "aba", "applied"],
                        "next_path": "treatment.behavioral_therapy",
                        "label": "Behavioral Therapy",
                        "description": "Addressing challenging behaviors"
                    }
                ],
                "branches": [
                    {
                        "path": "treatment.individualized_plan",
                        "label": "Individualized Treatment Plan",
                        "description": "Creating a personalized treatment approach"
                    },
                    {
                        "path": "treatment.family_involvement",
                        "label": "Family Involvement",
                        "description": "How families can support treatment"
                    }
                ]
            },
            "support": {
                "label": "Support & Resources",
                "description": "Finding help and building support networks",
                "content": "Building a strong support network is essential for families affected by autism. Various resources and services are available to help navigate the journey.",
                "routes": [
                    {
                        "keywords": ["group", "community", "other", "families"],
                        "next_path": "support.groups",
                        "label": "Support Groups",
                        "description": "Connect with other families"
                    },
                    {
                        "keywords": ["school", "education", "iep", "special"],
                        "next_path": "support.education",
                        "label": "Educational Support",
                        "description": "School services and accommodations"
                    },
                    {
                        "keywords": ["financial", "insurance", "cost", "money"],
                        "next_path": "support.financial",
                        "label": "Financial Resources",
                        "description": "Insurance coverage and financial assistance"
                    },
                    {
                        "keywords": ["crisis", "emergency", "urgent", "help"],
                        "next_path": "support.crisis",
                        "label": "Crisis Support",
                        "description": "Emergency resources and crisis intervention"
                    }
                ],
                "branches": [
                    {
                        "path": "support.local_resources",
                        "label": "Local Resources",
                        "description": "Finding help in your community"
                    },
                    {
                        "path": "support.online_resources",
                        "label": "Online Resources",
                        "description": "Websites, apps, and digital tools"
                    }
                ]
            }
        }
    
    def get_initial_context(self, user_profile: Dict) -> str:
        """Get the appropriate starting context based on user profile."""
        diagnosis_status = user_profile.get("diagnosis_status", "")
        child_age = user_profile.get("child_age", "")
        role = user_profile.get("role", "")
        
        # Route based on diagnosis status
        if diagnosis_status == "diagnosed_no":
            if child_age in ["0-3", "3-5"]:
                return "screening.early_childhood"
            elif child_age in ["6-12", "13-17"]:
                return "screening.school_age"
            else:
                return "screening"
        elif diagnosis_status == "diagnosed_yes":
            if child_age in ["0-3", "3-5"]:
                return "treatment.early_intervention"
            else:
                return "treatment"
        
        # Route based on role
        if role == "adult_self":
            return "screening.adult"
        
        # Default fallback
        return "general"
    
    def get_available_paths(self, context_path: str) -> List[str]:
        """Get available conversation paths from current context."""
        if not context_path:
            return ["general", "screening", "diagnosis", "treatment", "support"]
        
        # Split path to navigate tree
        path_parts = context_path.split(".")
        current_node = self.conversation_tree
        
        # Navigate to current context
        for part in path_parts:
            if part in current_node:
                current_node = current_node[part]
            else:
                return ["general"]  # Fallback if path not found
        
        # Get available routes and branches
        available_paths = []
        
        # Add routes
        if "routes" in current_node:
            for route in current_node["routes"]:
                available_paths.append(route["next_path"])
        
        # Add branches
        if "branches" in current_node:
            for branch in current_node["branches"]:
                available_paths.append(branch["path"])
        
        # Add parent context for navigation
        if len(path_parts) > 1:
            available_paths.append(".".join(path_parts[:-1]))
        
        # Add main categories
        available_paths.extend(["general", "screening", "diagnosis", "treatment", "support"])
        
        return list(set(available_paths))  # Remove duplicates
    
    def get_node(self, context_path: str) -> Optional[Dict]:
        """Get the content and structure of a specific context node."""
        if not context_path:
            return None
        
        path_parts = context_path.split(".")
        current_node = self.conversation_tree
        
        # Navigate to requested context
        for part in path_parts:
            if part in current_node:
                current_node = current_node[part]
            else:
                # If path not found, return the closest parent node
                return self._get_closest_parent_node(path_parts)
        
        return current_node
    
    def _get_closest_parent_node(self, path_parts: List[str]) -> Optional[Dict]:
        """Get the closest available parent node when exact path not found."""
        current_node = self.conversation_tree
        
        # Try to find the longest valid path
        for i in range(len(path_parts) - 1, -1, -1):
            partial_path = ".".join(path_parts[:i+1])
            test_node = self._get_node_by_path(partial_path)
            if test_node:
                return test_node
        
        # Fallback to general
        return self.conversation_tree.get("general")
    
    def _get_node_by_path(self, path: str) -> Optional[Dict]:
        """Get node by exact path."""
        if not path:
            return None
        
        path_parts = path.split(".")
        current_node = self.conversation_tree
        
        for part in path_parts:
            if part in current_node:
                current_node = current_node[part]
            else:
                return None
        
        return current_node
    
    def suggest_next_topics(self, context_path: str, user_profile: Dict) -> List[Dict]:
        """Suggest relevant next topics based on current context and user profile."""
        current_node = self.get_node(context_path)
        if not current_node:
            return []
        
        suggestions = []
        
        # Add route-based suggestions
        if "routes" in current_node:
            for route in current_node["routes"]:
                suggestions.append({
                    "topic": route["label"],
                    "path": route["next_path"],
                    "description": route["description"],
                    "type": "route",
                    "relevance": self._calculate_relevance(route, user_profile)
                })
        
        # Add branch-based suggestions
        if "branches" in current_node:
            for branch in current_node["branches"]:
                suggestions.append({
                    "topic": branch["label"],
                    "path": branch["path"],
                    "description": branch["description"],
                    "type": "branch",
                    "relevance": 0.8  # Default relevance for branches
                })
        
        # Add profile-based suggestions
        profile_suggestions = self._get_profile_based_suggestions(user_profile)
        suggestions.extend(profile_suggestions)
        
        # Sort by relevance and return top suggestions
        suggestions.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return suggestions[:6]  # Limit to 6 suggestions
    
    def _calculate_relevance(self, route: Dict, user_profile: Dict) -> float:
        """Calculate relevance score for a route based on user profile."""
        relevance = 0.5  # Base relevance
        
        # Boost relevance based on user profile matches
        if user_profile.get("diagnosis_status") == "diagnosed_no" and "screening" in route["next_path"]:
            relevance += 0.3
        elif user_profile.get("diagnosis_status") == "diagnosed_yes" and "treatment" in route["next_path"]:
            relevance += 0.3
        
        if user_profile.get("child_age") in ["0-3", "3-5"] and "early" in route["next_path"]:
            relevance += 0.2
        
        return min(relevance, 1.0)  # Cap at 1.0
    
    def _get_profile_based_suggestions(self, user_profile: Dict) -> List[Dict]:
        """Get suggestions based on user profile characteristics."""
        suggestions = []
        
        if user_profile.get("diagnosis_status") == "diagnosed_no":
            suggestions.append({
                "topic": "Get Screening Recommendations",
                "path": "screening",
                "description": "Learn about autism screening tools and assessments",
                "type": "profile_based",
                "relevance": 0.9
            })
        elif user_profile.get("diagnosis_status") == "diagnosed_yes":
            suggestions.append({
                "topic": "Find Treatment Options",
                "path": "treatment",
                "description": "Explore treatment and therapy options",
                "type": "profile_based",
                "relevance": 0.9
            })
        
        if user_profile.get("child_age") in ["0-3", "3-5"]:
            suggestions.append({
                "topic": "Early Intervention Services",
                "path": "treatment.early_intervention",
                "description": "Learn about early intervention programs",
                "type": "profile_based",
                "relevance": 0.8
            })
        
        return suggestions
    
    def get_conversation_summary(self, context_path: str, user_profile: Dict) -> Dict:
        """Generate a summary of the current conversation context."""
        current_node = self.get_node(context_path)
        if not current_node:
            return {"summary": "No context information available."}
        
        summary = {
            "current_topic": current_node.get("label", "Unknown Topic"),
            "description": current_node.get("description", ""),
            "content": current_node.get("content", ""),
            "available_paths": self.get_available_paths(context_path),
            "next_suggestions": self.suggest_next_topics(context_path, user_profile),
            "user_context": f"Role: {user_profile.get('role', 'Unknown')}, Child Age: {user_profile.get('child_age', 'Unknown')}, Diagnosis: {user_profile.get('diagnosis_status', 'Unknown')}"
        }
        
        return summary
    
    def update_user_progress(self, user_id: str, context_path: str, user_input: str):
        """Track user progress through conversation paths."""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "visited_paths": [],
                "last_activity": datetime.now().isoformat(),
                "conversation_flow": []
            }
        
        # Record visited path
        if context_path not in self.user_progress[user_id]["visited_paths"]:
            self.user_progress[user_id]["visited_paths"].append(context_path)
        
        # Update last activity
        self.user_progress[user_id]["last_activity"] = datetime.now().isoformat()
        
        # Record conversation flow
        self.user_progress[user_id]["conversation_flow"].append({
            "timestamp": datetime.now().isoformat(),
            "path": context_path,
            "user_input": user_input[:100]  # Truncate long inputs
        })
    
    def get_user_progress(self, user_id: str) -> Dict:
        """Get user's conversation progress and history."""
        return self.user_progress.get(user_id, {
            "visited_paths": [],
            "last_activity": None,
            "conversation_flow": []
        })
    
    def reset_user_progress(self, user_id: str):
        """Reset user's conversation progress."""
        if user_id in self.user_progress:
            del self.user_progress[user_id]
    
    def export_conversation_tree(self) -> str:
        """Export the conversation tree structure as JSON."""
        return json.dumps(self.conversation_tree, indent=2)
    
    def import_conversation_tree(self, tree_data: str):
        """Import a conversation tree structure from JSON."""
        try:
            self.conversation_tree = json.loads(tree_data)
            return True
        except json.JSONDecodeError:
            return False

# Example usage and testing
if __name__ == "__main__":
    adapter = KnowledgeAdapter()
    
    # Test initial context routing
    test_profile = {
        "role": "parent_caregiver",
        "child_age": "3-5",
        "diagnosis_status": "diagnosed_no"
    }
    
    initial_context = adapter.get_initial_context(test_profile)
    print(f"Initial context for profile: {initial_context}")
    
    # Test available paths
    available_paths = adapter.get_available_paths(initial_context)
    print(f"Available paths: {available_paths}")
    
    # Test suggestions
    suggestions = adapter.suggest_next_topics(initial_context, test_profile)
    print(f"Next topic suggestions: {len(suggestions)} available")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"{i}. {suggestion['topic']} - {suggestion['description']}")
    
    # Test conversation summary
    summary = adapter.get_conversation_summary(initial_context, test_profile)
    print(f"\nConversation summary: {summary['current_topic']}")
    print(f"Description: {summary['description']}")
