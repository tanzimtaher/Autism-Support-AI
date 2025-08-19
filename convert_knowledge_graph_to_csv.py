import json
import csv

def flatten_json_tree(json_tree, parent_path=""):
    flattened = []
    
    for key, value in json_tree.items():
        current_path = f"{parent_path} > {key}" if parent_path else key
        
        if isinstance(value, dict):
            if "response" in value:
                # Leaf node with content
                row = {
                    "context_path": current_path,
                    "label": value.get("label", ""),
                    "response": value["response"],
                    "tone": value.get("tone", ""),
                    "source": value.get("source", "")
                }
                flattened.append(row)
            else:
                # Recurse deeper
                flattened.extend(flatten_json_tree(value, current_path))
    return flattened

def write_to_csv(data, output_file):
    fieldnames = ["context_path", "label", "response", "tone", "source"]
    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

# --- Run the script ---
input_file = "knowledge.json"
output_file = "knowledge.csv"

with open(input_file, 'r', encoding='utf-8') as f:
    json_tree = json.load(f)

flat_data = flatten_json_tree(json_tree)
write_to_csv(flat_data, output_file)

print(f"Flattened data written to {output_file}")
