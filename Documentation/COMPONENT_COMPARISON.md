# Component Comparison: server.py, admin_routes.py, orchestrator.py, routing_engine.py

## 🎯 Quick Summary

| Component | Layer | Purpose | When It Runs |
|-----------|-------|---------|--------------|
| **server.py** | Web Server | Starts HTTP server, serves frontend | Application startup |
| **admin_routes.py** | API Layer | Handles HTTP requests, creates jobs | When user uploads file |
| **orchestrator.py** | Pipeline Coordinator | Coordinates entire processing pipeline | When worker processes job |
| **routing_engine.py** | Content Router | Routes content to right processor | During processing (step 2) |

---

## 📋 Detailed Comparison

### 1. **server.py** - The Web Server

**Location:** `src/server.py`

**Role:** Application entry point and HTTP server

**Responsibilities:**
- Creates FastAPI application
- Sets up CORS middleware
- Serves static files (HTML, JS, CSS)
- Registers API routes
- Starts background worker
- Handles server lifecycle (startup/shutdown)

**Key Code:**
```python
# Creates FastAPI app
app = FastAPI(...)

# Includes API routes
app.include_router(admin_router)

# Serves static files
app.mount("/static", StaticFiles(...))

# Starts worker on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_worker())
```

**What it does:**
- Listens on port 8000 (or configured port)
- Serves admin panel at `/admin`
- Makes API endpoints available at `/api/admin/*`
- Starts background worker to process jobs

**Analogy:** Like a restaurant's front door and host - it welcomes customers and directs them to the right place.

---

### 2. **admin_routes.py** - The API Endpoints

**Location:** `src/data_manager/api/admin_routes.py`

**Role:** HTTP request handlers (REST API)

**Responsibilities:**
- Receives file uploads from frontend
- Validates files
- Creates jobs
- Returns job status
- Manages job lifecycle (list, delete, retry)

**Key Endpoints:**
```python
@router.post("/upload")      # POST /api/admin/upload
@router.get("/job/{job_id}") # GET /api/admin/job/{job_id}
@router.get("/jobs")         # GET /api/admin/jobs
@router.delete("/job/{job_id}") # DELETE /api/admin/job/{job_id}
```

**What it does:**
1. **Upload Endpoint:**
   - Receives file + questionnaire data
   - Validates file (size, extension)
   - Saves file to disk
   - Creates job record
   - Returns `job_id`

2. **Status Endpoint:**
   - Reads job file
   - Returns current status and progress

**Key Code:**
```python
@router.post("/upload")
async def upload_file(...):
    # Save file
    saved_path = file_handler.save_upload(file.file, file.filename)
    
    # Create job
    job = job_manager.create_job(...)
    
    return {"job_id": job.job_id, ...}
```

**Analogy:** Like a restaurant's order taker - takes orders (file uploads), writes them down (creates jobs), and checks order status.

**Important:** This does NOT process the file - it only creates a job. Processing happens in background worker.

---

### 3. **orchestrator.py** - The Pipeline Coordinator

**Location:** `src/data_manager/core/orchestrator.py`

**Role:** Coordinates the entire processing pipeline

**Responsibilities:**
- Manages the complete processing flow
- Calls each stage in sequence
- Handles errors and progress updates
- Generates final reports

**Processing Stages:**
```python
1. Extract content (10%)     → FileTypeRouter → JSONExtractor
2. Process & chunk (30%)    → RoutingEngine → Processor
3. Generate embeddings (50%) → Embedder
4. Prepare vectors (70%)    → VectorPreparer
5. Upload to Pinecone (85%)  → PineconeUpserter
6. Verify upload (95%)      → UploadVerifier
7. Generate report (100%)   → ReportGenerator
```

**Key Code:**
```python
async def process_file(file_path, job_metadata, progress_callback):
    # Stage 1: Extract
    extraction_result = await self._extract_content(...)
    
    # Stage 2: Process
    processing_result = await self._process_content(...)
    
    # Stage 3: Embed
    embedding_result = await self._generate_embeddings(...)
    
    # Stage 4: Prepare vectors
    vector_result = await self._prepare_vectors(...)
    
    # Stage 5: Upload
    upload_result = await self._upload_vectors(...)
    
    # Stage 6: Verify
    verification_result = await self._verify_upload(...)
    
    # Stage 7: Report
    report = self.report_generator.generate_processing_report(...)
```

**What it does:**
- Orchestrates all processing steps
- Manages data flow between stages
- Updates progress via callbacks
- Handles errors at each stage
- Returns complete processing result

**Analogy:** Like a head chef - coordinates all kitchen stations (extraction, processing, embedding, etc.) to prepare the final dish.

**Important:** This is called by the background worker, NOT directly by API routes.

---

### 4. **routing_engine.py** - The Content Router

**Location:** `src/data_manager/routing/routing_engine.py`

**Role:** Routes extracted content to the appropriate processor

**Responsibilities:**
- Analyzes content structure
- Selects best processor for content
- Executes processing
- Returns chunks

**Available Processors:**
```python
- TabularProcessor      # For array_of_objects, tables
- DirectoryProcessor    # For directory/contact lists
- WebContentProcessor   # For web scraping output
- UniversalProcessor    # Fallback for anything
```

**Routing Logic:**
```python
def route(content, structure, metadata):
    # 1. Check user preference
    # 2. Check category hints (e.g., government_officials → DirectoryProcessor)
    # 3. Check structure mapping (array_of_objects → TabularProcessor)
    # 4. Try each processor's can_process() method
    # 5. Fallback to UniversalProcessor
    
    processor = self._select_processor(...)
    result = processor.process(content, metadata)
    return result
```

**What it does:**
- Takes extracted content (e.g., list of objects from JSON)
- Decides which processor to use
- Calls processor to create chunks
- Returns chunks with metadata

**Analogy:** Like a restaurant's expediter - looks at the order (content structure) and routes it to the right station (processor).

**Important:** This is ONE step in the orchestrator's pipeline (Stage 2). It's called BY the orchestrator.

---

## 🔄 How They Work Together

### Complete Flow:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER UPLOADS FILE (Frontend)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. server.py                                                 │
│    - Receives HTTP request                                   │
│    - Routes to admin_routes.py                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. admin_routes.py                                          │
│    - Validates file                                          │
│    - Saves file to disk                                      │
│    - Creates job (status: "created")                        │
│    - Returns job_id to frontend                             │
│    ❌ Does NOT process file                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Background Worker (processing_worker.py)                 │
│    - Finds pending jobs                                      │
│    - Updates status: "processing"                            │
│    - Calls orchestrator.process_file()                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. orchestrator.py                                          │
│    Stage 1: Extract → FileTypeRouter → JSONExtractor        │
│    Stage 2: Process → routing_engine.py → Processor        │
│    Stage 3: Embed → Embedder                                │
│    Stage 4: Prepare → VectorPreparer                        │
│    Stage 5: Upload → PineconeUpserter                       │
│    Stage 6: Verify → UploadVerifier                          │
│    Stage 7: Report → ReportGenerator                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. routing_engine.py (called in Stage 2)                   │
│    - Analyzes content structure                              │
│    - Selects processor (e.g., UniversalProcessor)           │
│    - Calls processor.process()                               │
│    - Returns chunks                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. orchestrator.py continues                                │
│    - Takes chunks from routing_engine                        │
│    - Generates embeddings                                    │
│    - Uploads to Pinecone                                     │
│    - Returns result to worker                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Worker updates job status: "completed"                   │
│ 9. Frontend polls and shows success                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Key Differences

### **server.py vs admin_routes.py**

| Aspect | server.py | admin_routes.py |
|--------|-----------|-----------------|
| **Level** | Application level | API level |
| **Purpose** | Server setup | Request handling |
| **Scope** | Entire application | API endpoints only |
| **Dependencies** | Includes admin_routes | Uses JobManager, FileHandler |
| **When** | Startup | Per request |

**server.py** sets up the server; **admin_routes.py** handles specific API requests.

### **orchestrator.py vs routing_engine.py**

| Aspect | orchestrator.py | routing_engine.py |
|--------|------------------|-------------------|
| **Scope** | Entire pipeline (7 stages) | One stage (processor selection) |
| **Level** | High-level coordination | Mid-level routing |
| **Calls** | All components | Only processors |
| **Input** | File path + metadata | Extracted content |
| **Output** | Complete result | Chunks only |
| **Stages** | 7 stages | Part of stage 2 |

**orchestrator.py** manages the entire pipeline; **routing_engine.py** handles one step (processor selection).

---

## 🎯 Real-World Analogy

Think of a restaurant:

- **server.py** = The restaurant building
  - Opens the doors
  - Sets up tables
  - Starts the kitchen

- **admin_routes.py** = The order taker
  - Takes orders (file uploads)
  - Writes tickets (creates jobs)
  - Checks order status

- **orchestrator.py** = The head chef
  - Coordinates all stations
  - Manages the entire cooking process
  - Ensures quality at each step

- **routing_engine.py** = The expediter
  - Looks at the order
  - Routes to the right station (processor)
  - Part of the head chef's team

---

## 💡 Key Takeaways

1. **server.py** = Infrastructure (starts server, serves files)
2. **admin_routes.py** = API layer (handles HTTP requests, creates jobs)
3. **orchestrator.py** = Pipeline manager (coordinates all processing steps)
4. **routing_engine.py** = Content router (selects processor for content)

**Flow:**
```
User → server.py → admin_routes.py → Job Created
                                    ↓
Worker → orchestrator.py → routing_engine.py → Processor → Chunks
                                    ↓
                            orchestrator.py continues → Pinecone → Done
```

Each component has a specific, well-defined role in the system!

