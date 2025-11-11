# Vector Pipeline System - Complete Flow Documentation

## 📋 Overview

This document provides a comprehensive technical explanation of the entire system flow, from when a user uploads a file until they see the "completed" message. It covers all scripts, data flow, inter-component communication, and technical details.

---

## 🎯 System Architecture

The system follows a **pipeline architecture** with these main components:

1. **Frontend (Admin Panel)** - `static/admin.html` + `static/admin.js`
2. **API Server** - `src/server.py` + `src/data_manager/api/admin_routes.py`
3. **Background Worker** - `src/data_manager/workers/processing_worker.py`
4. **Orchestrator** - `src/data_manager/core/orchestrator.py`
5. **Processing Pipeline** - Extractors → Processors → Embedders → Vector DB

---

## 🔄 Complete Flow: File Upload to Completion

### **PHASE 1: User Upload (Frontend → API)**

#### Step 1.1: File Selection
**Location:** `static/admin.js` (lines 23-80)

**What Happens:**
- User clicks or drags-and-drops a JSON file
- `handleFileSelection()` validates:
  - File extension must be `.json`
  - File size must be < 50MB
- If valid, file is stored in `selectedFile` variable
- UI switches from upload section to questionnaire

**Data Flow:**
```
User Action → File Input → Validation → State Update (selectedFile)
```

#### Step 1.2: Questionnaire Completion
**Location:** `static/admin.js` (lines 95-153)

**What Happens:**
- User fills questionnaire:
  - Content Structure (array_of_objects, nested_objects, etc.)
  - Language (en, mr, bilingual)
  - Category (government_officials, services_schemes, etc.)
  - Importance Level
  - Chunk Size
- User clicks "Upload & Process"
- `submitUpload()` function is called

**Data Collected:**
```javascript
{
  file: File object,
  file_type: "json",
  content_structure: "array_of_objects",
  language: "en",
  category: "government_officials",
  importance: "normal",
  chunk_size: "medium",
  special_elements: []
}
```

#### Step 1.3: File Upload to Server
**Location:** `static/admin.js` (lines 130-148)

**What Happens:**
- Creates `FormData` with file + questionnaire answers
- Sends POST request to `/api/admin/upload`
- Shows progress: "Uploading file..." (5%)
- Waits for response with `job_id`

**HTTP Request:**
```http
POST /api/admin/upload
Content-Type: multipart/form-data

file: [binary file data]
file_type: json
content_structure: array_of_objects
language: en
category: government_officials
importance: normal
chunk_size: medium
special_elements: []
```

---

### **PHASE 2: API Receives Upload**

#### Step 2.1: API Route Handler
**Location:** `src/data_manager/api/admin_routes.py` (lines 25-125)

**What Happens:**
1. **File Validation:**
   - Validates file extension matches declared type
   - Checks file size < 50MB
   
2. **File Saving:**
   - Calls `FileHandler.save_upload()` 
   - Saves file to `uploads/temp/` directory
   - Returns path to saved file

3. **File Hash Generation:**
   - Calculates SHA256 hash using `FileHandler.get_file_hash()`
   - Used for duplicate detection and source ID generation

4. **Job Creation:**
   - Calls `JobManager.create_job()`
   - Creates job metadata with all user selections
   - Generates unique `job_id` (format: `job_YYYYMMDDHHMMSS_<hash>`)
   - Saves job to `jobs/job_<job_id>.json`

5. **Response:**
   - Returns JSON with `job_id` and file info
   - Status: `created` (not yet processing)

**Code Flow:**
```python
# admin_routes.py:upload_file()
1. Validate file extension
2. Save file → FileHandler.save_upload()
3. Validate file → FileHandler.validate_file()
4. Get file hash → FileHandler.get_file_hash()
5. Create job → JobManager.create_job()
6. Save job file path
7. Return job_id to frontend
```

**Job File Created:**
```json
{
  "job_id": "job_20251106152651_6eb4ee11",
  "status": "created",
  "filename": "officials_directory.json",
  "file_type": "json",
  "file_path": "/uploads/temp/officials_directory.json",
  "content_structure": "array_of_objects",
  "language": "en",
  "category": "government_officials",
  ...
}
```

#### Step 2.2: Frontend Receives Job ID
**Location:** `static/admin.js` (lines 143-147)

**What Happens:**
- Receives `job_id` from API
- Updates progress: "File uploaded. Starting processing..." (10%)
- Starts polling for job status every 2 seconds
- Calls `startJobPolling()`

**Polling Logic:**
```javascript
// Polls every 2 seconds
GET /api/admin/job/{job_id}
```

---

### **PHASE 3: Background Worker Picks Up Job**

#### Step 3.1: Worker Startup
**Location:** `src/server.py` (lines 64-72)

**What Happens:**
- On server startup, `start_worker()` is called
- Creates background async task that runs indefinitely
- Worker continuously checks for pending jobs

**Worker Loop:**
```python
# processing_worker.py:start()
while is_running:
    1. Get pending jobs → JobManager.get_pending_jobs()
    2. For each pending job:
       - Process job → process_job(job_id)
    3. If no jobs, sleep 2 seconds
    4. Repeat
```

#### Step 3.2: Worker Finds Job
**Location:** `src/data_manager/workers/processing_worker.py` (lines 36-65)

**What Happens:**
- Worker checks `jobs/` directory for files with status `created` or `pending`
- Finds job file: `job_20251106152651_6eb4ee11.json`
- Calls `process_job(job_id)`

#### Step 3.3: Job Processing Starts
**Location:** `src/data_manager/workers/processing_worker.py` (lines 72-191)

**What Happens:**
1. **Load Job Data:**
   - Reads job JSON file
   - Creates `JobMetadata` object

2. **Status Update:**
   - Updates job status: `created` → `processing`
   - Sets progress: 5%
   - Sets current_step: "Starting processing"
   - Saves updated job file

3. **Prepare Metadata:**
   - Extracts all job metadata (file_type, content_structure, language, etc.)
   - Prepares `job_metadata` dict for orchestrator

4. **Call Orchestrator:**
   - Calls `orchestrator.process_file(file_path, job_metadata, progress_callback)`
   - Progress callback updates job file with each step

**Progress Callback:**
```python
def progress_callback(percentage, message):
    JobManager.update_job(
        job_id,
        progress=percentage,
        current_step=message
    )
```

---

### **PHASE 4: Orchestrator Coordinates Processing**

#### Step 4.1: Orchestrator Initialization
**Location:** `src/data_manager/core/orchestrator.py` (lines 36-48)

**What Happens:**
- Orchestrator initializes all components (singletons):
  - `FileTypeRouter` - Routes files to extractors
  - `RoutingEngine` - Routes content to processors
  - `Embedder` - Generates embeddings
  - `VectorPreparer` - Formats vectors for Pinecone
  - `PineconeUpserter` - Uploads to vector DB
  - `UploadVerifier` - Verifies uploads
  - `ReportGenerator` - Generates reports

#### Step 4.2: Source ID Generation
**Location:** `src/data_manager/core/orchestrator.py` (lines 87-106)

**What Happens:**
- Generates unique `source_id` for this file
- Uses: `IDGenerator.generate_source_id(filename, file_hash, user_metadata)`
- Format: `src_<hash>` (e.g., `src_abd56bc77bfd7ba9`)
- Used to track all vectors from this source in Pinecone

**Source ID Components:**
```python
source_id = hash(
    filename + 
    file_hash + 
    category + 
    content_type + 
    language
)
```

---

### **PHASE 5: Content Extraction**

#### Step 5.1: File Type Routing
**Location:** `src/data_manager/core/orchestrator.py` (lines 237-269)
**Extractor:** `src/data_manager/extractors/file_type_router.py`

**What Happens:**
1. **Route to Extractor:**
   - Determines file type: `json`
   - Gets `JSONExtractor` from router
   - Calls `extractor.extract(file_path)`

2. **Progress Update:**
   - Updates job: progress=10%, step="Extracting content from file"

#### Step 5.2: JSON Extraction
**Location:** `src/data_manager/extractors/json_extractor.py` (lines 70-138)

**What Happens:**
1. **File Validation:**
   - Checks file exists and is readable
   - Validates JSON syntax
   - Reads file content

2. **Structure Detection:**
   - Detects JSON structure type:
     - `array_of_objects` - List of dicts
     - `nested_objects` - Nested dict structure
     - `web_scraping_output` - Has url, title, content
     - `api_response` - Has status, data fields

3. **Content Normalization:**
   - Converts to standard format (list of objects)
   - Handles different structures:
     - Array: Use as-is
     - API response: Extract `data` field
     - Nested: Flatten to list
   - Returns normalized content + structure type

**Extraction Result:**
```python
ExtractionResult(
    content=[{...}, {...}, ...],  # List of objects
    file_type="json",
    extracted_structure="array_of_objects",
    metadata={...}
)
```

**Data Flow:**
```
File (JSON) → JSONExtractor → Normalized List of Objects
```

---

### **PHASE 6: Content Processing & Chunking**

#### Step 6.1: Routing to Processor
**Location:** `src/data_manager/core/orchestrator.py` (lines 271-307)
**Router:** `src/data_manager/routing/routing_engine.py`

**What Happens:**
1. **Processor Selection:**
   - RoutingEngine analyzes:
     - Content structure: `array_of_objects`
     - User category: `government_officials`
     - Content characteristics
   - Selects appropriate processor:
     - `TabularProcessor` - For array_of_objects
     - `DirectoryProcessor` - For directory structures
     - `WebContentProcessor` - For web scraping output
     - `UniversalProcessor` - Fallback

2. **Progress Update:**
   - Updates job: progress=30%, step="Processing content and creating chunks"

#### Step 6.2: Processor Execution
**Location:** `src/data_manager/processors/universal_processor.py` (or specific processor)

**What Happens:**
1. **Content Analysis:**
   - Analyzes each object in the array
   - Extracts text fields
   - Identifies key-value pairs

2. **Chunk Creation:**
   - For each object/item:
     - Converts to text representation
     - Checks if text fits in chunk size (512 tokens for "medium")
     - If too large, splits intelligently:
       - Split by paragraphs
       - Split by sentences
       - Preserve context
   - Creates `Chunk` objects with:
     - `chunk_id` - Unique ID (format: `{source_id}_chunk_{index}`)
     - `text` - Chunk text content
     - `metadata` - Original object data + enriched metadata
     - `language` - Detected or user-specified
     - `quality_score` - Quality validation score

3. **Chunk Validation:**
   - Validates each chunk:
     - Minimum length check
     - Quality score check (must be > 0.5)
     - Language validation
   - Rejects low-quality chunks

4. **Metadata Enrichment:**
   - Adds metadata to each chunk:
     - `source_id` - Source document ID
     - `category` - Content category
     - `importance` - Importance level
     - `chunk_index` - Position in document
     - `item_type` - Type of content

**Processing Result:**
```python
ProcessingResult(
    chunks=[Chunk(...), Chunk(...), ...],  # List of 20 chunks
    total_chunks=20,
    valid_chunks=20,
    rejected_chunks=0
)
```

**Data Flow:**
```
Normalized Objects → Processor → Chunks (with metadata)
```

---

### **PHASE 7: Embedding Generation**

#### Step 7.1: Embedding Preparation
**Location:** `src/data_manager/core/orchestrator.py` (lines 309-336)

**What Happens:**
1. **Extract Texts:**
   - Extracts `text` field from each chunk
   - Creates list: `["chunk text 1", "chunk text 2", ...]`

2. **Progress Update:**
   - Updates job: progress=50%, step="Generating embeddings"

#### Step 7.2: Batch Embedding
**Location:** `src/data_manager/embedding/embedder.py` (lines 76-119)

**What Happens:**
1. **Model Loading:**
   - Uses `multilingual-e5-base` model (768 dimensions)
   - Loaded as singleton (loaded once, reused)
   - Runs on CPU or GPU (configurable)

2. **Text Prefixing:**
   - For document content, prefixes with `"passage: "`
   - Example: `"passage: John Doe is the director..."`

3. **Batch Processing:**
   - Processes chunks in batches (batch_size=32)
   - Generates 768-dimensional vectors
   - Returns list of numpy arrays

**Embedding Process:**
```python
texts = ["chunk 1", "chunk 2", ...]
prefixed = ["passage: chunk 1", "passage: chunk 2", ...]
embeddings = model.encode(prefixed, batch_size=32)
# Returns: [array([...768 dims...]), array([...768 dims...]), ...]
```

**Data Flow:**
```
Chunks (text) → Embedder → Embeddings (768-dim vectors)
```

---

### **PHASE 8: Vector Preparation**

#### Step 8.1: Vector Formatting
**Location:** `src/data_manager/core/orchestrator.py` (lines 338-378)
**Preparer:** `src/data_manager/embedding/vector_preparer.py`

**What Happens:**
1. **Combine Data:**
   - Combines chunks + embeddings into vector format
   - For each chunk:
     ```python
     {
         'id': chunk.chunk_id,
         'embedding': embedding_array,
         'text': chunk.text,
         'metadata': chunk.metadata
     }
     ```

2. **Prepare Pinecone Format:**
   - Converts numpy arrays to lists (JSON serializable)
   - Prepares metadata for Pinecone:
     - Filters metadata to Pinecone-compatible types
     - Limits text length in metadata (2000 chars)
   - Creates vector dicts:
     ```python
     {
         'id': 'src_abc_chunk_0',
         'values': [0.123, -0.456, ...],  # 768 floats
         'metadata': {
             'text': 'chunk text...',
             'source_id': 'src_abc',
             'category': 'government_officials',
             ...
         }
     }
     ```

3. **Validation:**
   - Validates each vector:
     - ID format check
     - Embedding dimension check (must be 768)
     - No NaN or Inf values
     - Metadata type checks

4. **Progress Update:**
   - Updates job: progress=70%, step="Preparing vectors for upload"

**Data Flow:**
```
Chunks + Embeddings → VectorPreparer → Pinecone-format Vectors
```

---

### **PHASE 9: Pinecone Upload**

#### Step 9.1: Pinecone Connection
**Location:** `src/data_manager/database/pinecone_upserter.py` (lines 24-56)

**What Happens:**
1. **Initialization (First Time):**
   - Connects to Pinecone using API key
   - Checks if index exists
   - If not, creates index:
     - Name: `dma-bot-index`
     - Dimension: 768
     - Metric: cosine
     - Cloud: AWS (serverless)

2. **Connection:**
   - Connects to existing index
   - Gets index stats

#### Step 9.2: Vector Upload
**Location:** `src/data_manager/core/orchestrator.py` (lines 380-407)
**Upserter:** `src/data_manager/database/pinecone_upserter.py` (lines 81-120)

**What Happens:**
1. **Batch Upload:**
   - Splits vectors into batches (batch_size=100)
   - Uploads each batch to Pinecone
   - Uses `index.upsert(vectors=vectors)`

2. **Progress Tracking:**
   - Tracks uploaded count
   - Handles errors per batch
   - Continues even if some batches fail

3. **Progress Update:**
   - Updates job: progress=85%, step="Uploading to vector database"

**Upload Process:**
```python
# Split into batches of 100
batches = [vectors[0:100], vectors[100:200], ...]

for batch in batches:
    response = index.upsert(vectors=batch)
    uploaded_count += response.upserted_count
```

**Data Flow:**
```
Pinecone Vectors → Pinecone API → Vector Database
```

---

### **PHASE 10: Verification**

#### Step 10.1: Upload Verification
**Location:** `src/data_manager/core/orchestrator.py` (lines 409-433)
**Verifier:** `src/data_manager/database/verifier.py`

**What Happens:**
1. **Source Verification:**
   - Queries Pinecone with `source_id` filter
   - Counts vectors found for this source
   - Compares with expected count

2. **Progress Update:**
   - Updates job: progress=95%, step="Verifying upload"

**Verification Process:**
```python
# Query with source_id filter
results = index.query(
    vector=[0.0] * 768,  # Dummy vector
    top_k=expected_count,
    filter={"source_id": source_id}
)

found_count = len(results.matches)
success = found_count == expected_count
```

**Data Flow:**
```
Pinecone Query → Verification Result
```

---

### **PHASE 11: Report Generation**

#### Step 11.1: Generate Report
**Location:** `src/data_manager/core/orchestrator.py` (lines 174-208)

**What Happens:**
1. **Collect Statistics:**
   - Processing time
   - Chunks created vs uploaded
   - File size
   - Source ID
   - Verification results

2. **Generate Report:**
   - Creates JSON report with all details
   - Saves to `reports/job_<job_id>_report.json`

3. **Progress Update:**
   - Updates job: progress=100%, step="Generating report"

**Report Structure:**
```json
{
  "job_id": "job_20251106152651_6eb4ee11",
  "source_metadata": {...},
  "processing_stats": {
    "chunks_created": 20,
    "chunks_uploaded": 20,
    "duration_seconds": 8.5
  },
  "upload_results": {...},
  "verification_results": {...}
}
```

---

### **PHASE 12: Job Completion**

#### Step 12.1: Update Job Status
**Location:** `src/data_manager/workers/processing_worker.py` (lines 136-153)

**What Happens:**
1. **Update Job:**
   - Status: `processing` → `completed`
   - Progress: 100%
   - Sets `chunks_created` and `chunks_uploaded` counts
   - Sets `source_id`
   - Sets `processing_completed_at` timestamp

2. **Move File:**
   - Moves file from `uploads/temp/` to `uploads/processed/{job_id}/`
   - Keeps processed files organized by job

3. **Save Report:**
   - Saves processing report to `reports/` directory

**Final Job File:**
```json
{
  "job_id": "job_20251106152651_6eb4ee11",
  "status": "completed",
  "progress_percentage": 100,
  "current_step": "Processing complete",
  "chunks_created": 20,
  "chunks_uploaded": 20,
  "source_id": "src_abd56bc77bfd7ba9",
  "processing_completed_at": "2025-11-06T15:27:00.169503"
}
```

---

### **PHASE 13: Frontend Shows Completion**

#### Step 13.1: Polling Detects Completion
**Location:** `static/admin.js` (lines 163-191)

**What Happens:**
- Polling continues every 2 seconds
- Polls: `GET /api/admin/job/{job_id}`
- API returns updated job status

#### Step 13.2: Status Check
**Location:** `static/admin.js` (lines 178-186)

**What Happens:**
- Checks `job.status === 'completed'`
- Stops polling
- Calls `showSuccess(job)`

#### Step 13.3: Display Success
**Location:** `static/admin.js` (lines 209-239)

**What Happens:**
- Hides progress section
- Shows success message with:
  - File name
  - Job ID
  - Source ID
  - Statistics:
    - Chunks Created: 20
    - Vectors Uploaded: 20
- Shows "Upload Another File" button

**Final UI State:**
```
✅ Processing Complete!
File: officials_directory.json
Job ID: job_20251106152651_6eb4ee11
Source ID: src_abd56bc77bfd7ba9

[20] Chunks Created    [20] Vectors Uploaded

[Upload Another File]
```

---

## 🔗 Component Communication

### **File-Based Communication**

1. **Job Files (`jobs/*.json`):**
   - **Writer:** JobManager, ProcessingWorker
   - **Reader:** API routes, Frontend (via API)
   - **Purpose:** Job state synchronization
   - **Update Frequency:** Real-time (on each progress update)

2. **Report Files (`reports/*.json`):**
   - **Writer:** ReportGenerator
   - **Reader:** API routes (for download/view)
   - **Purpose:** Processing results archive

### **In-Memory Communication**

1. **Progress Callbacks:**
   - Orchestrator → Worker → JobManager
   - Updates job file with progress

2. **Singleton Instances:**
   - All components use singleton pattern
   - Shared state across requests:
     - Embedder (model loaded once)
     - PineconeUpserter (connection reused)
     - FileTypeRouter (extractors initialized once)

### **API Communication**

1. **Frontend → Backend:**
   - `POST /api/admin/upload` - File upload
   - `GET /api/admin/job/{job_id}` - Job status (polling)
   - `GET /api/admin/jobs` - List all jobs

2. **Backend → Frontend:**
   - JSON responses with job data
   - Real-time status updates via polling

### **External Services**

1. **Pinecone API:**
   - Vector database for storing embeddings
   - Communication: HTTP REST API
   - Operations: upsert, query, fetch, delete

2. **HuggingFace (Embedding Model):**
   - Model: `intfloat/multilingual-e5-base`
   - Loaded once, used for all embeddings
   - Runs locally (CPU/GPU)

---

## 📊 Data Structures

### **Job Metadata**
```python
JobMetadata(
    job_id: str,
    status: str,  # created, processing, completed, failed
    filename: str,
    file_type: str,
    file_path: str,
    content_structure: str,
    language: str,
    category: str,
    progress_percentage: int,
    current_step: str,
    chunks_created: int,
    chunks_uploaded: int,
    source_id: str
)
```

### **Chunk Object**
```python
Chunk(
    chunk_id: str,  # src_abc_chunk_0
    text: str,  # Chunk text content
    metadata: dict,  # Enriched metadata
    language: str,
    quality_score: float
)
```

### **Vector Format (Pinecone)**
```python
{
    'id': 'src_abc_chunk_0',
    'values': [0.123, -0.456, ...],  # 768 floats
    'metadata': {
        'text': 'chunk text...',
        'source_id': 'src_abc',
        'category': 'government_officials',
        'language': 'en',
        ...
    }
}
```

---

## 🔧 Technical Details

### **Concurrency Model**

1. **Async/Await:**
   - Worker runs as async task
   - Orchestrator uses async methods
   - Non-blocking I/O for file operations

2. **Single Worker:**
   - One worker processes jobs sequentially
   - Can be extended to multiple workers

3. **Polling:**
   - Frontend polls every 2 seconds
   - Could be upgraded to WebSockets for real-time

### **Error Handling**

1. **Job Retry:**
   - Failed jobs can retry (max 3 times)
   - Retry count tracked in job file

2. **Partial Failures:**
   - If some chunks fail, others continue
   - Failed chunks logged but don't stop processing

3. **Validation:**
   - File validation before processing
   - Chunk validation before embedding
   - Vector validation before upload

### **Performance Optimizations**

1. **Batch Processing:**
   - Embeddings: batch_size=32
   - Pinecone uploads: batch_size=100

2. **Singleton Pattern:**
   - Embedder model loaded once
   - Pinecone connection reused
   - Extractors initialized once

3. **Lazy Loading:**
   - Components initialized on first use
   - Model loaded when first embedding requested

---

## 📁 File Organization

```
Vector Pipeline/
├── static/
│   ├── admin.html          # Frontend UI
│   └── admin.js            # Frontend logic
├── src/
│   ├── server.py           # FastAPI server
│   └── data_manager/
│       ├── api/
│       │   ├── admin_routes.py    # API endpoints
│       │   └── job_manager.py     # Job state management
│       ├── core/
│       │   ├── orchestrator.py   # Main pipeline coordinator
│       │   └── config.py          # Configuration
│       ├── workers/
│       │   └── processing_worker.py  # Background worker
│       ├── extractors/
│       │   ├── file_type_router.py   # Routes to extractors
│       │   └── json_extractor.py    # JSON extraction
│       ├── routing/
│       │   └── routing_engine.py    # Routes to processors
│       ├── processors/
│       │   └── universal_processor.py  # Chunk creation
│       ├── embedding/
│       │   ├── embedder.py        # Embedding generation
│       │   └── vector_preparer.py  # Vector formatting
│       ├── database/
│       │   ├── pinecone_upserter.py  # Pinecone upload
│       │   └── verifier.py           # Upload verification
│       └── utils/
│           ├── file_handler.py     # File operations
│           └── id_generator.py     # ID generation
├── jobs/                    # Job state files
├── uploads/
│   ├── temp/                # Temporary uploads
│   └── processed/           # Processed files
└── reports/                 # Processing reports
```

---

## 🎯 Summary: Complete Flow

```
1. User uploads file → Frontend validates
2. Frontend sends to API → /api/admin/upload
3. API saves file → Creates job → Returns job_id
4. Frontend starts polling → GET /api/admin/job/{job_id}
5. Worker finds job → Updates status to "processing"
6. Worker calls Orchestrator → process_file()
7. Orchestrator extracts content → JSONExtractor
8. Orchestrator processes content → UniversalProcessor
9. Orchestrator generates embeddings → Embedder
10. Orchestrator prepares vectors → VectorPreparer
11. Orchestrator uploads to Pinecone → PineconeUpserter
12. Orchestrator verifies upload → UploadVerifier
13. Orchestrator generates report → ReportGenerator
14. Worker updates job → Status: "completed"
15. Frontend polling detects completion → Shows success
16. User sees "Processing Complete!" message
```

**Total Time:** ~8-10 seconds for a typical JSON file with 20 chunks

**Key Files Involved:**
- Frontend: `admin.js`, `admin.html`
- API: `admin_routes.py`, `job_manager.py`
- Worker: `processing_worker.py`
- Orchestrator: `orchestrator.py`
- Extractors: `json_extractor.py`
- Processors: `universal_processor.py`
- Embedding: `embedder.py`
- Database: `pinecone_upserter.py`, `verifier.py`

---

## 🔍 Debugging Tips

1. **Check Job Files:**
   - Look in `jobs/` directory for job state
   - Check `status`, `progress_percentage`, `error_message`

2. **Check Logs:**
   - Each component has its own log file in `logs/`
   - Key logs: `orchestrator.log`, `worker.log`, `api_admin.log`

3. **Check Reports:**
   - Processing reports in `reports/` directory
   - Contains detailed statistics

4. **Check Pinecone:**
   - Use Pinecone dashboard to verify vectors
   - Query by `source_id` to see uploaded vectors

---

This document provides a complete technical overview of the system flow. Each component is designed to be modular and replaceable, following clean architecture principles.

