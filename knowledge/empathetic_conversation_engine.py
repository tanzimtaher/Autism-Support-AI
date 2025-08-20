"""
Intelligent Conversation Engine for Autism Support App
Uses LLM for natural language understanding and knowledge base integration.
"""

import json
import re
import openai
from typing import Dict, List, Optional, Tuple
from .conversation_router import ConversationRouter


class EmpatheticConversationEngine:
    def __init__(self, knowledge_base_path: str = "knowledge/structured_mongo.json"):
        """Initialize the intelligent conversation engine."""
        self.router = ConversationRouter(knowledge_base_path)
        self.conversation_memory = {}
        
        # Initialize OpenAI client from Streamlit secrets
        self.llm_client = None
        self.use_llm = False
        
        try:
            import openai
            import streamlit as st
            
            # Try to get API key from Streamlit secrets
            try:
                api_key = st.secrets.get("OPENAI_API_KEY")
                if api_key:
                    self.llm_client = openai.OpenAI(api_key=api_key)
                    self.use_llm = True
                    print("OpenAI client initialized successfully from Streamlit secrets")
                else:
                    print("No OPENAI_API_KEY found in Streamlit secrets, using rule-based approach")
            except Exception as secrets_error:
                print(f"Could not access Streamlit secrets: {secrets_error}")
                # Fallback to environment variable
                import os
                if os.getenv('OPENAI_API_KEY'):
                    self.llm_client = openai.OpenAI()
                    self.use_llm = True
                    print("OpenAI client initialized successfully from environment variable")
                else:
                    print("No OPENAI_API_KEY found in environment, using rule-based approach")
                    
        except Exception as e:
            print(f"Warning: OpenAI not available, falling back to rule-based approach: {e}")
            self.llm_client = None
            self.use_llm = False
    
    def start_conversation(self, user_profile: Dict) -> Dict:
        """Start an intelligent conversation based on user profile."""
        conversation_id = f"{user_profile['role']}_{user_profile['diagnosis_status']}_{user_profile.get('child_age', 'unknown')}"
        self.conversation_memory[conversation_id] = {
            "profile": user_profile,
            "topics_covered": [],
            "conversation_history": [],
            "extracted_info": {},
            "current_path": "entry_point",
            "emotional_state": "seeking_information"
        }
        
        # Get personalized greeting - no more suggestions, just empathetic questions
        greeting = self._get_knowledge_based_greeting(user_profile)
        
        return {
            "message": greeting,
            "tone": "warm_supportive",
            "conversation_id": conversation_id,
            "conversation_state": self.conversation_memory[conversation_id]
        }
    
    def _get_knowledge_based_greeting(self, user_profile: Dict) -> str:
        """Get greeting from knowledge base based on user profile."""
        try:
            if user_profile["role"] == "parent_caregiver":
                if user_profile["diagnosis_status"] == "diagnosed_no":
                    # More empathetic, question-based approach
                    return "Hi there! I'm here to help guide you through autism support and resources. I know this can feel overwhelming when you're concerned about your child's development. Let me understand your situation better - what brought you here today?"
                else:
                    entry = self.router.get_knowledge_entry("diagnosed_yes.find_resources.caregiver_support")
                    if entry and "response" in entry:
                        return entry["response"]
            
            # Fallback greeting - more empathetic and question-focused
            return "Hi there! I'm here to help guide you through autism support and resources. I know this journey can feel overwhelming. What brought you here today? I'd love to understand your situation better so I can provide the most relevant help."
            
        except Exception as e:
            print(f"Error accessing knowledge base: {e}")
            return "Hi there! I'm here to help guide you through autism support and resources. What brought you here today?"
    
    def _get_intelligent_starters(self, user_profile: Dict) -> List[str]:
        """Get intelligent conversation starters based on knowledge base."""
        try:
            if user_profile["role"] == "parent_caregiver" and user_profile["diagnosis_status"] == "diagnosed_no":
                if user_profile["child_age"] in ["0-3", "3-5"]:
                    return [
                        "What specific behaviors are you seeing that concern you?",
                        "How does your child's development compare to other children their age?",
                        "What made you decide to look into autism screening?"
                    ]
                else:
                    return [
                        "What specific challenges is your child facing at school?",
                        "How long have you been concerned about their development?",
                        "What have you tried so far to help your child?"
                    ]
            elif user_profile["role"] == "parent_caregiver" and user_profile["diagnosis_status"] == "diagnosed_yes":
                return [
                    "What's your biggest challenge right now with the diagnosis?",
                    "What type of support are you looking for most urgently?",
                    "How are you feeling about the diagnosis?"
                ]
            
            return ["What brought you here today?", "What would be most helpful for me to know about your situation?"]
            
        except Exception as e:
            print(f"Error getting conversation starters: {e}")
            return ["What brought you here today?"]
    
    def process_user_input(self, user_input: str, conversation_id: str) -> Dict:
        """Process user input with LLM-based understanding and knowledge base routing."""
        if conversation_id not in self.conversation_memory:
            return {"error": "Conversation not found. Please start a new conversation."}
        
        memory = self.conversation_memory[conversation_id]
        
        # Update profile with extracted information from chat
        self._update_profile_from_chat(user_input, memory)
        
        # Use LLM to extract information and understand intent
        extracted_info = self._extract_info_with_llm(user_input, memory)
        user_intent = self._determine_intent_with_llm(user_input, memory)
        
        # Get response from knowledge base based on current path and intent
        response = self._get_knowledge_based_response(user_intent, memory)
        
        # Add to conversation history
        memory["conversation_history"].append({
            "role": "user",
            "content": user_input,
            "extracted_info": extracted_info,
            "intent": user_intent
        })
        
        memory["conversation_history"].append({
            "role": "assistant",
            "content": response,
            "intent_addressed": user_intent
        })
        
        # Update conversation path
        self._update_conversation_path(user_intent, memory)
        
        return {
            "message": response,
            "tone": "empathetic_supportive",
            "conversation_id": conversation_id,
            "helpful_resources": self._get_relevant_resources(user_intent, memory["profile"]),
            "next_steps": self._get_next_steps(user_intent, memory)
        }
    
    def _update_profile_from_chat(self, user_input: str, memory: Dict):
        """Extract and update user profile information from chat messages using LLM."""
        profile = memory["profile"]
        
        # Use LLM for intelligent information extraction if available
        if self.use_llm and self.llm_client:
            try:
                print(f"Attempting LLM extraction for: {user_input[:50]}...")
                extracted_info = self._extract_info_with_llm(user_input, profile)
                
                if extracted_info and isinstance(extracted_info, dict):
                    print(f"LLM extracted info: {extracted_info}")
                    
                    # Update profile with extracted information
                    if "age_band" in extracted_info and extracted_info["age_band"]:
                        old_age = profile.get("child_age", "unknown")
                        profile["child_age"] = extracted_info["age_band"]
                        print(f"Updated age from {old_age} to {profile['child_age']}")
                        
                    if "child_name" in extracted_info and extracted_info["child_name"]:
                        old_name = profile.get("child_name", "unknown")
                        profile["child_name"] = extracted_info["child_name"]
                        print(f"Updated name from {old_name} to {profile['child_name']}")
                        
                    if "child_gender" in extracted_info and extracted_info["child_gender"]:
                        old_gender = profile.get("child_gender", "unknown")
                        profile["child_gender"] = extracted_info["child_gender"]
                        print(f"Updated gender from {old_gender} to {profile['child_gender']}")
                        
                    if "parent_name" in extracted_info and extracted_info["parent_name"]:
                        old_parent = profile.get("parent_name", "unknown")
                        profile["parent_name"] = extracted_info["parent_name"]
                        print(f"Updated parent name from {old_parent} to {profile['parent_name']}")
                        
                    if "diagnosis_status" in extracted_info and extracted_info["diagnosis_status"]:
                        old_status = profile.get("diagnosis_status", "unknown")
                        profile["diagnosis_status"] = extracted_info["diagnosis_status"]
                        print(f"Updated diagnosis status from {old_status} to {profile['diagnosis_status']}")
                    
                    # Store additional context information
                    if "specific_concerns" in extracted_info and extracted_info["specific_concerns"]:
                        if "specific_concerns" not in profile:
                            profile["specific_concerns"] = []
                        profile["specific_concerns"].extend(extracted_info["specific_concerns"])
                        print(f"Added concerns: {extracted_info['specific_concerns']}")
                        
                    if "professionals_mentioned" in extracted_info and extracted_info["professionals_mentioned"]:
                        if "professionals_mentioned" not in profile:
                            profile["professionals_mentioned"] = []
                        profile["professionals_mentioned"].extend(extracted_info["professionals_mentioned"])
                        print(f"Added professionals: {extracted_info['professionals_mentioned']}")
                        
                    if "challenges_strengths" in extracted_info and extracted_info["challenges_strengths"]:
                        if "challenges_strengths" not in profile:
                            profile["challenges_strengths"] = []
                        profile["challenges_strengths"].extend(extracted_info["challenges_strengths"])
                        print(f"Added challenges/strengths: {extracted_info['challenges_strengths']}")
                    
                    return  # Successfully updated with LLM
                else:
                    print("LLM extraction returned no valid information, falling back to rule-based")
                    
            except Exception as e:
                print(f"LLM extraction failed with exception: {e}")
        else:
            print("LLM not available, using rule-based extraction")
        
        # Fallback to rule-based extraction
        print("Using rule-based extraction as fallback")
        self._extract_info_rule_based(user_input, profile)
    
    def _extract_info_with_llm(self, user_input: str, profile: Dict) -> Dict:
        """Use LLM to intelligently extract information from user input."""
        if not self.use_llm or not self.llm_client:
            return {}
            
        try:
            system_prompt = f"""
            Extract comprehensive information from this message about a child and their family:
            
            Current profile: {profile}
            
            Extract ALL relevant information:
            - child's name (full name if provided)
            - child's age (convert to age band: 0-3, 3-5, 6-12, 13-17, 18+)
            - child's gender (male/female/other)
            - parent/caregiver name
            - diagnosis status (diagnosed_yes/diagnosed_no)
            - any specific behaviors, concerns, or symptoms mentioned
            - any medical or educational professionals mentioned
            - any specific challenges or strengths mentioned
            
            Return JSON only: {{
                "child_name": "Full Name",
                "age_band": "3-5", 
                "child_gender": "male",
                "parent_name": "Parent Name",
                "diagnosis_status": "diagnosed_yes",
                "specific_concerns": ["list of concerns"],
                "professionals_mentioned": ["list of professionals"],
                "challenges_strengths": ["list of challenges/strengths"]
            }}
            
            If you cannot extract any information, return: {{}}
            
            Note: Be smart about typos (e.g., "make" = male, "famale" = female)
            """
            
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                max_tokens=200  # Increased for more comprehensive extraction
            )
            
            content = response.choices[0].message.content.strip()
            
            # Validate response content
            if not content or content == "" or content.isspace():
                print(f"LLM returned empty response for input: {user_input[:50]}...")
                return {}
            
            # Try to parse JSON
            try:
                extracted_info = json.loads(content)
                
                # Validate extracted info structure
                if not isinstance(extracted_info, dict):
                    print(f"LLM returned non-dict response: {type(extracted_info)}")
                    return {}
                
                # Check if we got meaningful information
                has_info = False
                for key in ["child_name", "age_band", "child_gender", "parent_name", "diagnosis_status"]:
                    if key in extracted_info and extracted_info[key]:
                        has_info = True
                        break
                
                if not has_info:
                    print(f"LLM returned empty values: {extracted_info}")
                    return {}
                
                print(f"LLM extraction successful: {extracted_info}")
                return extracted_info
                
            except json.JSONDecodeError as json_err:
                print(f"LLM returned invalid JSON: {content[:100]}... Error: {json_err}")
                return {}
                
        except Exception as e:
            print(f"LLM extraction failed with error: {e}")
            return {}
    
    def _extract_info_rule_based(self, user_input: str, profile: Dict):
        """Fallback rule-based information extraction."""
        user_input_lower = user_input.lower()
        
        # Extract age with more patterns
        age_patterns = [
            (r'(\d+)\s*years?\s*old', "child_age"),
            (r'age\s+is\s+(\d+)', "child_age"),
            (r'he\s+is\s+(\d+)', "child_age"),
            (r'she\s+is\s+(\d+)', "child_age"),
            (r'(\d+)\s*years?', "child_age"),
            (r'age\s+(\d+)', "child_age")
        ]
        
        for pattern, field in age_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                age = int(match.group(1))
                if age <= 3: profile[field] = "0-3"
                elif age <= 5: profile[field] = "3-5"
                elif age <= 12: profile[field] = "6-12"
                elif age <= 17: profile[field] = "13-17"
                else: profile[field] = "18+"
                break
        
        # Extract name with improved patterns
        name_patterns = [
            r'my (?:child|son|daughter)[\'s]?\s*name\s*is\s*([A-Za-z\s]+?)(?:\s+is|\s+has|\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'(?:he|she)[\'s]?\s+([A-Za-z\s]+?)(?:\s+is|\s+has|\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'([A-Za-z\s]+?)\s+(?:is my child|has been diagnosed)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'his name is ([A-Za-z\s]+?)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'her name is ([A-Za-z\s]+?)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'my (?:child|son|daughter)\s+([A-Za-z\s]+?)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'name\s+is\s+([A-Za-z\s]+?)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)',
            r'([A-Za-z\s]+?)\s+is\s+my\s+(?:child|son|daughter)(?:\s+and|\s+is\s+\d+|\s+\d+\s+years?|$)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                name = match.group(1).strip().title()
                # Clean up the name - remove extra words
                name = re.sub(r'\s+(?:is|has|and|is\s+\d+|\d+\s+years?)$', '', name).strip()
                if len(name) > 1:  # Only set if we have a meaningful name
                    profile["child_name"] = name
                    break
        
        # Extract parent name
        parent_patterns = [
            r'my name is ([A-Za-z\s]+?)(?:\s+and|\s+is|\s+has|$)',
            r'i\'m ([A-Za-z\s]+?)(?:\s+and|\s+is|\s+has|$)',
            r'i am ([A-Za-z\s]+?)(?:\s+and|\s+is|\s+has|$)',
            r'([A-Za-z\s]+?)\s+(?:is my name|here|parent|mother|father)(?:\s+and|\s+is|\s+has|$)'
        ]
        
        for pattern in parent_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                parent_name = match.group(1).strip().title()
                # Clean up the name
                parent_name = re.sub(r'\s+(?:and|is|has)$', '', parent_name).strip()
                if len(parent_name) > 1:
                    profile["parent_name"] = parent_name
                    break
        
        # Extract gender with typo handling
        gender_patterns = [
            (r'\b(?:he|his|boy|male)\b', "male"),
            (r'\b(?:she|her|girl|female)\b', "female"),
            (r'\bmake\b', "male"),  # Handle typo "make" = male
            (r'\bfamale\b', "female"),  # Handle typo "famale" = female
            (r'\b(?:son|brother)\b', "male"),
            (r'\b(?:daughter|sister)\b', "female")
        ]
        
        for pattern, gender in gender_patterns:
            if re.search(pattern, user_input_lower):
                profile["child_gender"] = gender
                break
        
        # Extract diagnosis status
        if any(word in user_input_lower for word in ["diagnosed", "diagnosis", "has autism", "autism"]):
            profile["diagnosis_status"] = "diagnosed_yes"
        elif any(word in user_input_lower for word in ["no diagnosis", "not diagnosed", "suspected", "concerned"]):
            profile["diagnosis_status"] = "diagnosed_no"
    
    def _determine_intent_with_llm(self, user_input: str, memory: Dict) -> str:
        """Use LLM to determine user intent."""
        if not self.use_llm or not self.llm_client:
            return self._determine_intent_rule_based(user_input)
        
        try:
            profile = memory["profile"]
            system_prompt = f"""
            You are an AI assistant helping determine the user's intent in an autism support conversation.
            
            User profile: {profile}
            
            Categorize the user's intent into one of these categories:
            - wants_screening_info: Questions about screening, testing, assessment
            - needs_resources: Looking for therapy, services, support resources
            - school_concerns: Questions about school, IEP, 504, education
            - financial_concerns: Questions about costs, insurance, financial support
            - professional_evaluation: Questions about doctors, specialists, evaluation process
            - wants_understanding: Questions about autism, signs, symptoms, understanding
            - needs_next_steps: Asking what to do next, next steps
            - general_question: General questions or unclear intent
            
            Return ONLY the category name, nothing else.
            """
            
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                max_tokens=50  # Limit response length for intent
            )
            
            intent = response.choices[0].message.content.strip()
            
            # Validate response content
            if not intent or intent == "" or intent.isspace():
                print(f"LLM returned empty intent for input: {user_input[:50]}...")
                return self._determine_intent_rule_based(user_input)
            
            # Validate intent is one of the expected categories
            valid_intents = [
                "wants_screening_info", "needs_resources", "school_concerns", 
                "financial_concerns", "professional_evaluation", "wants_understanding", 
                "needs_next_steps", "general_question"
            ]
            
            if intent in valid_intents:
                print(f"LLM intent determination successful: {intent}")
                return intent
            else:
                print(f"LLM returned invalid intent: {intent}")
                return self._determine_intent_rule_based(user_input)
            
        except Exception as e:
            print(f"LLM intent determination failed with error: {e}")
            return self._determine_intent_rule_based(user_input)
    
    def _determine_intent_rule_based(self, user_input: str) -> str:
        """Fallback rule-based intent determination."""
        user_input_lower = user_input.lower()
        
        # More sophisticated intent detection
        if any(word in user_input_lower for word in ["screen", "test", "check", "assess", "evaluate", "signs", "symptoms", "behaviors", "development", "milestones"]):
            return "wants_screening_info"
        elif any(word in user_input_lower for word in ["help", "therapy", "treatment", "services", "resources", "support", "intervention"]):
            return "needs_resources"
        elif any(word in user_input_lower for word in ["school", "teacher", "classroom", "iep", "504", "education", "preschool", "kindergarten"]):
            return "school_concerns"
        elif any(word in user_input_lower for word in ["afford", "cost", "insurance", "expensive", "money", "pay", "financial", "medicaid", "coverage"]):
            return "financial_concerns"
        elif any(word in user_input_lower for word in ["doctor", "pediatrician", "specialist", "evaluation", "diagnosis", "professional", "clinic", "assessment"]):
            return "professional_evaluation"
        elif any(word in user_input_lower for word in ["what is", "explain", "understand", "learn", "know more", "information", "autism", "characteristics"]):
            return "wants_understanding"
        elif any(word in user_input_lower for word in ["next", "now what", "what do i do", "where do i start", "first step", "begin", "start"]):
            return "needs_next_steps"
        elif any(word in user_input_lower for word in ["hi", "hello", "hey", "start", "begin"]):
            return "greeting"
        
        return "general_question"
    
    def _update_profile_intelligently(self, extracted_info: Dict, memory: Dict):
        """Update user profile with intelligently extracted information."""
        profile = memory["profile"]
        
        if "age_band" in extracted_info:
            profile["child_age"] = extracted_info["age_band"]
        
        if "child_name" in extracted_info:
            profile["child_name"] = extracted_info["child_name"]
        
        if "diagnosis_status" in extracted_info:
            profile["diagnosis_status"] = extracted_info["diagnosis_status"]
        
        # Store extracted info for context
        memory["extracted_info"].update(extracted_info)
    
    def _get_knowledge_based_response(self, intent: str, memory: Dict) -> str:
        """Get response from knowledge base based on intent and current path."""
        try:
            profile = memory["profile"]
            current_path = memory.get("current_path", "entry_point")
            child_name = profile.get("child_name", "your child")
            child_age = profile.get("child_age", "unknown")
            
            # Map intent to knowledge base paths
            if intent == "wants_screening_info":
                if profile.get("child_age") in ["0-3", "3-5"]:
                    entry = self.router.get_knowledge_entry("diagnosed_no.screening_options.csbs_itc_6_24m")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"Now that I know {child_name} is {child_age}, what specific behaviors are you seeing that concern you? This will help me guide you to the right screening tools."
                        return f"{response}\n\n{follow_up}"
                else:
                    entry = self.router.get_knowledge_entry("diagnosed_no.screening_options.asd_specific_screening_18_24m")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"Since {child_name} is {child_age}, have you talked to your pediatrician about your concerns yet? What did they say?"
                        return f"{response}\n\n{follow_up}"
            
            elif intent == "needs_resources":
                if profile.get("diagnosis_status") == "diagnosed_yes":
                    entry = self.router.get_knowledge_entry("diagnosed_yes.find_resources.interventions.types_settings")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"Great! Since {child_name} has a diagnosis, what type of support are you looking for most urgently - therapy, school help, or something else?"
                        return f"{response}\n\n{follow_up}"
                else:
                    entry = self.router.get_knowledge_entry("diagnosed_no.at_home_resources")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"Even while you're exploring evaluation options, what's your biggest worry right now? I can help you find resources that address your specific concerns."
                        return f"{response}\n\n{follow_up}"
            
            elif intent == "school_concerns":
                if profile.get("diagnosis_status") == "diagnosed_yes":
                    entry = self.router.get_knowledge_entry("diagnosed_yes.find_resources.school.public_school")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"School support is crucial for {child_name}. Is {child_name} currently in school? What grade are they in?"
                        return f"{response}\n\n{follow_up}"
                else:
                    entry = self.router.get_knowledge_entry("diagnosed_no.not_yet_evaluated.where_to_eval")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"What specific school challenges are you seeing with {child_name}? Are they having trouble with academics, behavior, or social interactions?"
                        return f"{response}\n\n{follow_up}"
            
            elif intent == "financial_concerns":
                if profile.get("diagnosis_status") == "diagnosed_yes":
                    entry = self.router.get_knowledge_entry("diagnosed_yes.support_affording.medicaid")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"What's your current insurance situation? Are you covered through work, Medicaid, or something else?"
                        return f"{response}\n\n{follow_up}"
                else:
                    entry = self.router.get_knowledge_entry("diagnosed_no.legal_emergency_intro")
                    if entry and "response" in entry:
                        response = entry["response"]
                        follow_up = f"What's your current insurance situation? Are you covered through work, Medicaid, or something else?"
                        return f"{response}\n\n{follow_up}"
            
            # If no specific knowledge base entry found, fall back to conversational response
            return self._get_generic_response(intent, profile)
            
        except Exception as e:
            print(f"Error accessing knowledge base: {e}")
            # Fall back to conversational response
            return self._get_generic_response(intent, memory["profile"])
    
    def _get_generic_response(self, intent: str, profile: Dict) -> str:
        """Get conversational response when knowledge base lookup fails."""
        role = profile.get("role", "unknown")
        child_age = profile.get("child_age", "unknown")
        child_name = profile.get("child_name", "your child")
        
        if intent == "greeting":
            if role == "parent_caregiver":
                if child_name != "your child":
                    if child_age in ["0-3", "3-5"]:
                        return f"Hi there! I'm so glad you're here. I can see you're looking for information about {child_name}'s development. At {child_age}, there are some really important things to watch for. What's been on your mind lately with {child_name}?"
                    else:
                        return f"Hello! Thanks for reaching out about {child_name}. I know it can feel overwhelming when you're concerned about your child's development. What specific challenges are you seeing that worry you?"
                else:
                    if child_age in ["0-3", "3-5"]:
                        return f"Hi! I'm here to help you understand your {child_age} year old's development. It's completely normal to have questions and concerns. What behaviors are you noticing that made you want to learn more?"
                    else:
                        return f"Hello! I'm here to help you with your child's development. Since they're {child_age}, what specific challenges are you seeing at school or home that concern you?"
            else:
                return "Hi there! I'm here to help you understand autism and find the support you need. What brought you here today?"
        
        elif intent == "wants_screening_info":
            if role == "parent_caregiver" and child_age in ["0-3", "3-5"]:
                return f"For {child_name} who is {child_age}, I'd definitely recommend starting with the CSBS-DP Infant-Toddler Checklist. It's designed specifically for little ones and focuses on early communication and social skills. But first, tell me - what specific behaviors are you seeing that concern you? This will help me guide you to the right tools."
            else:
                return f"Since {child_name} is {child_age}, the screening approach will be different. Have you talked to your pediatrician about your concerns yet? What did they say?"
        
        elif intent == "needs_resources":
            if profile.get("diagnosis_status") == "diagnosed_yes":
                return f"Great! Since {child_name} has a diagnosis, there are several types of support available. What type of help are you looking for most urgently - therapy services, school support, or financial assistance?"
            else:
                return f"Even while you're exploring evaluation options, there are helpful resources you can use. What's your biggest worry right now? I can help you find resources that address your specific concerns."
        
        elif intent == "school_concerns":
            if profile.get("diagnosis_status") == "diagnosed_yes":
                return f"School support is crucial for {child_name}. Is {child_name} currently in school? What grade are they in, and what specific challenges are you seeing?"
            else:
                return f"Even without a diagnosis yet, you can still request school evaluation. What specific school challenges are you seeing? Are they having trouble with academics, behavior, or social interactions?"
        
        elif intent == "financial_concerns":
            return f"I understand financial concerns can be stressful. What's your current insurance situation? Are you covered through work, Medicaid, or something else? This will help me guide you to the right resources."
        
        elif intent == "professional_evaluation":
            return f"Getting a professional evaluation is an important step. Where are you in this process? Have you started looking for providers yet, or do you need help finding qualified evaluators in your area?"
        
        elif intent == "wants_understanding":
            return f"I'd be happy to help you understand autism better. What specific aspect would you like to learn about? The signs and symptoms, the diagnosis process, or how autism might present differently in {child_name}?"
        
        elif intent == "needs_next_steps":
            return f"Let's figure out your next steps together. What feels like the most urgent priority for you right now? We can tackle one thing at a time to make this manageable."
        
        else:
            # For general questions, ask something to understand their situation better
            if role == "parent_caregiver":
                if child_name != "your child":
                    return f"Thank you for sharing about {child_name}. I want to make sure I give you the most relevant information. What specific question or concern brought you here today?"
                else:
                    return "I want to understand your situation better so I can provide the most relevant help. What specific question or concern brought you here today?"
            else:
                return "What brought you here today? What would be most helpful for me to know about your situation?"
    
    def _update_conversation_path(self, intent: str, memory: Dict):
        """Update the conversation path based on user intent."""
        profile = memory["profile"]
        
        # Map intent to conversation paths
        if intent == "wants_screening_info":
            if profile.get("child_age") in ["0-3", "3-5"]:
                memory["current_path"] = "diagnosed_no.screening_options"
            else:
                memory["current_path"] = "diagnosed_no.screening_options"
        elif intent == "needs_resources":
            if profile.get("diagnosis_status") == "diagnosed_yes":
                memory["current_path"] = "diagnosed_yes.find_resources"
            else:
                memory["current_path"] = "diagnosed_no.at_home_resources"
        elif intent == "school_concerns":
            if profile.get("diagnosis_status") == "diagnosed_yes":
                memory["current_path"] = "diagnosed_yes.find_resources.school"
            else:
                memory["current_path"] = "diagnosed_no.not_yet_evaluated"
        
        # Mark topic as covered
        if intent not in memory.get("topics_covered", []):
            memory["topics_covered"].append(intent)
    
    def _get_next_steps(self, intent: str, memory: Dict) -> List[str]:
        """Get next steps based on current conversation state."""
        profile = memory["profile"]
        current_path = memory.get("current_path", "")
        
        if intent == "wants_screening_info":
            if profile.get("child_age") in ["0-3", "3-5"]:
                return [
                    "Download and complete the CSBS-DP Infant-Toddler Checklist",
                    "Schedule a discussion with your pediatrician about results",
                    "Keep a record of specific behaviors you observe"
                ]
            else:
                return [
                    "Talk to your pediatrician about autism-specific screening",
                    "Request a referral for comprehensive evaluation",
                    "Gather examples of concerning behaviors"
                ]
        elif intent == "needs_resources":
            return [
                "Research local therapy providers and their specialties",
                "Check with your insurance about coverage for services",
                "Connect with local autism support groups"
            ]
        elif intent == "school_concerns":
            return [
                "Request a school evaluation in writing",
                "Learn about IEP vs 504 plan differences",
                "Prepare documentation of your concerns"
            ]
        
        return ["Take some time to process this information", "Write down any questions that come up"]
    
    def _get_relevant_resources(self, intent: str, profile: Dict) -> List[Dict]:
        """Get relevant resources based on intent."""
        return [
            {
                "name": "Autism Navigator",
                "description": "Evidence-based video tools and educational resources for families",
                "url": "https://autismnavigator.com/printables/",
                "type": "Educational Resource"
            },
            {
                "name": "CDC Early Development",
                "description": "Information about developmental milestones and screening",
                "url": "https://www.cdc.gov/ncbddd/actearly/index.html",
                "type": "Government Resource"
            },
            {
                "name": "CSBS-DP Checklist",
                "description": "Early communication and social screening tool for toddlers",
                "url": "https://brookespublishing.com/wp-content/uploads/2012/06/csbs-dp-itc.pdf",
                "type": "Screening Tool"
            }
        ]
    
    def get_conversation_summary(self, conversation_id: str) -> Dict:
        """Get a comprehensive summary of the conversation."""
        if conversation_id not in self.conversation_memory:
            return {"error": "Conversation not found"}
        
        memory = self.conversation_memory[conversation_id]
        profile = memory["profile"]
        
        # Build comprehensive summary
        summary = {
            "conversation_id": conversation_id,
            "family_information": {
                "parent_name": profile.get("parent_name", "Not specified"),
                "role": profile.get("role", "unknown"),
                "child_name": profile.get("child_name", "Not specified"),
                "child_age": profile.get("child_age", "unknown"),
                "child_gender": profile.get("child_gender", "Not specified"),
                "diagnosis_status": profile.get("diagnosis_status", "unknown")
            },
            "specific_details": {
                "concerns_mentioned": profile.get("specific_concerns", []),
                "professionals_mentioned": profile.get("professionals_mentioned", []),
                "challenges_strengths": profile.get("challenges_strengths", [])
            },
            "conversation_progress": {
                "current_step": memory.get("current_path", "entry_point").replace("_", " ").title(),
                "completed_steps": memory.get("topics_covered", []),
                "conversation_length": len(memory["conversation_history"]),
                "emotional_journey": memory.get("emotional_state", "seeking_information")
            },
            "recommendations": {
                "next_steps": self._get_next_steps("general_question", memory),
                "helpful_resources": self._get_relevant_resources("general_question", profile)
            },
            "supportive_message": "Remember, you're doing an amazing job seeking out information and support. Every step you take is helping create a better path forward."
        }
        
        # Add conversation highlights if available
        if memory.get("conversation_history"):
            summary["conversation_highlights"] = []
            for entry in memory["conversation_history"][-5:]:  # Last 5 exchanges
                if entry["role"] == "user":
                    summary["conversation_highlights"].append({
                        "type": "user_concern",
                        "content": entry["content"][:100] + "..." if len(entry["content"]) > 100 else entry["content"],
                        "intent": entry.get("intent", "unknown")
                    })
        
        return summary
