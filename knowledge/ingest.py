import csv
import json
import os
from pymongo import MongoClient

# Paths
DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(DIR, "knowledge.csv")
TREE_JSON_PATH = os.path.join(DIR, "structured_mongo.json")
FLAT_JSON_PATH = os.path.join(DIR, "flat_knowledge.json")

# MongoDB config
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "autism_support"
COLLECTION_NAME = "knowledge"

# === Helper to nest keys dynamically ===
def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key.strip(), {})
    dic[keys[-1].strip()] = value

# === Build structured tree (for tree-UI logic) ===
def build_structured_tree(csv_path):
    tree = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["context_path"].strip() or not row["response"].strip():
                continue
            path = row["context_path"].split(">")
            entry = {
                "label": row["label"].strip() if row["label"] else path[-1].strip().replace("_", " ").capitalize(),
                "response": row["response"].strip(),
                "tone": row["tone"].strip(),
                "source": row["source"].strip() if row["source"] else None
            }
            nested_set(tree, path, entry)
    return tree

# === Build flat list (for MongoDB and querying) ===
def build_flat_list(csv_path):
    flat_list = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["context_path"].strip() or not row["response"].strip():
                continue
            flat_list.append({
                "context_path": row["context_path"].strip(),
                "label": row["label"].strip() if row["label"] else row["context_path"].split(">")[-1].strip(),
                "response": row["response"].strip(),
                "tone": row["tone"].strip(),
                "source": row["source"].strip() if row["source"] else None
            })
    return flat_list

# === Export and insert ===
def ingest_csv_to_mongo():
    # Process
    structured = build_structured_tree(CSV_PATH)
    flat = build_flat_list(CSV_PATH)

    # Save to JSON
    with open(TREE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)

    with open(FLAT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(flat, f, indent=2, ensure_ascii=False)

    # Upload to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    collection.delete_many({})
    if flat:
        collection.insert_many(flat)

    print("✅ CSV ingested: JSON written + MongoDB updated")

# === CLI Mode ===
if __name__ == "__main__":
    ingest_csv_to_mongo()
