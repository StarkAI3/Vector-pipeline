# **DMA Bot Data Management System \- Complete Project Documentation**

## **1\. Project Overview**

### **What We're Building**

A self-service data upload and management system that lets admins add, update, and manage content for the DMA (Directorate of Municipal Administration) chatbot without any coding knowledge.

**The Problem**: Currently, adding new data to the chatbot requires technical work \- parsing files, creating embeddings, uploading to the vector database. Every time someone wants to add FAQ documents, officer directories, or policy information, a developer needs to handle it.

**The Solution**: A web-based admin panel where users upload files through a simple questionnaire, and the system automatically processes everything \- from extraction to vector database storage.

### **Core Concept: Smart Questionnaire Approach**

Instead of trying to auto-detect what's in uploaded files (which is error-prone and expensive), we ask users directly through a simple wizard:

* What type of file are you uploading?
* What's the content structure? (FAQ, data table, document, etc.)
* What category does it belong to?
* What language is it in?

This approach is simpler, more accurate, and faster than complex machine learning detection systems.

## **2\. System Architecture**

### **High-Level Flow**

User uploads file \+ answers questions
    ↓
API receives and creates processing job
    ↓
Background worker picks up job
    ↓
Processing Orchestrator coordinates:
  1\. Extract content from file
  2\. Analyze structure
  3\. Route to appropriate processor
  4\. Create chunks with metadata
  5\. Generate embeddings
  6\. Upload to Pinecone vector DB
  7\. Verify and report results
    ↓
User sees success report with tracking ID

### **Component Architecture**

**Frontend Layer**

* `admin.html` \- Upload interface with questionnaire wizard
* `admin.js` \- Handles file upload, progress tracking, result display

**API Layer**

* `admin_routes.py` \- FastAPI endpoints for upload, status, updates
* `job_manager.py` \- Manages processing job state and lifecycle

**Processing Layer** (Background Workers)

* `processing_worker.py` \- Async worker that processes jobs from queue
* `orchestrator.py` \- Coordinates all processing steps

**Extraction Layer**

* `file_type_router.py` \- Routes to correct extractor based on file type
* Individual extractors: `json_extractor.py`, `excel_extractor.py`, `pdf_extractor.py`, etc.

**Analysis Layer**

* `structure_analyzer.py` \- Validates and maps content structure
* `language_detector.py` \- Detects English, Marathi, or bilingual content

**Processing Layer**

* `routing_engine.py` \- Selects appropriate processor based on content type
* Specialized processors:
  * `faq_table_processor.py` \- For FAQ in table format
  * `faq_document_processor.py` \- For FAQ in document format
  * `tabular_processor.py` \- For standard data tables
  * `directory_processor.py` \- For officer/contact directories
  * `text_processor.py` \- For narrative documents
  * `web_content_processor.py` \- For scraped web content

**Enrichment Layer**

* `metadata_enricher.py` \- Adds metadata based on user selections
* `special_elements.py` \- Extracts URLs, phone numbers, emails
* `quality_validator.py` \- Validates chunk quality

**Vector Database Layer**

* `embedder.py` \- Generates embeddings using multilingual-e5-base model
* `vector_preparer.py` \- Formats vectors for Pinecone
* `pinecone_upserter.py` \- Uploads vectors to Pinecone
* `verifier.py` \- Verifies successful upload

**Utilities**

* `id_generator.py` \- Creates stable IDs for tracking
* `report_generator.py` \- Creates detailed processing reports
* `file_handler.py` \- File operations (save, delete, validate)
* `logger.py` \- Logging configuration

### **Data Flow Example (JSON FAQ Upload)**

1. **User Input**

   * Uploads `faq_data.xlsx`
   * Selects: Excel → FAQ Table → Bilingual → FAQ Category
2. **Extraction**

   * Excel extractor reads file
   * Finds 50 Q\&A pairs in columns: Q\_EN, A\_EN, Q\_MR, A\_MR
3. **Processing**

   * FAQ Table Processor creates 3 chunks per Q\&A:
     * English only chunk
     * Marathi only chunk
     * Bilingual combined chunk
   * Total: 150 chunks
4. **Enrichment**

   * Adds metadata: category, language, importance score, source info
   * Extracts any URLs or contact info
5. **Embedding**

   * Generates 768-dimensional embeddings for each chunk
   * Uses multilingual-e5-base model
6. **Storage**

   * Uploads 150 vectors to Pinecone
   * Each vector includes text, embedding, and metadata
7. **Verification**

   * Queries Pinecone to confirm vectors exist
   * Tests sample retrieval
   * Generates success report

## **3\. Content Structures & Questionnaire Design**

### **Why This Section Matters**

Government data comes in many different formats and structures. Understanding all possible cases helps us:

* Design the right questionnaire questions
* Build specialized processors for each case
* Route content to the appropriate handler
* Ensure high-quality processing for all types

### **3.1 PDF File Structures**

PDFs are complex because they can contain various content types. Here are all the cases we need to handle:

#### **3.1.1 Pure Text Document**

* **Example**: Policy document, circular, notification
* **Structure**: Headings \+ paragraphs \+ sections
* **Characteristics**: No tables or structured data
* **Processing Strategy**: Semantic chunking with section preservation

#### **3.1.2 Document with Tables**

* **Example**: Officer contact list with narrative sections
* **Structure**: Paragraphs \+ embedded tables
* **Characteristics**: Tables are part of document flow
* **Processing Strategy**: Extract text and tables separately, then merge

#### **3.1.3 Pure Tabular Document**

* **Example**: Entire PDF is just tables
* **Structure**: Only tables, minimal text
* **Characteristics**: Like an Excel sheet in PDF format
* **Processing Strategy**: Extract as table data, treat like CSV

#### **3.1.4 FAQ Document**

* **Example**: Q\&A format document
* **Structure**: Question-Answer pairs (may be bilingual)
* **Processing Strategy**: Pattern matching for Q\&A, create separate chunks per FAQ

#### **3.1.5 Form/Template Document**

* **Example**: Application form, registration form
* **Structure**: Form fields, labels, instructions
* **Processing Strategy**: Extract field names and instructions as searchable content

#### **3.1.6 Scanned Document**

* **Example**: Old scanned paper documents
* **Structure**: Images (needs OCR)
* **Processing Strategy**: OCR with pytesseract, then text processing

#### **3.1.7 Mixed Complex Document**

* **Example**: Annual report, comprehensive guide
* **Structure**: Text \+ Tables \+ Images \+ Charts \+ Lists
* **Characteristics**: Most complex case
* **Processing Strategy**: Multi-pass extraction with element detection

### **3.2 Excel/CSV File Structures**

Excel files have even more variety because users organize data differently. Here are all the cases:

#### **3.2.1 Simple Data Table (Most Common)**

* **Structure**: Headers in first row \+ data rows

**Example**: Name     | Position    | Contact   | EmailJohn     | Manager     | 123-456   | john@example.comMary     | Supervisor  | 789-012   | mary@example.com

* 
* **Characteristics**: All columns are data fields
* **Processing Strategy**: Convert each row to searchable text chunk

#### **3.2.2 Multi-Sheet Workbook**

* **Structure**: Different sheets with different structures
* **Examples**:
  * Sheet 1: Officials table
  * Sheet 2: FAQ content
  * Sheet 3: Policy text
* **Processing Strategy**: User selects which sheets to process, each routed separately

#### **3.2.3 FAQ in Table Format**

* **Structure**: 2 or 4 columns (Question, Answer, Question\_MR, Answer\_MR)

**Example**: Question              | Answer          | प्रश्न          | उत्तरHow to apply?         | Fill form...    | कसे अर्ज करावा? | फॉर्म भरा...What documents needed?| ID proof...     | कागदपत्रे?      | ओळखपत्र...

* 
* **Processing Strategy**: Create 3 chunks per row (EN, MR, Bilingual)

#### **3.2.4 Directory/Contact List**

* **Structure**: Name, Position, Department, Phone, Email, Office
* **Characteristics**: Repeated pattern for each person
* **Processing Strategy**: Create person-centric chunks with search variations

#### **3.2.5 Services Catalog**

* **Structure**: Service Name, Description, Link, Department, Category
* **Characteristics**: Each row is a service
* **Processing Strategy**: Create detailed service chunks with metadata

#### **3.2.6 Hierarchical Data**

* **Structure**: Parent-child relationships
* **Example**: Department → Sub-department → Officials
* **Characteristics**: May use indentation or level columns
* **Processing Strategy**: Preserve hierarchy in metadata and chunk text

#### **3.2.7 Mixed Content in Cells**

* **Structure**: Some cells have long paragraphs, not just data
* **Characteristics**: Like a document written in Excel cells, no clear table structure
* **Processing Strategy**: Detect long-form text and use text processor

#### **3.2.8 Pivot Table or Summary Sheet**

* **Structure**: Aggregated data with merged cells
* **Characteristics**: Complex layout, not straightforward rows
* **Processing Strategy**: User guidance required, may need manual preprocessing

#### **3.2.9 Data with Merged Cells**

* **Structure**: Some cells span multiple rows/columns
* **Characteristics**: Header rows spanning multiple columns
* **Processing Strategy**: Unmerge cells and preserve relationships

#### **3.2.10 Multiple Tables in One Sheet**

* **Structure**: Sheet has Table 1, then blank rows, then Table 2
* **Characteristics**: Different tables with different structures
* **Processing Strategy**: Detect table boundaries, process separately

### **3.3 JSON File Structures**

JSON files are the most structured but still have variations:

#### **3.3.1 Array of Objects (Most Common)**

**Structure**: \[  {"name": "John", "position": "Manager", "contact": "123"},  {"name": "Mary", "position": "Supervisor", "contact": "456"}\]

* 
* **Characteristics**: Each object is like a table row
* **Processing Strategy**: Treat like tabular data, one chunk per object

#### **3.3.2 Nested Objects**

**Structure**: {  "officials": {    "marathi": \[...\],    "english": \[...\]  },  "metadata": {...}}

* 
* **Characteristics**: Hierarchical structure
* **Processing Strategy**: Flatten structure, preserve relationships in metadata

#### **3.3.3 Web Scraping Output**

**Structure**: {  "url": "...",  "title": "...",  "content": "...",  "links": \[...\]}

* 
* **Characteristics**: Like your existing scraped data
* **Processing Strategy**: Extract content field, semantic chunking, preserve URL

#### **3.3.4 API Response Format**

**Structure**: {  "status": "success",  "data": \[...\],  "pagination": {...}}

* 
* **Characteristics**: Standard API wrapper
* **Processing Strategy**: Extract data field, process contents

### **3.4 Text/Markdown File Structures**

Text files require pattern recognition:

#### **3.4.1 Pure Narrative Text**

* **Example**: Policy description, guidelines
* **Structure**: Paragraphs and headings
* **Processing Strategy**: Semantic chunking with heading preservation

#### **3.4.2 Structured Markdown**

* **Example**: README, documentation
* **Structure**: \# Headings, lists, tables, code blocks
* **Processing Strategy**: Parse markdown, preserve structure

#### **3.4.3 FAQ in Text Format**

**Structure**: Q: Question 1?A: Answer 1Q: Question 2?A: Answer 2

* 
* **Processing Strategy**: Pattern matching for Q\&A pairs

#### **3.4.4 Directory in Text Format**

**Structure**: Name: John SmithPosition: ManagerContact: 123-456Name: Mary JohnsonPosition: SupervisorContact: 789-012

* 
* **Processing Strategy**: Pattern matching for repeated structures

#### **3.4.5 Mixed Content**

* **Characteristics**: Paragraphs \+ lists \+ embedded data, no clear structure
* **Processing Strategy**: Use universal processor with conservative chunking

### **3.5 Web URL Content Types**

Web pages are the most complex due to dynamic content:

#### **3.5.1 Article/Blog Post**

* **Structure**: Title, paragraphs, images
* **Characteristics**: Single cohesive narrative
* **Processing Strategy**: Extract main content area, semantic chunking

#### **3.5.2 Table-Heavy Page**

* **Structure**: Mostly HTML tables
* **Characteristics**: Like a data directory
* **Processing Strategy**: Extract tables, treat like CSV data

#### **3.5.3 Interactive Page with Dropdowns**

* **Structure**: Hidden content in dropdowns, accordions
* **Characteristics**: Needs interaction to reveal
* **Processing Strategy**: Selenium automation to click and expand

#### **3.5.4 Multi-Tab Interface**

* **Structure**: Content split across tabs
* **Characteristics**: Need to click each tab
* **Processing Strategy**: Selenium to iterate through tabs

#### **3.5.5 Infinite Scroll Page**

* **Structure**: Content loads as you scroll
* **Characteristics**: Like news feed
* **Processing Strategy**: Selenium with scroll automation

#### **3.5.6 Service Pages with Forms**

* **Structure**: Description \+ application form
* **Characteristics**: Forms have fields and instructions
* **Processing Strategy**: Extract both description and form structure

#### **3.5.7 FAQ Page**

* **Structure**: Collapsible Q\&A sections
* **Characteristics**: May use accordion UI
* **Processing Strategy**: Selenium to expand all, extract Q\&A pairs

#### **3.5.8 Directory/Listing Page**

* **Structure**: List of officers, services, etc.
* **Characteristics**: Repeated card/list structure
* **Processing Strategy**: Extract repeated patterns, create structured data

#### **3.5.9 Complex Mixed Page**

* **Structure**: Article \+ sidebar \+ tables \+ embedded widgets
* **Characteristics**: Most government websites
* **Processing Strategy**: User selects which elements to extract

#### **3.5.10 PDF/Document Download Page**

* **Structure**: Links to download PDFs
* **Characteristics**: May need to extract those PDFs too
* **Processing Strategy**: Download PDFs, process separately

## **4\. Complete Questionnaire Flow**

The questionnaire adapts based on previous answers. Here's the complete decision tree:

### **Step 1: Source Type (Always First)**

**Question**: "What type of input are you providing?"

**Options**:

* File Upload (PDF, Excel, CSV, Text, JSON, Word)
* Website URL
* Multiple Files (Batch Upload)
* Direct Text Paste

---

### **Step 2: File Type (If File Upload Selected)**

**Question**: "What type of file are you uploading?"

**Options**:

* PDF Document
* Excel Workbook (.xlsx, .xls)
* CSV File
* JSON File
* Text/Markdown (.txt, .md)
* Word Document (.docx, .doc)

---

### **Step 3: Content Structure (Varies by File Type)**

#### **If PDF Selected:**

**Question**: "What type of content is in your PDF?"

**Options**:

* Text Document (Articles, policies, guidelines with paragraphs)
* Document with Tables (Mix of text and tables)
* Mostly Tables (Directory, lists, data tables)
* FAQ Document (Question-Answer format)
* Scanned Document (Needs OCR \- older scanned papers)
* Form/Application (Form fields and instructions)
* Complex Mix (All of the above \- let system auto-detect)

**Additional Questions**:

If "Document with Tables" or "Mostly Tables" selected:

* **Sub-question**: "What do the tables contain?"
  * Officer/Staff Directory
  * Services List
  * Contact Information
  * Statistical/Reference Data
  * Other: \_\_\_

If "FAQ Document" selected:

* **Sub-question**: "Is it bilingual (English \+ Marathi)?"
  * Yes, parallel questions and answers
  * No, single language
  * Mixed (some bilingual, some not)

#### **If Excel/CSV Selected:**

**Question**: "How is your data organized?"

**Options**:

* **Standard Data Table**
  * First row has column headers
  * Each row is a record/entry
  * All data is in columns
* **FAQ Table**
  * Columns: Question, Answer (maybe bilingual)
  * Each row is one Q\&A pair
* **Multiple Sheets with Different Content**
  * Different sheets have different structures
  * Need to process each sheet separately
* **Directory/Contact List**
  * Name, Position, Contact pattern
  * Like a phone book
* **Service Catalog**
  * Service name, description, links
  * Each row is a service
* **Text Content in Cells**
  * Long paragraphs written in cells
  * Not a traditional data table
* **Complex Layout**
  * Merged cells, multiple tables in one sheet
  * Irregular structure

**Additional Questions**:

**For Standard Data Table**:

1. "What does each row represent?"

   * Government Official/Staff Member
   * Service/Scheme
   * Office/Department
   * Contact Information
   * General Data
   * Other: \_\_\_
2. "Are there any columns with special content?" (Multiple selection)

   * URLs/Website Links
   * Email Addresses
   * Phone Numbers
   * Postal Addresses
   * Date Information
   * File Attachments/References
3. "Is the data bilingual?"

   * Yes, some columns English, some Marathi
   * Yes, parallel columns (Name & नाव, Position & पद)
   * No, single language throughout
   * Mixed

**For Multiple Sheets**:

1. "How many sheets need processing?"

   * All sheets
   * Specific sheets (let me select)
2. "For each sheet, what type of content?" (Show sheet names, let user classify)

   * Sheet 1: \[Dropdown with options\]
   * Sheet 2: \[Dropdown with options\]
   * Sheet 3: \[Dropdown with options\]

**For FAQ Table**:

"Column structure?"

* 2 columns: Question, Answer
* 4 columns: Question\_EN, Answer\_EN, Question\_MR, Answer\_MR
* Other arrangement: \_\_\_

#### **If JSON Selected:**

**Question**: "What is the JSON structure?"

**Options**:

* Array of Objects (Each object is like a table row)
* Nested Object (Hierarchical data structure)
* Web Scraping Output (Has url, title, content fields)
* API Response (Has status, data, metadata)
* Not Sure (Let me upload and preview)

**Additional Question**:

"What does the data represent?"

* Officials/Staff Directory
* Services/Schemes
* Web Content (scraped articles)
* Contact Information
* General Data
* Other: \_\_\_

#### **If Text/Markdown Selected:**

**Question**: "What format is the text in?"

**Options**:

* Narrative Document (Paragraphs, headings, continuous text)
* Structured Markdown (Has \# headings, lists, tables)
* FAQ Format (Q: A: pattern)
* Directory Listing (Name, Position, Contact pattern repeated)
* Mixed Content (Various types)

**Additional Question**:

"Is it bilingual?"

* Yes, English and Marathi mixed
* No, single language

#### **If URL Selected:**

**Question**: "What type of web page is this?"

**Options**:

* Article/Blog Post (News, article, narrative content)
* Data Table Page (Page is mostly HTML tables)
* Directory/Listing (List of officers, services, departments)
* FAQ Page (Question-answer sections)
* Service Description (Government service details)
* Interactive Page (Has dropdowns, tabs, hidden content)
* Form Page (Application form with fields)
* Complex Page (Mix of everything)

**Additional Questions**:

**For Interactive Page**:

"What type of interactive elements?" (Multiple selection)

* Dropdown menus (need to click to see options)
* Accordion sections (collapsible content)
* Tab interface (content in tabs)
* Infinite scroll (content loads as you scroll)
* Modal popups (click to open popup)

**For Complex Page**:

"What elements should we extract?" (Multiple selection)

* Main article/text content
* All tables on page
* Sidebar content
* All links
* Contact information
* Embedded documents
* Everything

**For All URL Types**:

"Does the page have a login/authentication?"

* No, public page
* Yes, needs login (I'll provide credentials separately)

---

### **Step 4: Language (Always Ask)**

**Question**: "What language is the content in?"

**Options**:

* English only
* Marathi only
* Bilingual (Both English and Marathi)
* Multiple languages (English, Marathi, Hindi, etc.)
* Auto-detect

**If Bilingual Selected**:

"How is bilingual content arranged?"

* Parallel (English section, then Marathi section)
* Interleaved (English and Marathi mixed together)
* Columnar (English columns and Marathi columns)

---

### **Step 5: Category (Always Ask)**

**Question**: "What category does this data belong to?"

**Options**:

* Government Officials/Staff
* Services/Schemes
* Policies/Regulations/Acts
* Contact Information/Directory
* FAQ/Help Content
* News/Announcements
* Forms/Applications
* Statistical/Reference Data
* General Information
* Other: \_\_\_

---

### **Step 6: Special Elements (Always Ask)**

**Question**: "Does your data contain any of these special elements?" (Multiple selection)

**Options**:

* URLs/Website Links (Important to preserve for retrieval)
* Email Addresses
* Phone Numbers
* Postal Addresses
* Dates (Important dates, deadlines)
* File References (References to other documents/PDFs)
* None of the above

**If URLs Selected**:

"How should URLs be handled?"

* Keep as reference in text
* Also create separate searchable entries for URLs
* Both (recommended)

---

### **Step 7: Processing Preferences (Optional, Advanced)**

**Question**: "Any specific processing preferences?" (Collapsible advanced section)

**Options**:

**Chunking Size**:

* Small chunks (256 tokens) \- Better for precise answers
* Medium chunks (512 tokens) \- Default, balanced
* Large chunks (768 tokens) \- Better for context

**Importance Level**:

* Critical (High priority in search results)
* Normal (Standard priority)
* Low (Background reference)

**Update Behavior**:

* Add as new data (append)
* Replace existing data from same source
* Merge with existing data

---

### **Questionnaire to Processing Pipeline Mapping**

Here's how user selections map to specific processors:

| User Selections                      | Processing Pipeline                                  |
| ------------------------------------ | ---------------------------------------------------- |
| PDF\+ Text Document \+ English       | TextProcessor with semantic chunking                 |
| PDF\+ FAQ Document \+ Bilingual      | FAQProcessor with bilingual splitting                |
| PDF\+ Mostly Tables \+ Officers      | TabularProcessor for tables\+ TextProcessor for text |
| Excel\+ Standard Table \+ Services   | TabularProcessor with service metadata               |
| Excel\+ FAQ Table \+ Bilingual 4-col | FAQProcessor specialized for tabular FAQ             |
| Excel\+ Multiple Sheets              | Per-sheet routing based on user classification       |
| JSON\+ Array of Objects \+ Officials | JSONTableProcessor (treat like table)                |
| URL\+ Interactive \+ Dropdowns       | SeleniumExtractor\+ dynamic content handler          |
| URL\+ Article \+ English             | WebContentExtractor\+ TextProcessor                  |
| Text\+ FAQ Format \+ Bilingual       | FAQProcessor with text parsing                       |

## **5\. Tech Stack**

### **Backend**

* **Python 3.10+** \- Core language
* **FastAPI** \- API framework
* **Asyncio** \- Background job processing
* **Pandas** \- Excel/CSV processing
* **PyPDF2 / pdfplumber** \- PDF extraction
* **Beautiful Soup / Selenium** \- Web scraping
* **langdetect** \- Language detection
* **sentence-transformers** \- Embedding generation (multilingual-e5-base)

### **Vector Database**

* **Pinecone** \- Vector storage and similarity search
* **768-dimensional embeddings**
* **Embedding model: intfloat/multilingual-e5-base**

### **Frontend**

* **Vanilla HTML/CSS/JavaScript** \- Simple, no frameworks needed
* **Fetch API** \- HTTP requests
* **Modern CSS** \- Clean, responsive design

### **File Processing**

* **JSON** \- Native Python json library
* **Excel/CSV** \- pandas, openpyxl
* **PDF** \- PyPDF2, pdfplumber, pytesseract (OCR)
* **Text/Markdown** \- Built-in text processing
* **Web** \- Selenium WebDriver for dynamic content

### **Utilities**

* **uuid** \- Unique ID generation
* **hashlib** \- Stable content hashing
* **datetime** \- Timestamp tracking
* **logging** \- Comprehensive logging

## **6\. Development Strategy: Incremental by File Type**

### **Why This Approach?**

Instead of building everything at once, we build the complete pipeline for ONE file type, test thoroughly, then add the next type. This approach:

* Reduces complexity and debugging time
* Provides working functionality faster
* Makes testing easier and more focused
* Allows early user feedback on core features

### **File Type Priority Order**

1. **JSON** \- Easiest (already structured, no parsing complexity)
2. **Excel/CSV** \- Common and important for tabular data
3. **Text/Markdown** \- Simple text processing
4. **PDF** \- More complex but necessary
5. **URL** \- Most complex (dynamic content, interaction needed)

## **7\. Development Phases**

### **Phase 0: Foundation Setup (2-3 days)**

**Goal**: Build all shared components that work for ALL file types

**Scripts to Build** (14 scripts):

* Configuration management (`config.py`)
* Logging setup (`logger.py`)
* File operations (`file_handler.py`)
* ID generation (`id_generator.py`)
* Job management (`job_manager.py`)
* Language detection (`language_detector.py`)
* Metadata enrichment (`metadata_enricher.py`)
* Special element extraction (`special_elements.py`)
* Quality validation (`quality_validator.py`)
* Embedding generation (`embedder.py`)
* Vector preparation (`vector_preparer.py`)
* Pinecone upserting (`pinecone_upserter.py`)
* Upload verification (`verifier.py`)
* Report generation (`report_generator.py`)

**Deliverable**: All utility scripts ready and tested

---

### **Phase 1: JSON Support (1.5 weeks)**

**Goal**: Complete end-to-end working system for JSON files ONLY

#### **Sub-Phase 1.1: JSON Extraction (2 days)**

* Build base extractor class
* Build JSON-specific extractor
* Support 3 JSON structures:
  * Array of objects (most common)
  * Nested objects
  * Web scraping format
* Test with sample JSON files

#### **Sub-Phase 1.2: JSON Processing (3 days)**

* Build routing engine to select processors
* Build processors:
  * Tabular processor (treat JSON array as table)
  * Directory processor (for officials/contacts)
  * Web content processor (for scraped content)
  * Universal processor (fallback)
* Test each processor

#### **Sub-Phase 1.3: Integration & API (2 days)**

* Build orchestrator to coordinate all steps
* Build background worker for async processing
* Build API endpoints:
  * `POST /api/admin/upload` \- Upload JSON file
  * `GET /api/admin/job/{job_id}` \- Check processing status
* Integrate with existing FastAPI server

#### **Sub-Phase 1.4: Frontend (2 days)**

* Build upload interface with questionnaire
* Add progress tracking with live updates
* Display success report with statistics
* Save data source ID for future updates

#### **Sub-Phase 1.5: Testing & Documentation (2 days)**

* Write integration tests
* Test with various JSON structures
* Fix bugs
* Document Phase 1 completion

**Deliverable**: Fully working system for JSON files ✓

---

### **Phase 2: Excel/CSV Support (1 week)**

**What's New**:

* Excel extractor (`excel_extractor.py`)
* FAQ table processor (`faq_table_processor.py`)
* Multi-sheet handling
* Merged cell handling
* Update file type router
* Update frontend with Excel-specific options

**Testing Focus**:

* Various Excel structures
* Multi-sheet workbooks
* FAQ tables (your existing FAQ\_document.xlsx)
* Bilingual column handling

**Deliverable**: JSON \+ Excel/CSV support ✓

---

### **Phase 3: Text/Markdown Support (4-5 days)**

**What's New**:

* Text extractor (`text_extractor.py`)
* FAQ document processor (for Q\&A text patterns)
* Markdown parsing
* Update routing and frontend

**Testing Focus**:

* Plain text files
* Markdown documents
* Text-based FAQs
* Various formatting styles

**Deliverable**: JSON \+ Excel \+ Text support ✓

---

### **Phase 4: PDF Support (1 week)**

**What's New**:

* PDF extractor (`pdf_extractor.py`)
* Text extraction with positions
* Table extraction from PDFs
* OCR for scanned documents
* Layout detection
* Update frontend

**Testing Focus**:

* Text PDFs
* PDFs with tables
* Scanned documents (OCR)
* Mixed content PDFs
* Various PDF structures

**Deliverable**: JSON \+ Excel \+ Text \+ PDF support ✓

---

### **Phase 5: URL/Web Scraping (1.5 weeks)**

**What's New**:

* Web extractor with Selenium (`web_extractor.py`)
* Dynamic content handling
* Interactive element handling (dropdowns, tabs)
* Update frontend

**Testing Focus**:

* Static web pages
* Dynamic content pages
* Pages with tabs/accordions
* Various government websites

**Deliverable**: Complete system with all file types ✓

---

## **8\. Project Structure**

DMA\_BOT/
├── src/
│   ├── data\_manager/
│   │   ├── \_\_init\_\_.py
│   │   │
│   │   ├── api/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── admin\_routes.py          \# API endpoints
│   │   │   └── job\_manager.py           \# Job state management
│   │   │
│   │   ├── workers/
│   │   │   ├── \_\_init\_\_.py
│   │   │   └── processing\_worker.py     \# Background processing
│   │   │
│   │   ├── core/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── orchestrator.py          \# Main coordinator
│   │   │   └── config.py                \# Configuration
│   │   │
│   │   ├── extractors/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── base\_extractor.py        \# Base class
│   │   │   ├── json\_extractor.py        \# Phase 1
│   │   │   ├── excel\_extractor.py       \# Phase 2
│   │   │   ├── text\_extractor.py        \# Phase 3
│   │   │   ├── pdf\_extractor.py         \# Phase 4
│   │   │   ├── web\_extractor.py         \# Phase 5
│   │   │   └── file\_type\_router.py      \# Router
│   │   │
│   │   ├── analyzers/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── structure\_analyzer.py    \# Structure validation
│   │   │   └── language\_detector.py     \# Language detection
│   │   │
│   │   ├── routing/
│   │   │   ├── \_\_init\_\_.py
│   │   │   └── routing\_engine.py        \# Processor selection
│   │   │
│   │   ├── processors/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── base\_processor.py        \# Base class
│   │   │   ├── faq\_table\_processor.py   \# FAQ tables
│   │   │   ├── faq\_document\_processor.py \# FAQ documents
│   │   │   ├── tabular\_processor.py     \# Data tables
│   │   │   ├── directory\_processor.py   \# Contact lists
│   │   │   ├── text\_processor.py        \# Narrative text
│   │   │   ├── web\_content\_processor.py \# Web content
│   │   │   └── universal\_processor.py   \# Fallback
│   │   │
│   │   ├── enrichers/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── metadata\_enricher.py     \# Add metadata
│   │   │   └── special\_elements.py      \# Extract URLs, contacts
│   │   │
│   │   ├── validators/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── quality\_validator.py     \# Chunk quality
│   │   │   └── input\_validator.py       \# Input validation
│   │   │
│   │   ├── embedding/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── embedder.py              \# Generate embeddings
│   │   │   └── vector\_preparer.py       \# Format for Pinecone
│   │   │
│   │   ├── database/
│   │   │   ├── \_\_init\_\_.py
│   │   │   ├── pinecone\_upserter.py     \# Upload to Pinecone
│   │   │   └── verifier.py              \# Verify upload
│   │   │
│   │   └── utils/
│   │       ├── \_\_init\_\_.py
│   │       ├── id\_generator.py          \# Generate IDs
│   │       ├── report\_generator.py      \# Create reports
│   │       ├── file\_handler.py          \# File operations
│   │       └── logger.py                \# Logging
│   │
│   └── server.py                        \# Main FastAPI server
│
├── static/
│   ├── admin.html                       \# Upload UI
│   └── admin.js                         \# Frontend logic
│
└── tests/
    ├── test\_json\_extractor.py
    ├── test\_processors.py
    ├── test\_phase1\_integration.py
    └── ...

## **9\. Key Design Decisions**

### **1\. Questionnaire vs Auto-Detection**

**Why questionnaire wins**:

* More accurate (user knows their data best)
* Simpler implementation (no ML needed)
* Faster processing (no detection overhead)
* Transparent (user sees what's happening)
* Cheaper (no LLM costs for detection)
* More reliable (no misclassification)

### **2\. Incremental File Type Development**

**Why one-at-a-time wins**:

* Focused testing reduces bugs
* Earlier working functionality
* Easier debugging
* Progressive complexity
* User feedback earlier
* Lower cognitive load

### **3\. Background Job Processing**

**Why async workers win**:

* File uploads don't timeout
* Better user experience (progress tracking)
* Can handle multiple concurrent uploads
* Failed jobs can retry
* Easy to scale later

### **4\. Specialized Processors**

**Why multiple processors win**:

* Better quality for each content type
* Easier to maintain
* Can optimize per type
* Clear separation of concerns
* Easier to add new types

## **10\. Testing Strategy**

### **Unit Testing**

* Test each extractor independently
* Test each processor independently
* Test utilities (ID generation, validation, etc.)

### **Integration Testing**

* Test complete pipeline for each file type
* Test with real data samples
* Test error handling
* Test edge cases

### **Manual Testing**

* UI walkthrough for each file type
* Verify vectors in Pinecone
* Test retrieval quality
* User acceptance testing

## **11\. Timeline Summary**

| Phase           | Duration            | File Types            | Total Scripts          |
| --------------- | ------------------- | --------------------- | ---------------------- |
| Phase 0         | 2-3 days            | Foundation            | 14 scripts             |
| Phase 1         | 1.5 weeks           | JSON                  | \+13 scripts           |
| Phase 2         | 1 week              | Excel/CSV             | \+2 scripts            |
| Phase 3         | 4-5 days            | Text/Markdown         | \+2 scripts            |
| Phase 4         | 1 week              | PDF                   | \+1 script             |
| Phase 5         | 1.5 weeks           | URL                   | \+1 script             |
| **Total** | **6-7 weeks** | **All formats** | **\~35 scripts** |

## **12\. Success Metrics**

**System is successful when**:

* Admins can upload files without developer help
* Processing completes in under 3 minutes for typical files
* 95%+ chunk quality score
* 100% success rate for properly formatted files
* Uploaded content is retrievable via chatbot
* System handles bilingual content correctly
* Clear error messages for issues
* Users can track and manage their uploads

## **13\. Next Steps**

### **Immediate (Start Phase 0\)**

1. Set up project directory structure
2. Create `config.py` with all constants
3. Build utility scripts (logger, file\_handler, etc.)
4. Set up job management system
5. Test foundation components

### **After Phase 0 (Start Phase 1\)**

1. Build JSON extractor
2. Build JSON processors
3. Build orchestrator
4. Build API endpoints
5. Build frontend
6. Test end-to-end with JSON files

---

**Ready to start building\!** The system is designed to be built incrementally, tested thoroughly, and delivered in working phases rather than all-at-once. The comprehensive questionnaire ensures we handle all real-world content structures while keeping the system maintainable and accurate.
