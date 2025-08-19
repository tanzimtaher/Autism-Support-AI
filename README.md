# Autism Support App v2

A comprehensive support application designed to assist individuals with autism and their caregivers.

## Features

- **Document Upload & Processing**: Upload and process various document formats
- **Knowledge Base Management**: Maintain and query a structured knowledge base
- **RAG (Retrieval-Augmented Generation)**: Advanced query capabilities with vector search
- **CSV Data Management**: Edit and manage structured data
- **Streamlit Web Interface**: User-friendly web application

## Project Structure

```
autism_support_app_v2/
├── app.py                          # Main Streamlit application
├── convert_knowledge_graph_to_csv.py  # Knowledge graph conversion utility
├── data/                           # Data storage directory
│   └── user_uploaded_docs/         # User uploaded documents
├── knowledge/                      # Knowledge base management
│   ├── __init__.py
│   ├── ingest.py                   # Document ingestion
│   └── mongo_insert.py             # MongoDB integration
├── pages/                          # Streamlit pages
│   ├── edit_csv.py                 # CSV editing interface
│   └── upload_docs.py              # Document upload interface
├── rag/                            # RAG implementation
│   ├── __init__.py
│   ├── build_index.py              # Vector index building
│   └── query_engine.py             # Query processing
└── vector_index/                   # Vector storage
```

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd autism_support_app_v2
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

## Configuration

The application uses Streamlit configuration files:
- `.streamlit/config.toml`: General configuration
- `.streamlit/secrets.toml`: Sensitive configuration (API keys, etc.)

## Usage

1. **Upload Documents**: Use the upload interface to add new documents to the knowledge base
2. **Query Knowledge**: Use the RAG system to search and retrieve relevant information
3. **Manage Data**: Edit CSV files and manage structured data
4. **Build Index**: Rebuild the vector index when new documents are added

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]

## Support

For support and questions, please [create an issue](link-to-issues) or contact the development team.
