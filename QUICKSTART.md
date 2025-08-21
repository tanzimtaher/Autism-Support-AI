# 🚀 Quick Start Guide

Get the Autism Support App running in 5 minutes!

## ⚡ Super Quick Setup

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Configure API Keys**
Create `.streamlit/secrets.toml`:
```toml
[secrets]
OPENAI_API_KEY = "your-openai-api-key"
ADMIN_PASSWORD = "admin123"
```

### 3. **Run the App**
```bash
streamlit run app.py
```

### 4. **Open Your Browser**
Navigate to: `http://localhost:8501`

## 🎯 First Steps

### **For Users:**
1. **Choose "Guided Step-by-Step"** for your first time
2. **Fill in your profile** (role, diagnosis status, age)
3. **Follow the conversation** - I'll guide you through everything
4. **Upload documents** if you have patient reports to share

### **For Admins:**
1. **Go to "Upload Documents"** page
2. **Enter password**: `admin123`
3. **Upload expert documents** (PDF, TXT, DOCX)
4. **Process documents** to improve the knowledge base

## 🔧 Optional: Enable Vector Search

For enhanced search capabilities:

### **Start Qdrant (Docker)**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### **Ingest Knowledge Base**
```bash
python -m rag.ingest_shared_kb
```

## 🧪 Test Everything Works

```bash
python test_system_integration.py
```

## 🆘 Common Issues

### **"No module named 'PyPDF2'"**
```bash
pip install PyPDF2 python-docx sentence-transformers
```

### **"Qdrant connection failed"**
- This is normal if Qdrant isn't running
- App works without it (uses MongoDB only)
- Start Qdrant for enhanced features

### **"OpenAI API key not found"**
- Check `.streamlit/secrets.toml` exists
- Verify API key is correct
- Restart the app after changes

## 📱 What You Can Do

### **Guided Mode** (Recommended for new users)
- ✅ Step-by-step conversation
- ✅ Personalized recommendations
- ✅ Clear next steps
- ✅ No need to know what to ask

### **Free Chat** (For experienced users)
- ✅ Ask any question
- ✅ Upload patient documents
- ✅ Get detailed answers
- ✅ Flexible conversation flow

### **Browse Topics** (Direct access)
- ✅ Choose specific topics
- ✅ Get structured information
- ✅ Follow-up questions
- ✅ Document insights

## 🎉 You're Ready!

The app is now running and ready to help families affected by autism. Start with guided mode for the best experience!

---

**Need help?** Check the full [README.md](README.md) for detailed documentation.
