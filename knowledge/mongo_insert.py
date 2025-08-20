"""
Enhanced MongoDB Insert Script
Updates MongoDB with knowledge base data from flat_knowledge.json
"""

from pymongo import MongoClient
import json
import os
import sys

# Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "autism_ai"
COLLECTION_NAME = "knowledge"

def load_flat_knowledge():
    """Load flat knowledge data from JSON file."""
    try:
        json_path = os.path.join("knowledge", "flat_knowledge.json")
        if not os.path.exists(json_path):
            print(f"❌ File not found: {json_path}")
            print("💡 Run 'python knowledge/ingest.py' first to generate this file")
            return None
        
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📊 Loaded {len(data)} records from {json_path}")
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {json_path}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None

def update_mongodb(data):
    """Update MongoDB with new knowledge data."""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        print(f"🔌 Connected to MongoDB: {MONGO_URI}")
        
        # Backup existing data count
        existing_count = collection.count_documents({})
        print(f"📋 Existing documents in database: {existing_count}")
        
        # Clear existing data
        result = collection.delete_many({})
        print(f"🗑️  Cleared {result.deleted_count} existing documents")
        
        # Insert new data
        if data:
            result = collection.insert_many(data)
            print(f"✅ Inserted {len(result.inserted_ids)} new documents")
            
            # Create indexes for better performance
            collection.create_index("context_path")
            collection.create_index("type")
            collection.create_index("tone")
            print("🔍 Created database indexes")
        
        # Verify insertion
        final_count = collection.count_documents({})
        print(f"📊 Final document count: {final_count}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        return False

def main():
    """Main execution function."""
    print("🚀 Starting MongoDB knowledge base update...")
    print("=" * 50)
    
    # Load data
    data = load_flat_knowledge()
    if not data:
        print("❌ Failed to load knowledge data")
        sys.exit(1)
    
    # Update MongoDB
    if update_mongodb(data):
        print("\n🎉 MongoDB update completed successfully!")
        print(f"📊 Total documents: {len(data)}")
    else:
        print("\n❌ MongoDB update failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
