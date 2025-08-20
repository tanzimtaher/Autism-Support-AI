"""
Conversation Router for Autism Support App
Handles routing logic and context management for conversational guidance.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class ConversationRouter:
    def __init__(self, knowledge_base_path: str = "knowledge/structured_mongo.json"):
        """Initialize the conversation router."""
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
        self.router_config = self.knowledge_base.get("router", {})
    
    def _load_knowledge_base(self, path: str) -> Dict:
        """Load the knowledge base from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return {}
    
    def determine_user_path(self, user_profile: Dict) -> Dict:
        """
        Determine the appropriate path for a user based on their profile.
        
        Args:
            user_profile: Dictionary containing role, diagnosis_status, child_age
            
        Returns:
            Dictionary with routing information and available paths
        """
        role = user_profile.get("role", "parent_caregiver")
        status = user_profile.get("diagnosis_status", "diagnosed_no")
        age = user_profile.get("child_age", "0-3")
        
        # Get available paths for this user profile
        available_paths = self._get_available_paths(role, status, age)
        
        # Get entry point
        entry_point = self._get_entry_point(role, status)
        
        # Get next steps
        next_steps = self._get_next_steps(role, status, age)
        
        return {
            "role": role,
            "status": status,
            "age": age,
            "available_paths": available_paths,
            "entry_point": entry_point,
            "next_steps": next_steps
        }
    
    def _get_available_paths(self, role: str, status: str, age: str) -> List[str]:
        """Get available paths for the user profile."""
        available_paths = []
        
        if role == "parent_caregiver":
            if status == "diagnosed_no":
                # For undiagnosed children, focus on screening and evaluation
                if age in ["0-3", "3-5"]:
                    available_paths.extend([
                        "diagnosed_no.entry_point",
                        "diagnosed_no.monitor_vs_screen",
                        "diagnosed_no.screening_options",
                        "diagnosed_no.at_home_resources"
                    ])
                else:
                    available_paths.extend([
                        "diagnosed_no.entry_point",
                        "diagnosed_no.not_yet_evaluated",
                        "diagnosed_no.at_home_resources"
                    ])
            else:  # diagnosed_yes
                available_paths.extend([
                    "diagnosed_yes.support_affording",
                    "diagnosed_yes.find_resources",
                    "diagnosed_yes.legal_and_emergency"
                ])
        else:  # adult_self
            if status == "diagnosed_no":
                available_paths.extend([
                    "adult_self.diagnosed_no.education",
                    "adult_self.diagnosed_no.eval_where",
                    "adult_self.diagnosed_no.workplace_rights"
                ])
            else:  # diagnosed_yes
                available_paths.extend([
                    "adult_self.diagnosed_yes.care_navigation",
                    "adult_self.diagnosed_yes.workplace_accommodations",
                    "adult_self.diagnosed_yes.legal_financial_full"
                ])
        
        return available_paths
    
    def _get_entry_point(self, role: str, status: str) -> Dict:
        """Get the entry point for the user profile."""
        if role == "parent_caregiver":
            if status == "diagnosed_no":
                return self.knowledge_base.get("diagnosed_no", {}).get("entry_point", {})
            else:
                return self.knowledge_base.get("diagnosed_yes", {}).get("support_affording", {})
        else:  # adult_self
            if status == "diagnosed_no":
                return self.knowledge_base.get("adult_self", {}).get("diagnosed_no", {}).get("education", {})
            else:
                return self.knowledge_base.get("adult_self", {}).get("diagnosed_yes", {}).get("care_navigation", {})
    
    def _get_next_steps(self, role: str, status: str, age: str) -> List[Dict]:
        """Get suggested next steps for the user profile."""
        next_steps = []
        
        if role == "parent_caregiver":
            if status == "diagnosed_no":
                if age in ["0-3", "3-5"]:
                    next_steps = [
                        {"description": "Complete age-appropriate screening tools", "path": "screening_options"},
                        {"description": "Learn about developmental milestones", "path": "at_home_resources"},
                        {"description": "Understand monitoring vs. screening", "path": "monitor_vs_screen"}
                    ]
                else:
                    next_steps = [
                        {"description": "Find evaluation options", "path": "not_yet_evaluated"},
                        {"description": "Learn about school-based services", "path": "at_home_resources"},
                        {"description": "Prepare for evaluation", "path": "not_yet_evaluated"}
                    ]
            else:  # diagnosed_yes
                next_steps = [
                    {"description": "Explore financial support options", "path": "support_affording"},
                    {"description": "Find therapy and intervention services", "path": "find_resources"},
                    {"description": "Learn about school support", "path": "find_resources.school"}
                ]
        else:  # adult_self
            if status == "diagnosed_no":
                next_steps = [
                    {"description": "Learn about adult autism characteristics", "path": "education"},
                    {"description": "Find evaluation options", "path": "eval_where"},
                    {"description": "Understand workplace rights", "path": "workplace_rights"}
                ]
            else:  # diagnosed_yes
                next_steps = [
                    {"description": "Navigate care and support services", "path": "care_navigation"},
                    {"description": "Request workplace accommodations", "path": "workplace_accommodations"},
                    {"description": "Plan for legal and financial future", "path": "legal_financial_full"}
                ]
        
        return next_steps
    
    def check_safety_flags(self, user_input: str) -> Optional[Dict]:
        """
        Check user input for safety concerns.
        
        Args:
            user_input: Text input from user
            
        Returns:
            Safety action dictionary if safety concern detected, None otherwise
        """
        safety_rules = self.router_config.get("safety_rules", {})
        critical_terms = safety_rules.get("critical_terms", [])
        
        user_input_lower = user_input.lower()
        
        for term in critical_terms:
            if term.lower() in user_input_lower:
                return {
                    "term": term,
                    "action": safety_rules.get("action", "Contact healthcare provider immediately"),
                    "severity": "high"
                }
        
        return None
    
    def get_context_path(self, routing_info: Dict) -> str:
        """Get the context path for the routing information."""
        role = routing_info.get("role", "parent_caregiver")
        status = routing_info.get("status", "diagnosed_no")
        
        if role == "parent_caregiver":
            if status == "diagnosed_no":
                return "diagnosed_no.entry_point"
            else:
                return "diagnosed_yes.support_affording"
        else:  # adult_self
            if status == "diagnosed_no":
                return "adult_self.diagnosed_no.education"
            else:
                return "adult_self.diagnosed_yes.care_navigation"
    
    def get_knowledge_entry(self, context_path: str) -> Optional[Dict]:
        """
        Get a knowledge entry by context path.
        
        Args:
            context_path: Dot-separated path to the knowledge entry
            
        Returns:
            Knowledge entry dictionary or None if not found
        """
        if not context_path:
            return None
        
        try:
            # Navigate through the nested structure
            current = self.knowledge_base
            path_parts = context_path.split(".")
            
            for part in path_parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            # Check if this is a content node
            if isinstance(current, dict) and "response" in current:
                return current
            
            return None
            
        except Exception as e:
            print(f"Error getting knowledge entry for {context_path}: {e}")
            return None
    
    def get_conversation_suggestions(self, context_path: str) -> List[str]:
        """
        Get conversation suggestions based on context path.
        
        Args:
            context_path: Current context path
            
        Returns:
            List of suggested questions or topics
        """
        if not context_path:
            return ["What would you like to know about autism support?"]
        
        try:
            # Get the knowledge entry for this context
            entry = self.get_knowledge_entry(context_path)
            if not entry:
                return self._get_default_suggestions(context_path)
            
            natural_questions = []
            
            # Check if there are specific routes or options and convert them to natural questions
            if "routes" in entry:
                routes = entry["routes"]
                if isinstance(routes, dict):
                    for route_key, route_value in routes.items():
                        if isinstance(route_value, dict) and "label" in route_value:
                            label = route_value["label"].lower()
                            if "reassure" in label:
                                natural_questions.append("What if the screening results look normal?")
                            elif "borderline" in label:
                                natural_questions.append("What if the results are unclear?")
                            elif "concern" in label or "high risk" in label:
                                natural_questions.append("What if the screening shows concerns?")
                            else:
                                natural_questions.append(f"What does '{route_value['label']}' mean?")
            
            # Check if there are branches
            if "branches" in entry:
                branches = entry["branches"]
                if isinstance(branches, dict):
                    for branch_key, branch_value in branches.items():
                        if isinstance(branch_value, dict) and "label" in branch_value:
                            label = branch_value["label"].lower()
                            if "communication" in label:
                                natural_questions.append("What if I'm only worried about speech delays?")
                            elif "social" in label or "behavior" in label:
                                natural_questions.append("What if I'm concerned about social skills?")
                            else:
                                natural_questions.append(f"Tell me more about {branch_value['label'].lower()}")
            
            # Check if there are options
            if "options" in entry:
                options = entry["options"]
                if isinstance(options, dict):
                    for option_key, option_value in options.items():
                        if isinstance(option_value, dict) and "label" in option_value:
                            label = option_value["label"].lower()
                            if "csbs" in label:
                                natural_questions.append("How do I use the CSBS screening tool?")
                            elif "milestone" in label:
                                natural_questions.append("What developmental milestones should I watch for?")
                            elif "navigator" in label:
                                natural_questions.append("What is Autism Navigator and how can it help?")
                            else:
                                natural_questions.append(f"Tell me more about {option_value['label'].lower()}")
            
            # Remove duplicates and return unique questions
            if natural_questions:
                unique_questions = list(dict.fromkeys(natural_questions))  # Preserves order while removing duplicates
                return unique_questions[:3]  # Limit to 3 suggestions
            
            # Return default suggestions based on context
            return self._get_default_suggestions(context_path)
            
        except Exception as e:
            print(f"Error getting conversation suggestions for {context_path}: {e}")
            return ["What would you like to know more about?"]
    
    def _get_default_suggestions(self, context_path: str) -> List[str]:
        """Get default suggestions based on context path."""
        if "screening" in context_path:
            return [
                "Which screening tool would you like to learn about?",
                "What age is your child?",
                "What specific concerns do you have?"
            ]
        elif "evaluation" in context_path:
            return [
                "Where would you like to get an evaluation?",
                "What insurance do you have?",
                "What should you expect during evaluation?"
            ]
        elif "support" in context_path or "affording" in context_path:
            return [
                "Do you have Medicaid?",
                "What type of insurance do you have?",
                "Are you looking for sliding-scale options?"
            ]
        elif "school" in context_path:
            return [
                "Is your child in public or private school?",
                "Do you need help with IEP or 504 plans?",
                "What specific school challenges are you facing?"
            ]
        elif "intervention" in context_path or "therapy" in context_path:
            return [
                "What type of therapy are you looking for?",
                "Do you prefer clinic, home, or school-based services?",
                "What are your main goals for therapy?"
            ]
        else:
            return [
                "What would you like to know more about?",
                "How can I help you today?",
                "What's your main concern right now?"
            ]
    
    def get_available_options(self, context_path: str) -> List[Dict]:
        """
        Get available options for a given context path.
        
        Args:
            context_path: Current context path
            
        Returns:
            List of available options with labels and descriptions
        """
        entry = self.get_knowledge_entry(context_path)
        if not entry:
            return []
        
        options = []
        
        # Check for routes
        if "routes" in entry:
            routes = entry["routes"]
            if isinstance(routes, dict):
                for key, value in routes.items():
                    if isinstance(value, dict) and "label" in value:
                        options.append({
                            "key": key,
                            "label": value["label"],
                            "description": value.get("response", ""),
                            "type": "route"
                        })
        
        # Check for branches
        if "branches" in entry:
            branches = entry["branches"]
            if isinstance(branches, dict):
                for key, value in branches.items():
                    if isinstance(value, dict) and "label" in value:
                        options.append({
                            "key": key,
                            "label": value["label"],
                            "description": value.get("response", ""),
                            "type": "branch"
                        })
        
        # Check for options
        if "options" in entry:
            opts = entry["options"]
            if isinstance(opts, dict):
                for key, value in opts.items():
                    if isinstance(value, dict) and "label" in value:
                        options.append({
                            "key": key,
                            "label": value["label"],
                            "description": value.get("response", ""),
                            "type": "option"
                        })
        
        return options

# Example usage and testing
if __name__ == "__main__":
    router = ConversationRouter()
    
    # Test user profile routing
    test_profile = {
        "role": "parent_caregiver",
        "diagnosis_status": "diagnosed_no",
        "child_age": "0-3"
    }
    
    result = router.determine_user_path(test_profile)
    print("Routing result:", json.dumps(result, indent=2))
    
    # Test safety flag checking
    test_input = "My child has lost some skills and is having seizures"
    safety_check = router.check_safety_flags(test_input)
    if safety_check:
        print("SAFETY ALERT:", safety_check)
    
    # Test knowledge entry retrieval
    entry = router.get_knowledge_entry("diagnosed_no.entry_point")
    print("Knowledge entry:", entry.get("response") if entry else "Not found")
