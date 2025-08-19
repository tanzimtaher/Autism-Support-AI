import streamlit as st
import openai, pymongo
from pymongo import MongoClient
from rag.query_engine import query_index

# ---- keys & db
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
mongo = MongoClient("mongodb://localhost:27017/")["autism_ai"]["knowledge"]

# ---- session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "initial_response_shown" not in st.session_state:
    st.session_state.initial_response_shown = False
if "context_path" not in st.session_state:
    st.session_state.context_path = None

# ---- sidebar user profile
with st.sidebar:
    st.markdown("### About you")
    state = st.selectbox("State", ["GA", "CA", "NY", "TX", "Other"])
    income = st.selectbox("Income", ["<30k", "30-60k", "60-100k", ">100k"])
    age = st.slider("Child age", 0, 18, 6)
    st.session_state.profile_str = f"State:{state}, Income:{income}, ChildAge:{age}"

# ---- knowledge tree selection
st.title("Autism Support Assistant")
st.subheader("Step 1: Select a support topic")

diagnosed = st.radio("Has your child been diagnosed with autism?", ["Yes", "No"])
base_path = "diagnosed_yes" if diagnosed == "Yes" else "diagnosed_no"

topics = mongo.find({"context_path": {"$regex": f"^{base_path}"}})
categories = sorted({doc["context_path"].split(" > ")[1] for doc in topics})

category = st.selectbox("Select a category", categories)

subtopics = mongo.find({"context_path": {"$regex": f"^{base_path} > {category}"}})
subkeys = sorted({">".join(doc["context_path"].split(" > ")[2:])
                  for doc in subtopics if len(doc["context_path"].split(" > ")) > 2})
subcategory = st.selectbox("Choose a specific topic", ["(none)"] + subkeys)

# Final context path
context_path = f"{base_path} > {category}"
if subcategory and subcategory != "(none)":
    context_path += f" > {subcategory}"
st.session_state.context_path = context_path

# ---- helper functions
def fetch_mongo(path): 
    return mongo.find_one({"context_path": path})

def llm_synthesize(user_msg, base_resp, rag_chunks, tone):
    sys = f"""You are a concise, empathetic autism-support assistant. 
User profile: {st.session_state.profile_str}
Tone: {tone}
"""
    if base_resp:
        sys += f"\nStructured guidance:\n{base_resp}"
    if rag_chunks:
        sys += "\nRelevant document insights:"
        for i, chunk in enumerate(rag_chunks, 1):
            sys += f"\n[{i}] {chunk['text'][:250]}... (source: {chunk['source']})"

    messages = [
        {"role": "system", "content": sys.strip()},
        {"role": "user", "content": user_msg}
    ]
    return client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, temperature=0.7
    ).choices[0].message.content.strip()

# ---- Step 1 output
if not st.session_state.initial_response_shown and st.button("🔍 Get Recommendation"):
    doc = fetch_mongo(context_path)
    rag_chunks, rag_answer = [], ""

    if doc:
        st.markdown("### 📘 Initial Recommendation")
        st.info(doc["response"])
        st.session_state.chat_history.append({"role": "assistant", "content": doc["response"]})
    else:
        try:
            rag_result = query_index(context_path)
            rag_answer = rag_result["answer"]
            rag_chunks = rag_result["chunks"]
            st.markdown("### 📘 Document Insight")
            st.info(rag_answer)
            st.session_state.chat_history.append({"role": "assistant", "content": rag_answer})
        except Exception:
            st.error("Could not retrieve structured or document-based recommendation.")
    st.session_state.initial_response_shown = True

# ---- Step 2 chat
if st.session_state.initial_response_shown:
    st.subheader("Step 2: Ask follow-up questions")
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).markdown(msg["content"])

    user_prompt = st.chat_input("Ask your question...")
    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        doc = fetch_mongo(st.session_state.context_path)
        rag_chunks, rag_answer = [], ""
        try:
            rag_result = query_index(user_prompt)
            rag_answer = rag_result["answer"]
            rag_chunks = rag_result["chunks"]
        except:
            rag_answer = "Sorry, document lookup failed."

        base_response = doc["response"] if doc else ""
        tone = doc["tone"] if doc else "supportive"
        answer = llm_synthesize(user_prompt, base_response, rag_chunks, tone)

        st.chat_message("assistant").markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

        with st.expander("📄 Sources & Context", expanded=False):
            if doc:
                st.markdown(f"**Structured Source:** `{st.session_state.context_path}`")
            if rag_chunks:
                st.markdown("**Document Chunks:**")
                for i, chunk in enumerate(rag_chunks, 1):
                    text = chunk.get("text", "").strip()
                    source = chunk.get("source", "Unknown")
                    st.markdown(f"**[{i}]** {text}\n\n_Source: {source}_")
