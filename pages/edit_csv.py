import streamlit as st
import pandas as pd
import os

from knowledge.ingest import ingest_csv_to_mongo

# === Setup ===
st.set_page_config(page_title="Manage Knowledge", layout="wide")
st.title("🧠 Manage Structured Knowledge Base")

csv_path = "knowledge/knowledge.csv"
required_columns = ["context_path", "label", "response", "tone", "source"]

# === Load CSV ===
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"Missing columns in CSV: {missing_cols}")
        st.stop()
else:
    df = pd.DataFrame(columns=required_columns)
    st.warning("CSV not found. A new one will be created after saving.")

# === Instructions ===
st.markdown("""
Use the table below to edit or add new structured guidance.  
- **context_path**: Full path (e.g. `diagnosed_yes > support_affording > medicaid`)  
- **label**: Optional UI label  
- **response**: Core content used in replies  
- **tone**: Style of voice (e.g., `supportive`, `informative`)  
- **source**: Optional links or attribution  
""")

# === Display + Edit Table ===
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "tone": st.column_config.SelectboxColumn("tone", options=["supportive", "informative", "friendly", "neutral"], required=False)
    }
)

# === Save Changes ===
if st.button("💾 Save & Sync to MongoDB"):
    # Drop blank rows (no context_path or response)
    cleaned_df = edited_df.dropna(subset=["context_path", "response"])
    
    # Save back to CSV
    cleaned_df.to_csv(csv_path, index=False)
    st.success("✅ CSV saved.")

    # Trigger ingestion
    try:
        ingest_csv_to_mongo()
        st.info("📦 MongoDB updated with new entries.")
    except Exception as e:
        st.error(f"❌ Error updating MongoDB: {e}")
