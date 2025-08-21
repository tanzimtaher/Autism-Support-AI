# Autism Support App v2

A comprehensive AI-powered support system for families and individuals affected by autism, featuring guided conversations, document analysis, and personalized assistance.

## 🚀 Features

### **Core Functionality**
- **🎯 Guided Conversations**: Step-by-step structured support for new users
- **💬 Free Chat**: Flexible conversation mode for experienced users
- **📄 Document Upload**: Patient-specific document analysis for personalized guidance
- **🔍 Smart Routing**: Intelligent query routing between structured knowledge and vector search
- **🔒 Privacy-First**: User-specific document storage with complete isolation

### **Admin Features**
- **📚 Expert Document Upload**: Admin-only interface for improving general knowledge base
- **🔐 Access Control**: Password-protected admin interface
- **📊 Knowledge Management**: Centralized management of expert resources

### **Technical Architecture**
- **🔄 Dual-Index System**: MongoDB for structured flows + Qdrant for vector search
- **🧠 Multi-Tenant**: UUID-based user isolation
- **🌐 Web Integration**: Real-time web browsing for dynamic context
- **📈 Scalable**: Production-ready vector database with metadata filtering

## 🛠️ Installation

### **Prerequisites**
- Python 3.8+
- Docker (for Qdrant)
- OpenAI API key

### **Quick Setup**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd autism_support_app_v2
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Configure Streamlit secrets**
   Create `.streamlit/secrets.toml`:
   ```toml
   [secrets]
   OPENAI_API_KEY = "your-openai-api-key"
   ADMIN_PASSWORD = "your-admin-password"
   ```

4. **Start Qdrant (optional but recommended)**
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 📖 Usage

### **For General Users**

1. **Choose Your Path**
   - **Guided Mode**: Best for new users - I'll lead the conversation
   - **Free Chat**: For experienced users - ask anything
   - **Browse Topics**: Direct access to specific topics

2. **Upload Patient Documents** (in chat)
   - Medical reports and evaluations
   - Assessment results
   - Therapy notes
   - Progress reports
   - IEP documents

3. **Get Personalized Support**
   - AI analyzes your documents
   - Provides context-aware responses
   - Maintains conversation history
   - Offers actionable next steps

### **For Admins/Experts**

1. **Access Admin Upload**
   - Navigate to "Upload Documents" page
   - Enter admin password
   - Upload expert documents

2. **Supported Document Types**
   - Autism research papers
   - Child development guidelines
   - Screening and assessment tools
   - Therapy and intervention guides
   - Educational resources
   - Policy documents

3. **Improve Knowledge Base**
   - Documents are processed and indexed
   - Available to all users
   - Maintains quality standards

## 🏗️ Architecture

### **File Structure**
```
autism_support_app_v2/
├── app.py                          # Main Streamlit application
├── pages/                          # Streamlit pages
│   ├── guided_conversation_ui.py   # Guided conversation interface
│   ├── conversational_ui.py        # Free chat interface
│   └── upload_docs.py              # Admin document upload
├── knowledge/                      # Knowledge management
│   ├── intelligent_conversation_manager.py  # Core orchestrator
│   ├── response_synthesis_engine.py         # Response generation
│   └── structured_mongo.json               # Structured knowledge base
├── rag/                           # Vector operations
│   ├── qdrant_client.py           # Vector database client
│   ├── embeddings.py              # Text-to-vector conversion
│   ├── ingest_shared_kb.py        # Shared knowledge ingestion
│   ├── ingest_user_docs.py        # User document ingestion
│   └── process_admin_docs.py      # Admin document processing
├── app/services/                  # Service layer
│   └── knowledge_adapter.py       # Knowledge base adapter
├── retrieval/                     # Query routing
│   └── retrieval_router.py        # Smart query routing
└── data/                          # Data storage
    ├── admin_uploaded_docs/       # Admin documents
    ├── user_docs/                 # User documents
    └── processed_admin_docs/      # Processed documents
```

### **Data Flow**

1. **User Input** → **Retrieval Router**
2. **Router Decision**:
   - Safety terms → MongoDB only
   - Guided conversation → Blend (MongoDB + Vector)
   - Free-form query → Vector only
3. **Vector Search**:
   - Shared knowledge base (all users)
   - User's private documents (if available)
4. **Response Synthesis**:
   - Combine structured + vector results
   - Apply user context and profile
   - Generate empathetic response

## 🔧 Configuration

### **Environment Variables**
```bash
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key  # Optional

# Embedding Configuration
EMBED_PROVIDER=openai  # or local
EMBED_MODEL=text-embedding-3-small
```

### **Streamlit Secrets**
```toml
[secrets]
OPENAI_API_KEY = "your-openai-api-key"
ADMIN_PASSWORD = "your-admin-password"
```

## 🧪 Testing

### **Run System Tests**
```bash
python test_system_integration.py
```

### **Test Individual Components**
```bash
# Test knowledge ingestion
python -m rag.ingest_shared_kb

# Test user document processing
python -m rag.ingest_user_docs

# Test admin document processing
python -m rag.process_admin_docs
```

## 🔒 Privacy & Security

### **Data Isolation**
- **User Documents**: Stored in separate collections per user
- **Shared Knowledge**: Public collection with expert-curated content
- **No Cross-Contamination**: Strict user filtering in all queries

### **Access Control**
- **Admin Interface**: Password-protected upload system
- **User Sessions**: Isolated conversation contexts
- **Document Management**: User-specific document storage and retrieval

### **Data Retention**
- **User Documents**: Stored until manually deleted
- **Conversation History**: Session-based (cleared on restart)
- **Admin Documents**: Permanent in shared knowledge base

## 🚀 Deployment

### **Local Development**
```bash
streamlit run app.py
```

### **Production Considerations**
1. **Database**: Use managed Qdrant instance
2. **Storage**: Implement S3 for document storage
3. **Authentication**: Add proper user authentication
4. **Monitoring**: Add logging and metrics
5. **Backup**: Regular database backups

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation
- Run system tests: `python test_system_integration.py`
- Review error logs in the terminal

## 🎯 Roadmap

- [ ] User authentication system
- [ ] Advanced document analysis
- [ ] Multi-language support
- [ ] Mobile app version
- [ ] Integration with healthcare systems
- [ ] Advanced analytics dashboard
