"""
Patient Document Parsing Utilities
Breaks circular import between app.py and ResponseSynthesisEngine
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import sys
import os

# Add the project root to the path to import vector store functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_vector_store_documents(user_id: str = "default") -> List[Dict]:
    """Get documents from vector store for a specific user."""
    try:
        from rag.ingest_user_docs import get_user_documents
        
        # Use the existing function that actually works
        raw_docs = get_user_documents(user_id)
        
        # Transform the raw documents into the expected format
        documents = {}
        for doc in raw_docs:
            filename = doc.get("filename", "Unknown")
            
            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "chunks": doc.get("chunks", 1),
                    "content_samples": doc.get("content_samples", []),
                    "file_size": doc.get("file_size", 0),
                    "upload_timestamp": doc.get("upload_timestamp", "Unknown")
                }
        
        return list(documents.values())
        
    except Exception as e:
        print(f"❌ Error getting vector store documents: {e}")
        return []

def parse_patient_documents(user_id: str = "default") -> dict:
    """Parse patient documents using LLM for comprehensive intelligent information extraction."""
    try:
        # Get full document content for LLM processing
        from rag.ingest_user_docs import get_full_document_content
        
        all_content = get_full_document_content(user_id)
        if not all_content.strip():
            print(f"⚠️ No document content found for user: {user_id}")
            return {}
        
        print(f"🔍 Processing {len(all_content)} characters of document content")
        print(f"🔍 Document content preview: {all_content[:200]}...")
        
        # Use LLM to intelligently extract comprehensive patient information
        patient_info = extract_patient_info_with_llm(all_content)
        
        # Calculate current age from DOB if available
        if patient_info.get("date_of_birth"):
            current_age = calculate_current_age(patient_info["date_of_birth"])
            if current_age:
                patient_info["age"] = current_age
                patient_info["current_age"] = current_age
        
        # Add document metadata
        patient_info["document_sources"] = [{"user_id": user_id, "content_length": len(all_content)}]
        patient_info["last_updated"] = datetime.now().isoformat()
        
        print(f"✅ Successfully parsed patient documents for {user_id}")
        print(f"🔍 Final patient info: {patient_info}")
        return patient_info
        
    except Exception as e:
        print(f"❌ Error parsing patient documents: {e}")
        import traceback
        traceback.print_exc()
        return {}

def extract_patient_info_with_llm(document_content: str) -> dict:
    """Use LLM to intelligently extract comprehensive patient information from documents."""
    try:
        import streamlit as st
        
        # Get API key from Streamlit secrets
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key found in Streamlit secrets")
            return {}
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print(f"🔍 Sending {len(document_content)} characters to LLM for patient info extraction")
        
        # Create a comprehensive prompt for LLM extraction
        prompt = f"""You are a medical document analysis expert. Extract comprehensive patient information from the following medical documents.

Please extract and return ONLY a valid JSON object with the following structure (include all fields, use null for missing information):

{{
    "name": "Full patient name",
    "date_of_birth": "MM/DD/YYYY format if found",
    "age": null,
    "gender": "Male/Female/Other if mentioned",
    "parents": {{
        "mother": "Mother's name if mentioned",
        "father": "Father's name if mentioned",
        "guardians": ["list", "of", "other", "guardians"]
    }},
    "siblings": ["list", "of", "siblings", "if", "mentioned"],
    "family_structure": "Description of family structure if mentioned",
    "school": "School name if mentioned",
    "grade_level": "Grade or educational level",
    "iep_status": "IEP status if mentioned",
    "educational_needs": ["list", "of", "educational", "needs"],
    "teachers": ["list", "of", "teachers", "or", "educators"],
    "address": "Address if mentioned",
    "insurance": "Insurance information if mentioned",
    "contact_info": {{
        "phone": "Phone number if mentioned",
        "email": "Email if mentioned"
    }},
    "diagnosis": "Primary diagnosis",
    "medications": ["list", "of", "medications"],
    "providers": ["list", "of", "healthcare", "providers"],
    "medical_history": ["list", "of", "relevant", "medical", "history"],
    "evaluation_dates": ["list", "of", "evaluation", "dates"],
    "assessment_scores": {{
        "test_name": "score or result"
    }},
    "key_findings": ["list", "of", "key", "clinical", "findings"],
    "recommendations": ["list", "of", "recommendations"],
    "treatment_goals": ["list", "of", "treatment", "goals"],
    "progress_areas": ["list", "of", "areas", "showing", "progress"],
    "challenges": ["list", "of", "current", "challenges"],
    "therapists": ["list", "of", "therapists", "or", "specialists"],
    "services": ["list", "of", "services", "or", "interventions"],
    "resources": ["list", "of", "recommended", "resources"]
}}

Document content:
{document_content[:6000]}

Return ONLY the JSON object, no other text or explanation."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical document analysis expert. Extract patient information accurately and return only valid JSON. Be thorough and comprehensive in your extraction."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        # Parse the JSON response
        try:
            extracted_info = json.loads(response.choices[0].message.content.strip())
            print(f"✅ LLM extracted comprehensive patient information: {extracted_info.get('name', 'NO_NAME')} ({extracted_info.get('age', 'NO_AGE')})")
            return extracted_info
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response.choices[0].message.content[:500]}...")
            return {}
        
    except Exception as e:
        print(f"❌ Error in LLM extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}

def calculate_current_age(date_of_birth: str) -> Optional[int]:
    """Calculate current age from date of birth."""
    try:
        # Try different date formats
        date_formats = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]
        
        dob = None
        for fmt in date_formats:
            try:
                dob = datetime.strptime(date_of_birth, fmt)
                break
            except ValueError:
                continue
        
        if not dob:
            print(f"❌ Could not parse date of birth: {date_of_birth}")
            return None
        
        today = datetime.now()
        
        # Calculate age
        age = today.year - dob.year
        if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
            age -= 1
        
        print(f"✅ Calculated current age: {age} years old")
        return age
        
    except Exception as e:
        print(f"❌ Error calculating age: {e}")
        return None

def create_patient_summary(patient_info: dict) -> str:
    """Create a human-readable summary of patient information."""
    if not patient_info:
        return "No patient information available."
    
    summary_parts = []
    
    if patient_info.get("name"):
        summary_parts.append(f"**Patient Name:** {patient_info['name']}")
    
    if patient_info.get("age"):
        summary_parts.append(f"**Age:** {patient_info['age']} years old")
    
    if patient_info.get("diagnosis"):
        summary_parts.append(f"**Diagnosis:** {patient_info['diagnosis']}")
    
    if patient_info.get("concerns"):
        concerns_text = ", ".join(patient_info["concerns"][:3])  # Limit to 3 concerns
        summary_parts.append(f"**Key Concerns:** {concerns_text}")
    
    if patient_info.get("key_findings"):
        findings_text = "; ".join(patient_info["key_findings"][:2])  # Limit to 2 findings
        summary_parts.append(f"**Key Findings:** {findings_text}")
    
    if patient_info.get("recommendations"):
        recs_text = "; ".join(patient_info["recommendations"][:2])  # Limit to 2 recommendations
        summary_parts.append(f"**Recommendations:** {recs_text}")
    
    return "\n".join(summary_parts)

def enhance_user_query_with_patient_context(user_query: str, patient_info: dict) -> str:
    """Enhance user query with patient-specific context."""
    if not patient_info:
        return user_query
    
    enhanced_parts = [user_query]
    
    if patient_info.get("name"):
        enhanced_parts.append(f"Please focus on {patient_info['name']}'s specific situation.")
    
    if patient_info.get("diagnosis"):
        enhanced_parts.append(f"Reference the diagnosis: {patient_info['diagnosis']}")
    
    if patient_info.get("concerns"):
        concerns = ", ".join(patient_info["concerns"][:2])
        enhanced_parts.append(f"Address these concerns: {concerns}")
    
    return " ".join(enhanced_parts)
