"""
Process Admin Documents for Autism Support App
Processes expert documents uploaded by admins for ingestion into the shared knowledge base.
"""

import os
import json
from pathlib import Path
from typing import List, Dict
import PyPDF2
import docx

def process_admin_documents(upload_dir: str) -> int:
    """
    Process admin documents and prepare them for ingestion.
    
    Args:
        upload_dir: Path to directory containing uploaded documents
        
    Returns:
        Number of documents processed
    """
    upload_path = Path(upload_dir)
    if not upload_path.exists():
        print(f"❌ Upload directory not found: {upload_dir}")
        return 0
    
    processed_count = 0
    documents = []
    
    # Process each file in the upload directory
    for file_path in upload_path.glob("*"):
        if file_path.is_file():
            try:
                content = extract_text_from_file(file_path)
                if content:
                    # Create document entry
                    doc_entry = {
                        "filename": file_path.name,
                        "content": content,
                        "type": "admin_document",
                        "source": "admin_upload",
                        "metadata": {
                            "file_size": file_path.stat().st_size,
                            "file_type": file_path.suffix.lower(),
                            "upload_timestamp": str(file_path.stat().st_mtime)
                        }
                    }
                    documents.append(doc_entry)
                    processed_count += 1
                    print(f"✅ Processed: {file_path.name}")
                else:
                    print(f"⚠️ No content extracted from: {file_path.name}")
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
    
    # Save processed documents to a temporary file for ingestion
    if documents:
        temp_file = Path("data/processed_admin_docs.json")
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(documents)} processed documents to {temp_file}")
    
    return processed_count

def extract_text_from_file(file_path: Path) -> str:
    """
    Extract text content from various file types.
    
    Args:
        file_path: Path to the file to extract text from
        
    Returns:
        Extracted text content
    """
    file_extension = file_path.suffix.lower()
    
    try:
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension == '.txt':
            return extract_text_from_txt(file_path)
        elif file_extension in ['.docx', '.doc']:
            return extract_text_from_docx(file_path)
        else:
            print(f"⚠️ Unsupported file type: {file_extension}")
            return ""
    except Exception as e:
        print(f"❌ Error extracting text from {file_path.name}: {e}")
        return ""

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        return ""

def extract_text_from_txt(file_path: Path) -> str:
    """Extract text from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read().strip()
        except Exception as e:
            print(f"❌ TXT extraction error: {e}")
            return ""
    except Exception as e:
        print(f"❌ TXT extraction error: {e}")
        return ""

def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"❌ DOCX extraction error: {e}")
        return ""

def get_processed_documents() -> List[Dict]:
    """
    Get the list of processed admin documents.
    
    Returns:
        List of processed document dictionaries
    """
    temp_file = Path("data/processed_admin_docs.json")
    if not temp_file.exists():
        return []
    
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading processed documents: {e}")
        return []

if __name__ == "__main__":
    # Test processing
    upload_dir = "data/admin_uploaded_docs"
    count = process_admin_documents(upload_dir)
    print(f"Processed {count} documents")
