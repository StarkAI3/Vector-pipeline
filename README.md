# DMA Bot Data Management System

A self-service data upload and management system for the DMA (Directorate of Municipal Administration) chatbot. This system allows non-technical admins to upload various file types through a questionnaire-based interface, which automatically processes, chunks, embeds, and stores content in a Pinecone vector database.

## 🎯 Project Status

**Current Phase: Phase 2 - Excel/CSV Support ✓ COMPLETE**

Complete end-to-end pipeline for JSON, Excel, and CSV files is operational and production-ready!

## 📋 Features

- **Multi-format Support**: ✅ JSON, ✅ Excel, ✅ CSV (PDF, Text, Word, Web URLs coming soon)
- **Questionnaire-Based**: Simple wizard interface instead of complex auto-detection
- **Bilingual Support**: Handles English, Marathi, and mixed content
- **Background Processing**: Async job processing with progress tracking
- **Quality Validation**: Automatic chunk quality assessment
- **Comprehensive Reports**: Detailed processing reports with statistics
- **De-duplication**: Content-based stable IDs prevent duplicates
- **Deletion System**: Multiple deletion methods (semantic search, filename, filters)
- **Vector DB Agnostic**: Works with Pinecone, Qdrant, and more

## 🏗️ Architecture

```
User uploads file + answers questions
         ↓
API receives and creates processing job
         ↓
Background worker picks up job
         ↓
Processing Orchestrator coordinates:
  1. Extract content from file
  2. Analyze structure
  3. Route to appropriate processor
  4. Create chunks with metadata
  5. Generate embeddings
  6. Upload to Pinecone vector DB
  7. Verify and report results
         ↓
User sees success report with tracking ID
```

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Pinecone account and API key
- (Optional) CUDA-enabled GPU for faster embedding generation

### Setup Steps

1. **Clone/Navigate to Project Directory**
   ```bash
   cd "/home/stark/Desktop/Vector Pipeline"
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # Or on Windows: .\venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   - Copy `env.example.txt` to `.env`
   - Fill in your Pinecone API key and other settings:
   ```
   PINECONE_API_KEY=your_actual_api_key
   PINECONE_ENVIRONMENT=us-east-1
   PINECONE_INDEX_NAME=dma-bot-index
   ```

5. **Test Foundation Setup** (once testing script is created)
   ```bash
   python tests/test_phase0_foundation.py
   ```

## 📁 Project Structure

```
Vector Pipeline/
├── src/
│   └── data_manager/
│       ├── api/              # API endpoints and job management
│       ├── workers/          # Background processing workers
│       ├── core/             # Configuration and orchestration
│       ├── extractors/       # File content extractors
│       ├── analyzers/        # Content analysis
│       ├── routing/          # Processor routing
│       ├── processors/       # Content processors
│       ├── enrichers/        # Metadata and element extraction
│       ├── validators/       # Quality validation
│       ├── embedding/        # Embedding generation
│       ├── database/         # Pinecone operations
│       └── utils/            # Utilities (logging, IDs, reports)
├── static/                   # Frontend HTML/JS (Phase 1+)
├── tests/                    # Test files
├── uploads/                  # Temporary file storage
├── logs/                     # Log files
└── jobs/                     # Job state files
```

## 🔧 Phase 0 Components (Completed)

### Core Utilities
1. **config.py** - Configuration management
2. **logger.py** - Comprehensive logging
3. **file_handler.py** - File operations
4. **id_generator.py** - ID generation for tracking
5. **job_manager.py** - Job state management

### Analysis & Enrichment
6. **language_detector.py** - Language detection
7. **metadata_enricher.py** - Metadata enrichment
8. **special_elements.py** - Extract URLs, emails, phones
9. **quality_validator.py** - Chunk quality validation

### Embedding & Database
10. **embedder.py** - Embedding generation (multilingual-e5-base)
11. **vector_preparer.py** - Vector formatting
12. **pinecone_upserter.py** - Pinecone upload
13. **verifier.py** - Upload verification
14. **report_generator.py** - Report generation

## 🚀 Development Roadmap

- ✅ **Phase 0**: Foundation Setup (14 utility scripts) - COMPLETE
- ✅ **Phase 1**: JSON Support - COMPLETE
  - JSON extraction (4 structure types)
  - Smart processing (4 processors)
  - Complete pipeline integration
  - Web admin interface
  - Background worker
- ⏳ **Phase 2**: Excel/CSV Support (1 week)
- ⏳ **Phase 3**: Text/Markdown Support (4-5 days)
- ⏳ **Phase 4**: PDF Support (1 week)
- ⏳ **Phase 5**: URL/Web Scraping (1.5 weeks)

**Phase 1 Status**: ✅ Production Ready

## 📝 Usage

### Quick Start

1. **Setup environment** (first time only):
   ```bash
   cd "/home/stark/Desktop/Vector Pipeline"
   source venv/bin/activate
   
   # Configure .env file with Pinecone credentials
   cp env.example.txt .env
   # Edit .env and add your PINECONE_API_KEY
   ```

2. **Start the server**:
   ```bash
   python src/server.py
   ```

3. **Access admin panel**:
   ```
   http://localhost:8000/admin
   ```

4. **Upload JSON files**:
   - Drag and drop or click to browse
   - Fill out the questionnaire
   - Track progress in real-time
   - View results and statistics

5. **Test with samples**:
   - Use files in `tests/sample_data/` for testing
   - Try different JSON structures

### Supported File Types (Phase 1)
- ✅ JSON files (.json)
  - Array of objects
  - Nested objects
  - Web scraping output
  - API responses

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific phase tests
pytest tests/test_phase0_foundation.py
pytest tests/test_phase1_json.py
```

## 📊 Key Technologies

- **Backend**: FastAPI, Python 3.10+
- **Vector DB**: Pinecone
- **Embeddings**: sentence-transformers (multilingual-e5-base)
- **File Processing**: pandas, PyPDF2, pdfplumber, python-docx
- **Web Scraping**: Selenium, BeautifulSoup
- **Language**: English, Marathi, Hindi support

## 🔐 Security Notes

- Never commit `.env` file with real credentials
- Use `.gitignore` to exclude sensitive files
- Validate all user inputs
- Sanitize filenames before storage

## 📖 Documentation

Comprehensive documentation available in `vector DB Pipeline.md`

## 🤝 Contributing

This is a government project for DMA chatbot. Follow the incremental development strategy outlined in the project documentation.

## 📧 Support

For issues or questions, please refer to the project documentation or contact the development team.

---

**Last Updated**: November 5, 2025
**Current Version**: Phase 0 Complete

