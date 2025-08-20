"""
Updated Ingest Script for New Knowledge Base Structure
Converts the new structured_mongo.json format to MongoDB-compatible flat format.
"""

import json
import os
from pymongo import MongoClient
from typing import Dict, List, Any

# Paths
DIR = os.path.dirname(__file__)
STRUCTURED_JSON_PATH = os.path.join(DIR, "structured_mongo.json")
FLAT_JSON_PATH = os.path.join(DIR, "flat_knowledge.json")

# MongoDB config
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "autism_ai"
COLLECTION_NAME = "knowledge"

def flatten_structure(data: Dict, parent_path: str = "") -> List[Dict]:
    """
    Flatten the nested structure into a list of MongoDB documents.
    
    Args:
        data: The nested dictionary structure
        parent_path: The current path being processed
        
    Returns:
        List of flattened documents for MongoDB
    """
    flat_docs = []
    
    for key, value in data.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        
        if isinstance(value, dict):
            # Check if this is a leaf node (has response, label, tone)
            if "response" in value and "label" in value:
                # This is a content node
                doc = {
                    "context_path": current_path,
                    "label": value.get("label", key),
                    "response": value.get("response", ""),
                    "tone": value.get("tone", "neutral"),
                    "source": value.get("source"),
                    "type": "content"
                }
                
                # Add additional fields if they exist
                if "scoring_support" in value:
                    doc["scoring_support"] = value["scoring_support"]
                if "options" in value:
                    doc["options"] = value["options"]
                if "routes" in value:
                    doc["routes"] = value["routes"]
                if "branches" in value:
                    doc["branches"] = value["branches"]
                if "sources" in value:
                    doc["sources"] = value["sources"]
                
                flat_docs.append(doc)
            else:
                # This is a container node, recurse deeper
                flat_docs.extend(flatten_structure(value, current_path))
        else:
            # This is a simple value (string, number, etc.)
            doc = {
                "context_path": current_path,
                "label": key,
                "value": value,
                "type": "metadata"
            }
            flat_docs.append(doc)
    
    return flat_docs

def build_enhanced_flat_structure() -> List[Dict]:
    """
    Build enhanced flat structure with additional fields for conversational routing.
    
    Returns:
        List of enhanced documents for MongoDB
    """
    # Load the structured data
    with open(STRUCTURED_JSON_PATH, 'r', encoding='utf-8') as f:
        structured_data = json.load(f)
    
    # Get router configuration
    router_config = structured_data.get("router", {})
    safety_rules = router_config.get("safety_rules", {})
    
    # Flatten the structure
    flat_docs = flatten_structure(structured_data)
    
    # Add router configuration as a special document
    flat_docs.append({
        "context_path": "router",
        "label": "Router Configuration",
        "type": "router_config",
        "role_gate": router_config.get("role_gate", []),
        "status_gate": router_config.get("status_gate", []),
        "age_bands": router_config.get("age_bands", []),
        "jurisdiction_default": router_config.get("jurisdiction_default", "GA"),
        "safety_rules": safety_rules
    })
    
    # Add global info as separate documents
    globals_data = structured_data.get("globals", {})
    for section_key, section_data in globals_data.items():
        if isinstance(section_data, dict):
            for item_key, item_data in section_data.items():
                if isinstance(item_data, dict) and "response" in item_data:
                    flat_docs.append({
                        "context_path": f"globals.{section_key}.{item_key}",
                        "label": item_data.get("label", item_key),
                        "response": item_data.get("response", ""),
                        "tone": item_data.get("tone", "neutral"),
                        "source": item_data.get("source"),
                        "type": "global_content",
                        "section": section_key
                    })
    
    return flat_docs

def ingest_csv_to_mongo():
    """
    Ingest CSV data into MongoDB.
    This function is called by the edit_csv.py UI to update MongoDB from CSV changes.
    """
    try:
        import pandas as pd
        
        # Load CSV data
        csv_path = os.path.join(DIR, "knowledge.csv")
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {csv_path}")
            return False
        
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"📊 Loaded {len(df)} rows from CSV")
        
        # Clean data - remove rows without context_path or response
        df = df.dropna(subset=["context_path", "response"])
        print(f"🧹 Cleaned to {len(df)} valid rows")
        
        # Convert to MongoDB documents
        mongo_docs = []
        for _, row in df.iterrows():
            doc = {
                "context_path": row["context_path"],
                "label": row.get("label", ""),
                "response": row["response"],
                "tone": row.get("tone", "neutral"),
                "source": row.get("source", ""),
                "type": "content"
            }
            mongo_docs.append(doc)
        
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Clear existing content (but keep router config)
        collection.delete_many({"type": "content"})
        print("🗑️  Cleared existing content documents")
        
        # Insert new content
        if mongo_docs:
            result = collection.insert_many(mongo_docs)
            print(f"✅ Inserted {len(result.inserted_ids)} content documents into MongoDB")
        
        # Create indexes
        collection.create_index("context_path")
        collection.create_index("type")
        collection.create_index("tone")
        
        client.close()
        print("🎉 CSV ingestion completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error ingesting CSV: {e}")
        return False

def ingest_to_mongo():
    """
    Ingest the new structure into MongoDB.
    """
    try:
        # Build the enhanced flat structure
        flat_docs = build_enhanced_flat_structure()
        
        # Save to JSON file
        with open(FLAT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(flat_docs, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Generated {len(flat_docs)} documents")
        print(f"📁 Saved to: {FLAT_JSON_PATH}")

        # Upload to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Clear existing data
        collection.delete_many({})
        print("🗑️  Cleared existing MongoDB collection")
        
        # Insert new data
        if flat_docs:
            result = collection.insert_many(flat_docs)
            print(f"✅ Inserted {len(result.inserted_ids)} documents into MongoDB")
            
            # Create indexes for better performance
            collection.create_index("context_path")
            collection.create_index("type")
            collection.create_index("tone")
            print("🔍 Created database indexes")
        
        # Show sample documents
        print("\n📋 Sample documents:")
        sample_docs = list(collection.find().limit(3))
        for i, doc in enumerate(sample_docs):
            print(f"  {i+1}. {doc.get('context_path', 'N/A')} - {doc.get('label', 'N/A')}")
        
        client.close()
        print("\n🎉 MongoDB update completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

def create_conversation_indexes():
    """
    Create additional indexes for conversational features.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Create indexes for conversational routing
        collection.create_index([("type", 1), ("context_path", 1)])
        collection.create_index([("tone", 1)])
        collection.create_index([("section", 1)])
        
        print("🔍 Created conversation-specific indexes")
        client.close()
        
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")

def ingest_csv_to_mongo():
    """
    Ingest CSV data into MongoDB.
    This function is called by the edit_csv.py UI to update MongoDB from CSV changes.
    """
    try:
        import pandas as pd
        
        # Load CSV data
        csv_path = os.path.join(DIR, "knowledge.csv")
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {csv_path}")
            return False
        
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"📊 Loaded {len(df)} rows from CSV")
        
        # Clean data - remove rows without context_path or response
        df = df.dropna(subset=["context_path", "response"])
        print(f"🧹 Cleaned to {len(df)} valid rows")
        
        # Convert to MongoDB documents
        mongo_docs = []
        for _, row in df.iterrows():
            doc = {
                "context_path": row["context_path"],
                "label": row.get("label", ""),
                "response": row["response"],
                "tone": row.get("tone", "neutral"),
                "source": row.get("source", ""),
                "type": "content"
            }
            mongo_docs.append(doc)
        
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Clear existing content (but keep router config)
        collection.delete_many({"type": "content"})
        print("🗑️  Cleared existing content documents")
        
        # Insert new content
        if mongo_docs:
            result = collection.insert_many(mongo_docs)
            print(f"✅ Inserted {len(result.inserted_ids)} content documents into MongoDB")
        
        # Create indexes
        collection.create_index("context_path")
        collection.create_index("type")
        collection.create_index("tone")
        
        client.close()
        print("🎉 CSV ingestion completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error ingesting CSV: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting new knowledge base ingestion...")
    ingest_to_mongo()
    create_conversation_indexes()
    print("\n✨ All done! The new conversational system is ready to use.")
