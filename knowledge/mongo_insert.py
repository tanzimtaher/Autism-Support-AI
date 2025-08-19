from pymongo import MongoClient
import json
import os

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "autism_ai"
COLLECTION_NAME = "knowledge"

# Load flat knowledge entries
with open(os.path.join("knowledge", "flat_knowledge.json"), encoding="utf-8") as f:
    data = json.load(f)

# Connect and insert
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Clean existing data (optional, caution)
collection.delete_many({})

# Insert new
collection.insert_many(data)

print(f"✅ Inserted {len(data)} records into {DB_NAME}.{COLLECTION_NAME}")
