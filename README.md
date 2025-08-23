# Autism Support App v2

A comprehensive AI-powered support system for families and individuals affected by autism, featuring guided conversations, document analysis, and personalized assistance.

## 🚀 Features

### **Core Functionality**
- **🎯 Guided Conversations**: Step-by-step structured support for new users
- **💬 Free Chat**: Flexible conversation mode for experienced users
- **📄 Document Upload**: Patient-specific document analysis for personalized guidance
- **🔍 Smart Routing**: Intelligent query routing between structured knowledge and vector search
- **🔒 Privacy-First**: User-specific document storage with complete isolation
- **🧠 Conversation Memory**: Persistent storage of conversation insights and user preferences

### **Admin Features**
- **📚 Expert Document Upload**: Admin-only interface for improving general knowledge base
- **🔐 Access Control**: Password-protected admin interface
- **📊 Knowledge Management**: Centralized management of expert resources

### **Conversation Memory System**
- **💾 Persistent Storage**: Chat history and insights stored in user-specific vector collections
- **🔍 Smart Insights**: Automatic extraction of topics, concerns, strategies, and preferences
- **📈 Learning Patterns**: Tracks successful strategies and user learning preferences
- **🔄 Context Continuity**: Maintains conversation context across sessions
- **⚡ Performance Optimized**: Prevents browser crashes with intelligent history management

### **Technical Architecture**
- **🧠 Advanced RAG System**: Multi-source retrieval with patient context integration
- **🔍 Vector Search**: Qdrant with 1536-dimensional embeddings and diversity optimization
- **📊 Structured Knowledge**: MongoDB for guided conversation flows and treatment paths
- **🌐 Real-time Integration**: Web browsing + patient documents + expert knowledge
- **🔒 Privacy-First**: User-specific document isolation with transparent source attribution
- **📈 Production-Ready**: Scalable vector database with intelligent query routing

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

### **RAG System Overview**

The Autism Support App v2 implements a **comprehensive Retrieval-Augmented Generation (RAG) system** that combines multiple knowledge sources to provide personalized, context-aware support for autism families.

### **Core RAG Components**

#### **1. Knowledge Sources**
- **Qdrant Vector Store**: Primary knowledge base with 1536-dimensional embeddings
  - `user_docs_{user_id}`: Private patient documents (diagnosis reports, evaluations, therapy notes)
  - `kb_autism_support`: Shared autism knowledge base (research, guidelines, resources)
  - `chat_history_{user_id}`: Persistent conversation history storage
  - `insights_{user_id}`: Extracted conversation insights and patterns
  - `prefs_{user_id}`: User preferences and learning patterns
  - `learning_{user_id}`: Successful strategies and recommendations
- **MongoDB**: Structured conversation flows and guided support paths
- **Web Integration**: Real-time information retrieval for dynamic context
- **Patient Documents**: Real-time analysis and context extraction

#### **2. Intelligent Query Routing**
- **RetrievalRouter.route()**: Determines optimal knowledge source combination
- **Safety Detection**: Routes critical queries to appropriate resources
- **Context Awareness**: Adapts search strategy based on user profile and conversation state

#### **3. Multi-Source Vector Search**
- **search_with_diversity()**: Ensures multiple source perspectives for comprehensive responses
- **search_user_documents()**: Patient-specific document retrieval with semantic search
- **search_conversation_memory()**: Retrieves relevant past insights and preferences
- **Hybrid Search**: Combines shared knowledge with user-specific documents and memory

#### **4. Response Synthesis Engine**
- **Multi-Source Integration**: Intelligently blends information from 5+ sources
- **Patient Context Integration**: Automatically extracts and utilizes patient-specific details
- **Memory Context Integration**: Incorporates past conversation insights for continuity
- **OpenAI GPT-4**: Advanced language model for empathetic, personalized responses

#### **5. Conversation Memory Manager**
- **Persistent Storage**: Stores chat messages, insights, and preferences in vector database
- **Intelligent Extraction**: Automatically identifies topics, concerns, and successful strategies
- **Context Retrieval**: Semantic search across memory collections for relevant information
- **Performance Optimization**: Prevents unlimited history growth with smart summarization

### **File Structure**
```
autism_support_app_v2/
├── app.py                          # Main Streamlit application with unified UI
├── knowledge/                      # Core RAG orchestration
│   ├── intelligent_conversation_manager.py  # RAG system orchestrator
│   ├── response_synthesis_engine.py         # Multi-source response synthesis
│   ├── conversation_memory_manager.py       # Conversation memory persistence
│   └── knowledge_adapter.py                 # Conversation flow management
├── rag/                           # Vector operations and document processing
│   ├── qdrant_client.py           # Vector database client with diversity search
│   ├── embeddings.py              # OpenAI text-to-vector conversion
│   ├── ingest_user_docs.py        # Patient document ingestion and processing
│   └── process_admin_docs.py      # Expert knowledge base management
├── retrieval/                     # Intelligent query routing
│   └── retrieval_router.py        # Smart routing between knowledge sources
├── utils/                         # Patient context utilities
│   └── patient_utils.py           # Document parsing and patient summary generation
└── data/                          # Data storage
    ├── admin_uploaded_docs/       # Expert-curated resources
    ├── user_docs/                 # Patient-specific documents
    └── qdrant_storage/            # Vector database storage
```

### **RAG Data Flow**

#### **1. Query Processing**
```
User Query → RetrievalRouter.route() → Knowledge Source Selection
```

#### **2. Multi-Source Retrieval**
```
Vector Search:
├── search_with_diversity() → Shared knowledge base
├── search_user_documents() → Patient-specific documents
└── Web browsing → Dynamic information

MongoDB:
├── Structured conversation flows
├── Guided support paths
└── Treatment recommendations
```

#### **3. Context Building & Synthesis**
```
Information Sources:
├── Patient Documents (highest priority)
├── Shared Knowledge Base
├── MongoDB Structured Flows
├── Web Content
└── User Profile & History

Context Processing:
├── Patient Context Extraction (diagnosis, age, concerns)
├── Query Enhancement with Patient Details
├── Multi-Source Information Blending
└── Structured Context for LLM
```

#### **4. Response Generation**
```
OpenAI GPT-4 Processing:
├── Structured Context Input
├── Patient-Specific Personalization
├── Multi-Source Synthesis
├── Memory Context Integration
└── Empathetic Response Generation

Output:
├── Personalized Response
├── Source Transparency
├── Confidence Scoring
├── Memory Continuity
└── Next Step Suggestions
```

### **Conversation Memory Data Flow**

#### **1. Memory Storage Pipeline**
```
User Message → IntelligentConversationManager → ConversationMemoryManager
├── Store in chat_history_{user_id} collection
├── Extract insights every 10 messages
├── Store insights in insights_{user_id} collection
├── Store preferences in prefs_{user_id} collection
└── Store strategies in learning_{user_id} collection
```

#### **2. Memory Retrieval Pipeline**
```
User Query → Response Synthesis Engine → Memory Context Integration
├── Semantic search across all memory collections
├── Retrieve relevant chat history, insights, preferences
├── Integrate with current conversation context
├── Provide continuity and avoid repetition
└── Enhance personalization with past learnings
```

#### **3. Performance Optimization**
```
Chat History Management:
├── Maximum 25 messages in session
├── Automatic insight extraction at 10-message intervals
├── Smart summarization of old conversations
├── Vector storage of key insights
└── Prevention of browser crashes
```

### **Patient Context Integration**

#### **Document Processing Pipeline**
1. **Upload**: Real-time document ingestion into user-specific vector collections
2. **Parsing**: Automatic extraction of diagnosis, age, concerns, and key findings
3. **Context Enhancement**: Query enhancement with patient-specific details
4. **Response Personalization**: AI responses reference specific patient information

#### **Transparency Features**
- **"How I made this decision"**: Shows actual sources used (patient docs, knowledge base, etc.)
- **Source Attribution**: Individual document names and knowledge sources
- **Confidence Scoring**: 95% when using patient documents, 90% with web content, 70% with general knowledge
- **Context Path Tracking**: Current conversation topic and guidance path

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
