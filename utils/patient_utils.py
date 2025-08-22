"""
Patient Document Parsing Utilities
Breaks circular import between app.py and ResponseSynthesisEngine
"""

import re
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
    """Parse patient documents to extract key information."""
    try:
        vector_docs = get_vector_store_documents(user_id)
        if not vector_docs:
            return {}
        
        patient_info = {
            "name": None,
            "age": None,
            "diagnosis": None,
            "concerns": [],
            "evaluation_date": None,
            "key_findings": [],
            "recommendations": []
        }
        
        # Extract information from each document
        for doc in vector_docs:
            filename = doc.get("filename", "").lower()
            
            # Look for diagnosis/evaluation documents
            if any(keyword in filename for keyword in ["diagnosis", "evaluation", "assessment", "report"]):
                # Extract key information from content samples
                for sample in doc.get("content_samples", []):
                    content = sample.lower()
                    
                    # Extract name
                    if not patient_info["name"]:
                        name_patterns = [
                            r"patient name[:\s]+([a-zA-Z\s]+)",
                            r"name[:\s]+([a-zA-Z\s]+)",
                            r"([a-zA-Z]+)\s+[a-zA-Z]+\s+[a-zA-Z]+"  # First Middle Last pattern
                        ]
                        for pattern in name_patterns:
                            match = re.search(pattern, content)
                            if match:
                                patient_info["name"] = match.group(1).strip().title()
                                break
                    
                    # Extract age
                    if not patient_info["age"]:
                        age_patterns = [
                            r"(\d+)\s*(?:year|yr)s?\s*old",
                            r"age[:\s]+(\d+)",
                            r"(\d+)\s*(?:years?|yrs?)"
                        ]
                        for pattern in age_patterns:
                            match = re.search(pattern, content)
                            if match:
                                patient_info["age"] = int(match.group(1))
                                break
                    
                    # Extract diagnosis
                    if not patient_info["diagnosis"]:
                        if "autism" in content or "asd" in content:
                            patient_info["diagnosis"] = "Autism Spectrum Disorder"
                        elif "diagnosis" in content:
                            # Look for diagnosis section
                            diagnosis_section = content.split("diagnosis")[-1][:500]
                            patient_info["diagnosis"] = diagnosis_section.strip()
                    
                    # Extract concerns
                    concern_keywords = ["concern", "difficulty", "challenge", "issue", "problem"]
                    for keyword in concern_keywords:
                        if keyword in content and keyword not in patient_info["concerns"]:
                            patient_info["concerns"].append(keyword)
                    
                    # Extract key findings
                    if "finding" in content or "result" in content:
                        findings_section = content.split("finding")[-1][:300]
                        if findings_section.strip():
                            patient_info["key_findings"].append(findings_section.strip())
        
        return patient_info
        
    except Exception as e:
        print(f"❌ Error parsing patient documents: {e}")
        return {}

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
