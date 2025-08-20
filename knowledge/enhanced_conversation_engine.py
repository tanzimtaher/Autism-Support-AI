"""
Enhanced Conversation Engine for Autism Support App
Manages conversation flow and provides intelligent routing based on user context.
"""

import json
from typing import Dict, List, Optional
from .conversation_router import ConversationRouter


class EnhancedConversationEngine:
    def __init__(self, knowledge_base_path: str = "knowledge/structured_mongo.json"):
        """Initialize the conversation engine."""
        self.router = ConversationRouter(knowledge_base_path)
        self.conversation_flows = self._load_conversation_flows()
    
    def _load_conversation_flows(self) -> Dict:
        """Load conversation flow definitions."""
        try:
            with open("knowledge/structured_mongo.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversation flows: {e}")
            return {}
    
    def start_conversation(self, user_profile: Dict) -> Dict:
        """
        Initialize conversation based on user profile.
        
        Args:
            user_profile: User profile dictionary
            
        Returns:
            Conversation initialization response
        """
        # Get routing information
        routing_info = self.router.determine_user_path(user_profile)
        
        # Get entry point
        entry_point = routing_info.get("entry_point", {})
        
        # Get next steps
        next_steps = routing_info.get("next_steps", [])
        
        # Create initial conversation state
        conversation_state = {
            "role": user_profile["role"],
            "diagnosis_status": user_profile["diagnosis_status"],
            "child_age": user_profile.get("child_age", "18+"),
            "primary_concern": user_profile.get("primary_concern", "general"),
            "current_step": "entry",
            "completed_steps": [],
            "context_path": self._get_initial_context_path(user_profile),
            "conversation_history": [],
            "user_preferences": {},
            "current_topic": None
        }
        
        return {
            "message": entry_point.get("response", "How can I help you today?"),
            "tone": entry_point.get("tone", "supportive"),
            "routing_info": routing_info,
            "next_steps": next_steps,
            "conversation_state": conversation_state
        }
    
    def _get_initial_context_path(self, user_profile: Dict) -> str:
        """Get the initial context path based on user profile."""
        role = user_profile["role"]
        status = user_profile["diagnosis_status"]
        
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
    
    def process_user_response(self, user_input: str, conversation_state: Dict) -> Dict:
        """
        Process user input and determine next step.
        
        Args:
            user_input: Text input from user
            conversation_state: Current conversation state
            
        Returns:
            Response and next step information
        """
        # Check safety flags first
        safety_action = self.router.check_safety_flags(user_input)
        if safety_action:
            return self._handle_safety_concern(safety_action, conversation_state)
        
        # Add user input to conversation history
        conversation_state["conversation_history"].append({
            "role": "user",
            "content": user_input,
            "step": conversation_state.get("current_step", "unknown")
        })
        
        # Determine next step based on current context and user input
        next_step, context_path = self._determine_next_step(user_input, conversation_state)
        
        # Get response for next step
        response = self._get_step_response(next_step, context_path, conversation_state)
        
        # Update conversation state
        conversation_state["completed_steps"].append(conversation_state.get("current_step", "unknown"))
        conversation_state["current_step"] = next_step
        conversation_state["context_path"] = context_path
        conversation_state["current_topic"] = self._extract_topic_from_context(context_path)
        
        # Add assistant response to conversation history
        conversation_state["conversation_history"].append({
            "role": "assistant",
            "content": response.get("message", "I'm here to help. What would you like to know?"),
            "step": next_step
        })
        
        return {
            "response": response.get("message", "I'm here to help. What would you like to know?"),
            "tone": response.get("tone", "supportive"),
            "next_step": next_step,
            "conversation_state": conversation_state,
            "suggestions": self._get_contextual_suggestions(context_path, conversation_state),
            "safety_alert": None
        }
    
    def _handle_safety_concern(self, safety_action: Dict, conversation_state: Dict) -> Dict:
        """Handle safety concerns with appropriate response."""
        return {
            "response": f"🚨 **SAFETY ALERT** 🚨\n\n{safety_action['action']}\n\nPlease contact a healthcare provider immediately.",
            "tone": "urgent",
            "next_step": "safety_intervention",
            "conversation_state": conversation_state,
            "suggestions": ["Contact healthcare provider immediately"],
            "safety_alert": safety_action
        }
    
    def _determine_next_step(self, user_input: str, conversation_state: Dict) -> tuple:
        """Determine the next step and context path based on user input and current context."""
        current_context = conversation_state.get("context_path", "")
        role = conversation_state.get("role", "parent_caregiver")
        status = conversation_state.get("diagnosis_status", "diagnosed_no")
        age = conversation_state.get("child_age", "0-3")
        primary_concern = conversation_state.get("primary_concern", "general")
        
        user_input_lower = user_input.lower()
        
        # Handle specific user queries with intelligent routing
        if self._is_asking_about_screening(user_input_lower):
            if status == "diagnosed_no":
                if age in ["0-3", "3-5"]:
                    return "screening_options", "diagnosed_no.screening_options"
                else:
                    return "evaluation_info", "diagnosed_no.not_yet_evaluated.where_to_eval"
            else:
                return "find_resources", "diagnosed_yes.find_resources.interventions"
        
        elif self._is_asking_about_concerns(user_input_lower):
            if status == "diagnosed_no":
                if primary_concern == "communication":
                    return "communication_concerns", "diagnosed_no.no_dx_but_concerns.communication_only"
                elif primary_concern == "social_behavior":
                    return "social_behavior_concerns", "diagnosed_no.no_dx_but_concerns.social_behavior_concerns"
                else:
                    return "monitor_vs_screen", "diagnosed_no.monitor_vs_screen"
            else:
                return "find_resources", "diagnosed_yes.find_resources.interventions"
        
        elif self._is_asking_about_evaluation(user_input_lower):
            if status == "diagnosed_no":
                return "evaluation_info", "diagnosed_no.not_yet_evaluated.where_to_eval"
            else:
                return "find_resources", "diagnosed_yes.find_resources.interventions"
        
        elif self._is_asking_about_resources(user_input_lower):
            if status == "diagnosed_yes":
                return "support_affording", "diagnosed_yes.support_affording"
            else:
                return "at_home_resources", "diagnosed_no.at_home_resources"
        
        elif self._is_asking_about_school(user_input_lower):
            if status == "diagnosed_yes":
                return "school", "diagnosed_yes.find_resources.school"
            else:
                return "evaluation_info", "diagnosed_no.not_yet_evaluated.where_to_eval"
        
        # If no specific query detected, provide contextual next steps
        return self._get_contextual_next_step(current_context, conversation_state)
    
    def _is_asking_about_screening(self, user_input: str) -> bool:
        """Check if user is asking about screening."""
        screening_keywords = ["screen", "test", "check", "assessment", "evaluation", "milestone"]
        return any(keyword in user_input for keyword in screening_keywords)
    
    def _is_asking_about_concerns(self, user_input: str) -> bool:
        """Check if user is asking about concerns."""
        concern_keywords = ["concern", "worried", "worry", "problem", "issue", "sign", "symptom"]
        return any(keyword in user_input for keyword in concern_keywords)
    
    def _is_asking_about_evaluation(self, user_input: str) -> bool:
        """Check if user is asking about evaluation."""
        eval_keywords = ["evaluate", "diagnose", "doctor", "pediatrician", "specialist", "referral"]
        return any(keyword in user_input for keyword in eval_keywords)
    
    def _is_asking_about_resources(self, user_input: str) -> bool:
        """Check if user is asking about resources."""
        resource_keywords = ["help", "resource", "support", "therapy", "treatment", "service"]
        return any(keyword in user_input for keyword in resource_keywords)
    
    def _is_asking_about_school(self, user_input: str) -> bool:
        """Check if user is asking about school."""
        school_keywords = ["school", "preschool", "daycare", "education", "iep", "504", "classroom"]
        return any(keyword in user_input for keyword in school_keywords)
    
    def _get_contextual_next_step(self, current_context: str, conversation_state: Dict) -> tuple:
        """Get the next step based on current context."""
        role = conversation_state.get("role", "parent_caregiver")
        status = conversation_state.get("diagnosis_status", "diagnosed_no")
        age = conversation_state.get("child_age", "0-3")
        
        if "entry_point" in current_context:
            if status == "diagnosed_no":
                if age in ["0-3", "3-5"]:
                    return "screening_options", "diagnosed_no.screening_options"
                else:
                    return "evaluation_info", "diagnosed_no.not_yet_evaluated.where_to_eval"
            else:
                return "support_affording", "diagnosed_yes.support_affording"
        
        elif "screening_options" in current_context:
            return "interpretation_routes", "diagnosed_no.interpretation_routes"
        
        elif "monitor_vs_screen" in current_context:
            return "screening_options", "diagnosed_no.screening_options"
        
        # Default fallback
        if role == "parent_caregiver" and status == "diagnosed_no":
            return "at_home_resources", "diagnosed_no.at_home_resources"
        elif role == "parent_caregiver" and status == "diagnosed_yes":
            return "find_resources", "diagnosed_yes.find_resources.interventions"
        else:
            return "globals", "globals.info_hub.intro_to_autism"
    
    def _get_step_response(self, step: str, context_path: str, conversation_state: Dict) -> Dict:
        """Get the response for a specific step."""
        try:
            # Try to get response from the router
            knowledge_entry = self.router.get_knowledge_entry(context_path)
            if knowledge_entry:
                # Make the response more conversational
                response_text = knowledge_entry.get("response", "")
                if response_text:
                    # Add conversational elements
                    if "screening" in step.lower():
                        response_text = f"Great question! {response_text} Let me walk you through this step by step."
                    elif "evaluation" in step.lower():
                        response_text = f"I understand this can feel overwhelming. {response_text} Here's what you need to know:"
                    elif "support" in step.lower() or "affording" in step.lower():
                        response_text = f"I know this is a big concern for many families. {response_text} Let me help you explore your options:"
                    elif "school" in step.lower():
                        response_text = f"School services can make a huge difference. {response_text} Here's how to get started:"
                    else:
                        response_text = f"Let me help you with that. {response_text}"
                
                return {
                    "message": response_text,
                    "tone": knowledge_entry.get("tone", "supportive")
                }
            
            # Fallback to step-based responses with more natural language
            step_responses = {
                "screening_options": {
                    "message": "I'd be happy to help you find the right screening tools for your child's age. What specific concerns do you have about your child's development? We can work through this together.",
                    "tone": "informative"
                },
                "evaluation_info": {
                    "message": "I can definitely help you understand the evaluation process and find qualified professionals in your area. This is an important step, so let's make sure you have all the information you need. What would you like to know first?",
                    "tone": "supportive"
                },
                "at_home_resources": {
                    "message": "There are actually many helpful resources you can use at home while waiting for evaluation. This can make a real difference in your child's development. What area would you like to focus on?",
                    "tone": "encouraging"
                },
                "support_affording": {
                    "message": "I completely understand that accessing services can be expensive - this is a real challenge for many families. Let me help you explore your options for financial support and insurance coverage. We'll find a way to make this work for you.",
                    "tone": "supportive"
                }
            }
            
            return step_responses.get(step, {
                "message": "I'm here to help you figure this out. What specific information are you looking for?",
                "tone": "supportive"
            })
            
        except Exception as e:
            print(f"Error getting step response: {e}")
            return {
                "message": "I'm here to help you figure this out. What specific information are you looking for?",
                "tone": "supportive"
            }
    
    def _get_contextual_suggestions(self, context_path: str, conversation_state: Dict) -> List[str]:
        """Get contextual suggestions based on current context."""
        try:
            # Get available options from the router
            available_options = self.router.get_available_options(context_path)
            if available_options:
                # Convert options to natural questions
                natural_questions = []
                for option in available_options:
                    if option.get("label"):
                        # Create natural questions based on the option
                        label = option["label"].lower()
                        if "screening" in label or "csbs" in label:
                            natural_questions.append("How do I use the CSBS screening tool?")
                        elif "milestone" in label:
                            natural_questions.append("What developmental milestones should I watch for?")
                        elif "evaluation" in label:
                            natural_questions.append("Where can I get my child evaluated?")
                        elif "insurance" in label or "medicaid" in label:
                            natural_questions.append("What insurance options are available?")
                        elif "school" in label:
                            natural_questions.append("How can I get help with school services?")
                        elif "therapy" in label:
                            natural_questions.append("What types of therapy are available?")
                        else:
                            natural_questions.append(f"Tell me more about {option['label'].lower()}")
                
                if natural_questions:
                    return natural_questions
            
            # Provide contextual suggestions based on current path
            if "screening_options" in context_path:
                return [
                    "How do I know which screening tool to use?",
                    "What should I do with the screening results?",
                    "How often should I screen my child?"
                ]
            elif "evaluation_info" in context_path:
                return [
                    "How do I find a qualified evaluator?",
                    "What should I bring to the evaluation?",
                    "How long does the evaluation process take?"
                ]
            elif "support_affording" in context_path:
                return [
                    "What if I don't have insurance?",
                    "Are there sliding-scale options available?",
                    "What government programs can help?"
                ]
            elif "school" in context_path:
                return [
                    "How do I request a school evaluation?",
                    "What is an IEP and how do I get one?",
                    "What accommodations can my child receive?"
                ]
            elif "intervention" in context_path or "therapy" in context_path:
                return [
                    "What types of therapy are most effective?",
                    "How do I find qualified therapists?",
                    "What should I expect from therapy sessions?"
                ]
            else:
                return [
                    "What's the next step I should take?",
                    "Can you explain this in simpler terms?",
                    "What resources are available in my area?"
                ]
                
        except Exception as e:
            print(f"Error getting suggestions: {e}")
            return ["What would you like to know more about?"]
    
    def _extract_topic_from_context(self, context_path: str) -> str:
        """Extract the main topic from the context path."""
        if not context_path:
            return "general"
        
        parts = context_path.split(".")
        if len(parts) >= 2:
            return parts[1].replace("_", " ")
        return "general"
    
    def get_conversation_summary(self, conversation_state: Dict) -> Dict:
        """Get a summary of the current conversation."""
        return {
            "role": conversation_state.get("role", "unknown"),
            "diagnosis_status": conversation_state.get("diagnosis_status", "unknown"),
            "child_age": conversation_state.get("child_age", "unknown"),
            "current_step": conversation_state.get("current_step", "unknown"),
            "completed_steps": conversation_state.get("completed_steps", []),
            "current_topic": conversation_state.get("current_topic", "general"),
            "context_path": conversation_state.get("context_path", ""),
            "conversation_length": len(conversation_state.get("conversation_history", [])),
            "next_recommendations": self._get_next_recommendations(conversation_state)
        }
    
    def _get_next_recommendations(self, conversation_state: Dict) -> List[str]:
        """Get next recommendations based on current state."""
        current_topic = conversation_state.get("current_topic", "general")
        status = conversation_state.get("diagnosis_status", "diagnosed_no")
        
        if current_topic == "screening":
            if status == "diagnosed_no":
                return [
                    "Complete age-appropriate screening tools",
                    "Save results to share with pediatrician",
                    "Learn about developmental milestones"
                ]
            else:
                return [
                    "Focus on intervention and support",
                    "Explore therapy options",
                    "Connect with local resources"
                ]
        elif current_topic == "evaluation":
            return [
                "Contact recommended professionals",
                "Prepare required documents",
                "Check insurance coverage"
            ]
        elif current_topic == "resources":
            return [
                "Explore local service providers",
                "Check financial assistance options",
                "Connect with support groups"
            ]
        else:
            return [
                "Continue exploring relevant topics",
                "Ask specific questions about your concerns",
                "Save important information for later"
            ]
