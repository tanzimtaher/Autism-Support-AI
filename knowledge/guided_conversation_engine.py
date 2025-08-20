"""
Guided Conversation Engine for Autism Support App
Proactively guides users through structured conversation flows instead of reactive responses.
"""

import json
import openai
from typing import Dict, List, Optional, Tuple
from .conversation_router import ConversationRouter


class GuidedConversationEngine:
    def __init__(self, knowledge_base_path: str = "knowledge/structured_mongo.json"):
        """Initialize the guided conversation engine."""
        self.router = ConversationRouter(knowledge_base_path)
        self.conversation_flows = self._load_conversation_flows()
        self.active_conversations = {}
        
        # Initialize OpenAI client
        self.llm_client = None
        self.use_llm = False
        
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
            if api_key:
                self.llm_client = openai.OpenAI(api_key=api_key)
                self.use_llm = True
                print("OpenAI client initialized for guided conversations")
        except Exception as e:
            print(f"OpenAI not available for guided conversations: {e}")
    
    def _load_conversation_flows(self) -> Dict:
        """Load conversation flow definitions."""
        flows = {
            "screening_journey": {
                "name": "Autism Screening Journey",
                "description": "Guides parents through the screening process",
                "steps": [
                    {
                        "id": "step_1_concerns",
                        "question": "What specific behaviors are you seeing that concern you?",
                        "type": "information_gathering",
                        "context": "initial_concerns",
                        "next_steps": {
                            "communication": "step_2_communication",
                            "social": "step_2_social",
                            "behavior": "step_2_behavior",
                            "general": "step_2_general"
                        }
                    },
                    {
                        "id": "step_2_communication",
                        "question": "Tell me more about {child_name}'s communication. Does {child_name} respond to their name when you call them?",
                        "type": "detailed_assessment",
                        "context": "communication_skills",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_3_communication_yes",
                            "no": "step_3_communication_no",
                            "sometimes": "step_3_communication_sometimes"
                        }
                    },
                    {
                        "id": "step_2_social",
                        "question": "Let's talk about {child_name}'s social skills. Does {child_name} make eye contact when you talk to them?",
                        "type": "detailed_assessment",
                        "context": "social_skills",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_3_social_yes",
                            "no": "step_3_social_no",
                            "sometimes": "step_3_social_sometimes"
                        }
                    },
                    {
                        "id": "step_2_behavior",
                        "question": "I'd like to understand {child_name}'s behavior better. Does {child_name} have any repetitive movements or behaviors?",
                        "type": "detailed_assessment",
                        "context": "behavioral_patterns",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_3_behavior_yes",
                            "no": "step_3_behavior_no",
                            "sometimes": "step_3_behavior_sometimes"
                        }
                    },
                    {
                        "id": "step_2_general",
                        "question": "I'd like to understand {child_name} better. What's the most concerning behavior you've noticed?",
                        "type": "detailed_assessment",
                        "context": "general_concerns",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "communication": "step_2_communication",
                            "social": "step_2_social",
                            "behavior": "step_2_behavior",
                            "general": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_communication_no",
                        "question": "Thank you for sharing that. Does {child_name} use gestures like pointing or waving?",
                        "type": "detailed_assessment",
                        "context": "communication_gestures",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_urgent_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_communication_yes",
                        "question": "That's great! Does {child_name} use words or sounds to communicate?",
                        "type": "detailed_assessment",
                        "context": "communication_words",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_communication_sometimes",
                        "question": "I understand. Does {child_name} seem to understand what you're saying to them?",
                        "type": "detailed_assessment",
                        "context": "communication_understanding",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_social_yes",
                        "question": "That's wonderful! Does {child_name} enjoy playing with other children?",
                        "type": "detailed_assessment",
                        "context": "social_play",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_social_no",
                        "question": "I see. Does {child_name} show interest in what other people are doing?",
                        "type": "detailed_assessment",
                        "context": "social_interest",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_social_sometimes",
                        "question": "I understand. Does {child_name} share things with you, like showing you toys?",
                        "type": "detailed_assessment",
                        "context": "social_sharing",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_behavior_yes",
                        "question": "Can you tell me more about these repetitive movements? What do they look like?",
                        "type": "detailed_assessment",
                        "context": "behavior_details",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "general": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_behavior_no",
                        "question": "That's good to know. Does {child_name} have any strong interests or fixations?",
                        "type": "detailed_assessment",
                        "context": "behavior_interests",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_3_behavior_sometimes",
                        "question": "I understand. Does {child_name} get upset by changes in routine?",
                        "type": "detailed_assessment",
                        "context": "behavior_routine",
                        "tool": "csbs_checklist",
                        "next_steps": {
                            "yes": "step_4_recommend_screening",
                            "no": "step_4_recommend_screening",
                            "sometimes": "step_4_recommend_screening"
                        }
                    },
                    {
                        "id": "step_4_recommend_screening",
                        "question": "Based on what you've shared, I'd recommend we complete a screening tool together. The CSBS-DP Infant-Toddler Checklist is perfect for {child_name}'s age. Would you like to go through it now?",
                        "type": "recommendation",
                        "context": "screening_recommendation",
                        "action": "start_csbs_checklist",
                        "next_steps": {
                            "yes": "step_5_start_checklist",
                            "no": "step_5_alternative_help"
                        }
                    },
                    {
                        "id": "step_4_urgent_screening",
                        "question": "Based on what you've shared, I strongly recommend discussing these concerns with your pediatrician as soon as possible. Early intervention can make a significant difference. Would you like help preparing for that conversation?",
                        "type": "urgent_recommendation",
                        "context": "urgent_screening",
                        "action": "urgent_pediatrician_visit",
                        "next_steps": {
                            "yes": "step_5_prepare_conversation",
                            "no": "step_5_alternative_help"
                        }
                    },
                    {
                        "id": "step_5_start_checklist",
                        "question": "Great! Let's start with the CSBS-DP checklist. Question 1: Does {child_name} respond to their name when called? (Yes/No/Sometimes)",
                        "type": "checklist_question",
                        "context": "csbs_checklist",
                        "checklist_item": 1,
                        "next_steps": {
                            "yes": "step_6_checklist_2",
                            "no": "step_6_checklist_2",
                            "sometimes": "step_6_checklist_2"
                        }
                    },
                    {
                        "id": "step_5_alternative_help",
                        "question": "No problem! I can still help you in other ways. Would you like information about developmental milestones, resources for parents, or something else?",
                        "type": "alternative_support",
                        "context": "alternative_help",
                        "next_steps": {
                            "milestones": "step_6_milestones",
                            "resources": "step_6_resources",
                            "other": "step_6_other"
                        }
                    },
                    {
                        "id": "step_5_prepare_conversation",
                        "question": "Great! Let me help you prepare for your pediatrician visit. Here are some key points to mention: [list of concerns]. Would you like me to help you create a written summary to bring with you?",
                        "type": "conversation_preparation",
                        "context": "pediatrician_prep",
                        "action": "create_summary",
                        "next_steps": {
                            "yes": "step_6_create_summary",
                            "no": "step_6_conversation_end"
                        }
                    },
                    {
                        "id": "step_6_checklist_2",
                        "question": "Question 2: Does {child_name} look at you when you talk to them? (Yes/No/Sometimes)",
                        "type": "checklist_question",
                        "context": "csbs_checklist",
                        "checklist_item": 2,
                        "next_steps": {
                            "yes": "step_7_checklist_3",
                            "no": "step_7_checklist_3",
                            "sometimes": "step_7_checklist_3"
                        }
                    },
                    {
                        "id": "step_6_milestones",
                        "question": "I'd be happy to help you understand developmental milestones. What age is {child_name}?",
                        "type": "milestone_info",
                        "context": "developmental_milestones",
                        "next_steps": {
                            "general": "step_7_milestone_details"
                        }
                    },
                    {
                        "id": "step_6_resources",
                        "question": "Great! I can help you find resources. What type of support are you looking for - local services, online resources, or support groups?",
                        "type": "resource_finding",
                        "context": "parent_resources",
                        "next_steps": {
                            "local": "step_7_local_resources",
                            "online": "step_7_online_resources",
                            "groups": "step_7_support_groups"
                        }
                    },
                    {
                        "id": "step_6_other",
                        "question": "I'm here to help! What specific information or support do you need?",
                        "type": "general_support",
                        "context": "other_help",
                        "next_steps": {
                            "general": "step_7_general_help"
                        }
                    },
                    {
                        "id": "step_6_create_summary",
                        "question": "Perfect! I'll create a summary of our conversation and your concerns. This will help your pediatrician understand the situation better. Would you like me to email this to you or save it for you to download?",
                        "type": "summary_creation",
                        "context": "create_document",
                        "action": "generate_summary",
                        "next_steps": {
                            "email": "step_7_email_summary",
                            "download": "step_7_download_summary",
                            "both": "step_7_both_summary"
                        }
                    },
                    {
                        "id": "step_6_conversation_end",
                        "question": "Thank you for sharing with me today. I hope our conversation has been helpful. Remember, I'm here whenever you need support. Take care!",
                        "type": "conversation_end",
                        "context": "final_goodbye",
                        "next_steps": {}
                    },
                    {
                        "id": "step_7_checklist_3",
                        "question": "Question 3: Does {child_name} point to things they want or are interested in? (Yes/No/Sometimes)",
                        "type": "checklist_question",
                        "context": "csbs_checklist",
                        "checklist_item": 3,
                        "next_steps": {
                            "yes": "step_8_checklist_4",
                            "no": "step_8_checklist_4",
                            "sometimes": "step_8_checklist_4"
                        }
                    },
                    {
                        "id": "step_7_milestone_details",
                        "question": "Based on {child_name}'s age, here are the key developmental milestones to watch for. Would you like me to explain any specific area in more detail?",
                        "type": "milestone_details",
                        "context": "milestone_explanation",
                        "next_steps": {
                            "general": "step_8_milestone_summary"
                        }
                    },
                    {
                        "id": "step_7_local_resources",
                        "question": "I can help you find local resources. What's your general location (city/state) so I can provide relevant information?",
                        "type": "local_resource_finding",
                        "context": "location_based_resources",
                        "next_steps": {
                            "general": "step_8_resource_list"
                        }
                    },
                    {
                        "id": "step_7_online_resources",
                        "question": "Great! I can recommend some excellent online resources. Are you looking for educational materials, support groups, or professional organizations?",
                        "type": "online_resource_finding",
                        "context": "online_resources",
                        "next_steps": {
                            "general": "step_8_resource_list"
                        }
                    },
                    {
                        "id": "step_7_support_groups",
                        "question": "Support groups can be incredibly helpful. Are you looking for in-person groups, online communities, or both?",
                        "type": "support_group_finding",
                        "context": "support_groups",
                        "next_steps": {
                            "general": "step_8_resource_list"
                        }
                    },
                    {
                        "id": "step_7_general_help",
                        "question": "I'm here to support you in any way I can. What specific help do you need right now?",
                        "type": "general_support",
                        "context": "general_help",
                        "next_steps": {
                            "general": "step_8_general_summary"
                        }
                    },
                    {
                        "id": "step_7_email_summary",
                        "question": "I'll email the summary to you right away. Please check your email in a few minutes. Is there anything else I can help you with today?",
                        "type": "email_confirmation",
                        "context": "email_sent",
                        "action": "send_email",
                        "next_steps": {
                            "general": "step_8_general_summary"
                        }
                    },
                    {
                        "id": "step_7_download_summary",
                        "question": "Your summary is ready for download. You can save this document and bring it to your pediatrician appointment. Is there anything else I can help you with today?",
                        "type": "download_confirmation",
                        "context": "download_ready",
                        "action": "provide_download",
                        "next_steps": {
                            "general": "step_8_general_summary"
                        }
                    },
                    {
                        "id": "step_7_both_summary",
                        "question": "Perfect! I'll email the summary to you and also make it available for download. You'll receive the email shortly, and you can download the document now. Is there anything else I can help you with today?",
                        "type": "both_confirmation",
                        "context": "both_ready",
                        "action": "send_email_and_download",
                        "next_steps": {
                            "general": "step_8_general_summary"
                        }
                    },
                    {
                        "id": "step_8_checklist_4",
                        "question": "Question 4: Does {child_name} show you things they're interested in? (Yes/No/Sometimes)",
                        "type": "checklist_question",
                        "context": "csbs_checklist",
                        "checklist_item": 4,
                        "next_steps": {
                            "yes": "step_9_checklist_summary",
                            "no": "step_9_checklist_summary",
                            "sometimes": "step_9_checklist_summary"
                        }
                    },
                    {
                        "id": "step_8_milestone_summary",
                        "question": "Thank you for learning about developmental milestones with me. Is there anything else you'd like to know about {child_name}'s development?",
                        "type": "milestone_summary",
                        "context": "milestone_wrapup",
                        "next_steps": {
                            "general": "step_9_conversation_end"
                        }
                    },
                    {
                        "id": "step_8_resource_list",
                        "question": "Here are some resources that might be helpful for you. Would you like me to explain any of these in more detail?",
                        "type": "resource_summary",
                        "context": "resource_wrapup",
                        "next_steps": {
                            "general": "step_9_conversation_end"
                        }
                    },
                    {
                        "id": "step_8_general_summary",
                        "question": "I hope I've been able to help you today. Is there anything else you'd like to discuss about {child_name}?",
                        "type": "general_summary",
                        "context": "general_wrapup",
                        "next_steps": {
                            "general": "step_9_conversation_end"
                        }
                    },
                    {
                        "id": "step_9_checklist_summary",
                        "question": "Thank you for completing the screening questions with me. Based on your responses, I'd recommend discussing these concerns with your pediatrician. Would you like me to help you prepare for that conversation?",
                        "type": "checklist_summary",
                        "context": "checklist_wrapup",
                        "next_steps": {
                            "general": "step_9_conversation_end"
                        }
                    },
                    {
                        "id": "step_9_conversation_end",
                        "question": "Thank you for sharing with me today. I'm here whenever you need support. Take care!",
                        "type": "conversation_end",
                        "context": "final_goodbye",
                        "next_steps": {}
                    }
                ]
            },
            "diagnosis_journey": {
                "name": "Post-Diagnosis Support Journey",
                "description": "Guides parents through post-diagnosis support",
                "steps": [
                    {
                        "id": "step_1_diagnosis_reaction",
                        "question": "How are you feeling about {child_name}'s diagnosis? This can be a lot to process.",
                        "type": "emotional_support",
                        "context": "diagnosis_reaction",
                        "next_steps": {
                            "overwhelmed": "step_2_overwhelmed_support",
                            "relieved": "step_2_relieved_support",
                            "confused": "step_2_confused_support"
                        }
                    },
                    {
                        "id": "step_2_overwhelmed_support",
                        "question": "It's completely normal to feel overwhelmed. Many parents feel this way. What's the most overwhelming part for you right now?",
                        "type": "emotional_support",
                        "context": "overwhelmed_help",
                        "next_steps": {
                            "general": "step_3_resource_help"
                        }
                    },
                    {
                        "id": "step_2_relieved_support",
                        "question": "That's wonderful! Having a diagnosis can bring clarity and open doors to support. What type of help are you looking for now?",
                        "type": "positive_support",
                        "context": "relieved_help",
                        "next_steps": {
                            "general": "step_3_resource_help"
                        }
                    },
                    {
                        "id": "step_2_confused_support",
                        "question": "It's okay to feel confused. A diagnosis can bring up many questions. What would help you feel more clear about the next steps?",
                        "type": "clarification_support",
                        "context": "confused_help",
                        "next_steps": {
                            "general": "step_3_resource_help"
                        }
                    },
                    {
                        "id": "step_3_resource_help",
                        "question": "I can help you find the right resources and support. What's most important to you right now - therapy services, school support, parent resources, or something else?",
                        "type": "resource_guidance",
                        "context": "post_diagnosis_resources",
                        "next_steps": {
                            "therapy": "step_4_therapy_help",
                            "school": "step_4_school_help",
                            "resources": "step_4_parent_resources",
                            "other": "step_4_other_help"
                        }
                    },
                    {
                        "id": "step_4_therapy_help",
                        "question": "Great! Therapy can be incredibly helpful. What type of therapy are you interested in - speech therapy, occupational therapy, behavioral therapy, or a combination?",
                        "type": "therapy_guidance",
                        "context": "therapy_options",
                        "next_steps": {
                            "general": "step_5_therapy_resources"
                        }
                    },
                    {
                        "id": "step_4_school_help",
                        "question": "School support is crucial! Are you looking for information about IEPs, classroom accommodations, or finding the right school environment?",
                        "type": "school_guidance",
                        "context": "school_support",
                        "next_steps": {
                            "general": "step_5_school_resources"
                        }
                    },
                    {
                        "id": "step_4_parent_resources",
                        "question": "Parent resources can make a huge difference! Are you looking for support groups, educational materials, or help with daily challenges?",
                        "type": "parent_resource_guidance",
                        "context": "parent_support",
                        "next_steps": {
                            "general": "step_5_parent_resources"
                        }
                    },
                    {
                        "id": "step_4_other_help",
                        "question": "I'm here to help with whatever you need. What specific support or information are you looking for?",
                        "type": "general_guidance",
                        "context": "other_support",
                        "next_steps": {
                            "general": "step_5_general_resources"
                        }
                    },
                    {
                        "id": "step_5_therapy_resources",
                        "question": "I can help you find therapy resources in your area. What's your general location so I can provide relevant recommendations?",
                        "type": "therapy_resource_finding",
                        "context": "local_therapy",
                        "next_steps": {
                            "general": "step_6_conversation_end"
                        }
                    },
                    {
                        "id": "step_5_school_resources",
                        "question": "I can help you understand school support options and find resources. Would you like information about IEPs, classroom strategies, or school selection?",
                        "type": "school_resource_finding",
                        "context": "school_resources",
                        "next_steps": {
                            "general": "step_6_conversation_end"
                        }
                    },
                    {
                        "id": "step_5_parent_resources",
                        "question": "I can help you find parent support resources. Would you like information about support groups, educational materials, or practical strategies for daily life?",
                        "type": "parent_resource_finding",
                        "context": "parent_resources",
                        "next_steps": {
                            "general": "step_6_conversation_end"
                        }
                    },
                    {
                        "id": "step_5_general_resources",
                        "question": "I can help you find the right resources for your situation. What specific type of support or information would be most helpful right now?",
                        "type": "general_resource_finding",
                        "context": "general_resources",
                        "next_steps": {
                            "general": "step_6_conversation_end"
                        }
                    }
                ]
            }
        }
        return flows
    
    def start_guided_conversation(self, user_profile: Dict) -> Dict:
        """Start a guided conversation based on user profile."""
        conversation_id = f"guided_{user_profile['role']}_{user_profile['diagnosis_status']}_{user_profile.get('child_age', 'unknown')}"
        
        # Determine the right conversation flow
        flow_name = self._determine_flow(user_profile)
        flow = self.conversation_flows[flow_name]
        
        # Initialize conversation state
        conversation_state = {
            "conversation_id": conversation_id,
            "flow_name": flow_name,
            "current_step_id": flow["steps"][0]["id"],
            "step_history": [],
            "user_profile": user_profile,
            "extracted_info": {},
            "context": {}
        }
        
        self.active_conversations[conversation_id] = conversation_state
        
        # Get the first question
        first_step = self._get_step(flow_name, flow["steps"][0]["id"])
        question = self._personalize_question(first_step["question"], user_profile)
        
        return {
            "conversation_id": conversation_id,
            "message": question,
            "flow_name": flow["name"],
            "flow_description": flow["description"],
            "current_step": 1,
            "total_steps": len(flow["steps"]),
            "tone": "empathetic_guide"
        }
    
    def process_guided_response(self, user_input: str, conversation_id: str) -> Dict:
        """Process user response and determine next step in guided conversation."""
        if conversation_id not in self.active_conversations:
            return {"error": "Conversation not found"}
        
        conversation_state = self.active_conversations[conversation_id]
        flow_name = conversation_state["flow_name"]
        current_step_id = conversation_state["current_step_id"]
        
        # Analyze user response
        response_analysis = self._analyze_response(user_input, conversation_state)
        
        # Update conversation state with extracted information
        self._update_conversation_state(conversation_state, response_analysis)
        
        # Determine next step
        next_step_id = self._determine_next_step(current_step_id, response_analysis, conversation_state)
        
        if next_step_id:
            # Move to next step
            conversation_state["current_step_id"] = next_step_id
            conversation_state["step_history"].append({
                "step_id": current_step_id,
                "user_response": user_input,
                "analysis": response_analysis
            })
            
            next_step = self._get_step(flow_name, next_step_id)
            question = self._personalize_question(next_step["question"], conversation_state["user_profile"])
            
            return {
                "conversation_id": conversation_id,
                "message": question,
                "current_step": len(conversation_state["step_history"]) + 1,
                "total_steps": len(self.conversation_flows[flow_name]["steps"]),
                "context": next_step.get("context", ""),
                "tone": "empathetic_guide"
            }
        else:
            # End of flow - provide summary and next steps
            return self._end_conversation_flow(conversation_state)
    
    def _determine_flow(self, user_profile: Dict) -> str:
        """Determine which conversation flow to use based on user profile."""
        if user_profile["diagnosis_status"] == "diagnosed_yes":
            return "diagnosis_journey"
        else:
            return "screening_journey"
    
    def _get_step(self, flow_name: str, step_id: str) -> Dict:
        """Get a specific step from a conversation flow."""
        flow = self.conversation_flows[flow_name]
        for step in flow["steps"]:
            if step["id"] == step_id:
                return step
        return None
    
    def _personalize_question(self, question: str, user_profile: Dict) -> str:
        """Personalize a question with user's child's name."""
        child_name = user_profile.get("child_name", "your child")
        return question.replace("{child_name}", child_name)
    
    def _analyze_response(self, user_input: str, conversation_state: Dict) -> Dict:
        """Analyze user response to determine next step."""
        if not self.use_llm or not self.llm_client:
            return self._analyze_response_rule_based(user_input)
        
        try:
            current_step = self._get_step(conversation_state["flow_name"], conversation_state["current_step_id"])
            next_steps = current_step.get("next_steps", {})
            
            system_prompt = f"""
            Analyze this user response in the context of a guided autism screening conversation.
            
            Current step context: {current_step.get('context', '')}
            Available next steps: {list(next_steps.keys())}
            
            Determine which next step to take based on the user's response.
            Return ONLY the next step key from the available options.
            """
            
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            next_step = response.choices[0].message.content.strip().lower()
            
            # Validate next step
            if next_step in next_steps:
                return {"next_step": next_step, "confidence": "high"}
            else:
                return self._analyze_response_rule_based(user_input)
                
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._analyze_response_rule_based(user_input)
    
    def _analyze_response_rule_based(self, user_input: str) -> Dict:
        """Rule-based response analysis as fallback."""
        user_input_lower = user_input.lower()
        
        # Simple keyword matching
        if any(word in user_input_lower for word in ["yes", "yeah", "sure", "okay", "alright"]):
            return {"next_step": "yes", "confidence": "medium"}
        elif any(word in user_input_lower for word in ["no", "not", "never", "doesn't", "doesnt"]):
            return {"next_step": "no", "confidence": "medium"}
        elif any(word in user_input_lower for word in ["sometimes", "maybe", "occasionally", "rarely"]):
            return {"next_step": "sometimes", "confidence": "medium"}
        elif any(word in user_input_lower for word in ["communication", "speech", "talk", "language"]):
            return {"next_step": "communication", "confidence": "medium"}
        elif any(word in user_input_lower for word in ["social", "friends", "play", "interact"]):
            return {"next_step": "social", "confidence": "medium"}
        elif any(word in user_input_lower for word in ["behavior", "act", "tantrum", "meltdown"]):
            return {"next_step": "behavior", "confidence": "medium"}
        else:
            return {"next_step": "general", "confidence": "low"}
    
    def _determine_next_step(self, current_step_id: str, response_analysis: Dict, conversation_state: Dict) -> str:
        """Determine the next step based on current step and response analysis."""
        current_step = self._get_step(conversation_state["flow_name"], current_step_id)
        next_steps = current_step.get("next_steps", {})
        
        next_step_key = response_analysis.get("next_step", "general")
        
        # Get the next step ID
        next_step_id = next_steps.get(next_step_key)
        
        return next_step_id
    
    def _update_conversation_state(self, conversation_state: Dict, response_analysis: Dict):
        """Update conversation state with extracted information."""
        # Extract child information if mentioned
        if "child_name" in response_analysis:
            conversation_state["user_profile"]["child_name"] = response_analysis["child_name"]
        
        # Store response analysis
        conversation_state["extracted_info"].update(response_analysis)
    
    def _end_conversation_flow(self, conversation_state: Dict) -> Dict:
        """End the conversation flow and provide summary."""
        flow_name = conversation_state["flow_name"]
        
        if flow_name == "screening_journey":
            message = f"Thank you for sharing about {conversation_state['user_profile'].get('child_name', 'your child')}. Based on our conversation, I recommend:\n\n" \
                     f"1. **Complete the CSBS-DP Checklist** - I can guide you through it\n" \
                     f"2. **Schedule a pediatrician visit** - Share your concerns and screening results\n" \
                     f"3. **Keep a behavior log** - Document specific behaviors you observe\n\n" \
                     f"Would you like me to help you with any of these next steps?"
        
        return {
            "conversation_id": conversation_state["conversation_id"],
            "message": message,
            "flow_completed": True,
            "next_actions": ["complete_checklist", "schedule_visit", "behavior_log"],
            "tone": "supportive_summary"
        }
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """Get a summary of the guided conversation."""
        if conversation_id not in self.active_conversations:
            return {"error": "Conversation not found"}
        
        conversation_state = self.active_conversations[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "flow_name": conversation_state["flow_name"],
            "current_step": conversation_state["current_step_id"],
            "steps_completed": len(conversation_state["step_history"]),
            "user_profile": conversation_state["user_profile"],
            "extracted_info": conversation_state["extracted_info"],
            "step_history": conversation_state["step_history"]
        }
