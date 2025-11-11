# Vector Deletion System - Complete Guide

## Overview

A **generalized, database-agnostic** deletion system for vector databases that works with:
- ✅ **Pinecone**
- ✅ **Qdrant** 
- ✅ **Any future vector DB** (just implement the base adapter interface)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VectorManager (Unified API)                 │
│  All-in-one interface for discovery + deletion                 │
└───────────────────┬──────────────────────┬──────────────────────┘
                    │                      │
        ┌───────────▼───────────┐  ┌──────▼────────────────┐
        │  Discovery Manager    │  │  Deletion Manager     │
        │  - List documents     │  │  - Delete chunks      │
        │  - Search (semantic)  │  │  - Delete documents   │
        │  - Search (metadata)  │  │  - Batch operations   │
        │  - Browse & paginate  │  │  - Preview & verify   │
        └───────────┬───────────┘  └──────┬────────────────┘
                    │                     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Base Adapter       │
                    │  (Abstract Interface)│
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐  ┌──────────▼───────┐  ┌─────────▼────────┐
│ Pinecone       │  │  Qdrant          │  │  Your Custom     │
│ Adapter        │  │  Adapter         │  │  DB Adapter      │
└────────────────┘  └──────────────────┘  └──────────────────┘
```

## Key Features

### 1. **Multiple Discovery Methods**
- **Semantic Search**: Find content by meaning (your original idea)
- **Metadata Search**: Exact matches by filename, category, date
- **Browsing**: List and paginate through all documents
- **Advanced Filters**: Complex queries combining multiple criteria

### 2. **Safety Features**
- **Preview Before Delete**: See what will be deleted
- **Confidence Scores**: Semantic search shows HIGH/MEDIUM/LOW confidence
- **Verification**: Optional post-deletion verification
- **Dry-Run Mode**: Test without actually deleting

### 3. **Batch Operations**
- **Progress Tracking**: Real-time updates for large deletions
- **Error Handling**: Continues on partial failures
- **Detailed Reports**: Know exactly what succeeded/failed

### 4. **Database Agnostic**
- Works with **ANY** vector database
- Same API regardless of backend
- Easy to add new databases

## Quick Start

### Basic Usage

```python
from src.data_manager.database.vector_db_factory import get_vector_db_adapter
from src.data_manager.database.vector_manager import VectorManager

# Initialize (works with any vector DB configured in .env)
db = get_vector_db_adapter()
manager = VectorManager(db)

# Delete a single chunk
result = manager.delete_chunk("chunk_id_123")
print(f"Success: {result.success}, Deleted: {result.deleted_count}")

# Delete entire document
result = manager.delete_document("src_abc123")
print(f"Deleted {result.deleted_count} chunks")

# List all documents
documents = manager.list_all_documents()
for doc in documents:
    print(f"{doc.filename}: {doc.chunk_count} chunks")
```

### Semantic Search Deletion (User Story 1)

```python
from src.data_manager.embedding.embedder_manager import EmbedderManager

# User wants to delete content about "old CEO"
search_text = "John Smith is the CEO"

# Generate embedding
embedder = EmbedderManager.get_embedder()
embedding = embedder.embed_text(search_text)

# Find and preview deletion
result = manager.find_and_delete_by_content(
    text_query=search_text,
    query_embedding=embedding,
    top_k=10,
    auto_select_high_confidence=True,  # Auto-select score > 0.95
    dry_run=True  # Preview first
)

# Show results with confidence levels
for chunk in result['selected_chunks']:
    confidence = chunk.confidence_level.value  # HIGH, MEDIUM, or LOW
    print(f"{confidence}: {chunk.text_preview} (score: {chunk.similarity_score:.3f})")

# Actually delete (after user confirms)
result = manager.find_and_delete_by_content(..., dry_run=False)
```

### Filename-Based Deletion (User Story 2)

```python
# IT Admin deletes specific file
result = manager.find_and_delete_by_filename(
    filename="hr_policy_2024.pdf",
    exact_match=True,
    dry_run=True  # Preview first
)

if result['documents']:
    print(f"Found: {result['documents'][0].filename}")
    print(f"Will delete {result['preview'].total_chunks} chunks")
    
    # Confirm and delete
    result = manager.find_and_delete_by_filename(
        filename="hr_policy_2024.pdf",
        dry_run=False
    )
    print(f"✓ Deleted!")
```

### Browse and Delete (User Story 3)

```python
# Content Manager browses all documents
page_result = manager.browse_documents(page=1, page_size=20)

print(f"Page {page_result.page} of {page_result.total_pages}")
for doc in page_result.items:
    print(f"- {doc.filename} ({doc.chunk_count} chunks)")
    print(f"  Uploaded: {doc.upload_date}")

# User selects documents to delete
selected_ids = ["src_old001", "src_old002"]
preview = manager.get_deletion_preview(source_ids=selected_ids)

# Confirm and delete
result = manager.delete_documents(selected_ids)
```

### Advanced Filtering (User Story 4)

```python
# Data Analyst deletes old archived content
result = manager.delete_old_content(
    before_date="2024-01-01",
    filter_dict={"status": "archived"},  # Additional filter
    dry_run=True
)

print(f"Found {result['count']} old documents")
print(f"Total chunks: {result['preview'].total_chunks}")

# Delete
result = manager.delete_old_content("2024-01-01", dry_run=False)
```

### Duplicate Cleanup (User Story 5)

```python
# Support Engineer finds and removes duplicates
result = manager.cleanup_duplicates(
    keep_strategy="latest",  # Keep most recent version
    dry_run=True
)

for dup in result['duplicates']:
    print(f"{dup['filename']}: {dup['count']} copies")
    for doc in dup['documents']:
        print(f"  - {doc.source_id} (uploaded: {doc.upload_date})")

# Delete duplicates (keeping latest)
result = manager.cleanup_duplicates(keep_strategy="latest", dry_run=False)
```

## API Reference

### VectorManager

Main entry point for all operations.

#### Discovery Methods

```python
manager.list_all_documents(namespace="") -> List[DocumentInfo]
manager.browse_documents(page=1, page_size=20) -> PaginatedResult
manager.search_documents(query: str) -> List[DocumentInfo]
manager.search_by_filename(filename: str, exact=False) -> List[DocumentInfo]
manager.search_by_category(category: str) -> List[DocumentInfo]
manager.get_document_details(source_id: str) -> DocumentInfo
manager.find_duplicates() -> List[Dict]
manager.search_chunks_by_content(text, embedding, top_k=10) -> SearchResult
```

#### Deletion Methods

```python
manager.delete_chunk(chunk_id: str, verify=True) -> DeletionResult
manager.delete_chunks(chunk_ids: List[str]) -> BatchDeletionResult
manager.delete_document(source_id: str, verify=True) -> DeletionResult
manager.delete_documents(source_ids: List[str]) -> BatchDeletionResult
manager.delete_by_filter(filter_dict: Dict, dry_run=False) -> DeletionResult
manager.get_deletion_preview(...) -> DeletionPreview
```

#### Combined Workflows

```python
manager.find_and_delete_by_content(...) -> Dict
manager.find_and_delete_by_filename(...) -> Dict
manager.cleanup_duplicates(...) -> Dict
manager.delete_old_content(before_date: str) -> Dict
```

## Adding a New Vector Database

To add support for a new vector database (e.g., Weaviate, Chroma, Milvus):

1. **Create Adapter Class**:

```python
# src/data_manager/database/weaviate_adapter.py

from .base_adapter import VectorDBAdapter

class WeaviateAdapter(VectorDBAdapter):
    def __init__(self):
        super().__init__()
        # Initialize Weaviate client
    
    # Implement ALL abstract methods from VectorDBAdapter:
    def list_documents(self, namespace, filter_dict, limit):
        # Your Weaviate-specific implementation
        pass
    
    def list_chunks(self, source_id, namespace, limit):
        # Your implementation
        pass
    
    def search_by_metadata(self, filter_dict, namespace, limit):
        # Your implementation
        pass
    
    def delete_vectors(self, vector_ids, namespace):
        # Your implementation
        pass
    
    # ... implement all other abstract methods
```

2. **Register Adapter**:

```python
# src/data_manager/database/vector_db_factory.py

from .weaviate_adapter import WeaviateAdapter

class VectorDBFactory:
    _adapters = {
        'pinecone': PineconeAdapter,
        'qdrant': QdrantAdapter,
        'weaviate': WeaviateAdapter,  # Add here
    }
```

3. **Configure in .env**:

```bash
VECTOR_DB_TYPE=weaviate
VECTOR_DB_API_KEY=your_key
# ... other Weaviate config
```

4. **Done!** All deletion features now work with Weaviate.

## File Structure

```
src/data_manager/database/
├── base_adapter.py           # Abstract interface (ALL DBs must implement)
├── deletion_models.py        # Data models (Result objects)
├── discovery_manager.py      # Discovery service
├── deletion_manager.py       # Deletion service
├── vector_manager.py         # Unified manager
├── pinecone_adapter.py       # Pinecone implementation
├── qdrant_adapter.py         # Qdrant implementation
└── vector_db_factory.py      # Factory for creating adapters

examples/
├── deletion_system_demo.py        # Complete demo (all user stories)
└── simple_deletion_examples.py    # Quick reference examples
```

## Testing

```python
# Test connection
if manager.test_connection():
    print("✓ Connected")

# Get database stats
stats = manager.get_database_stats()
print(f"Total vectors: {stats['total_vectors']}")

# Run demo
python examples/deletion_system_demo.py
```

## Best Practices

### 1. Always Preview First

```python
# ✅ GOOD
preview = manager.get_deletion_preview(source_ids=[...])
if preview.warnings:
    print("⚠️  Warnings:", preview.warnings)
# User confirms
result = manager.delete_documents([...])

# ❌ BAD - No preview
result = manager.delete_documents([...])
```

### 2. Check Confidence Scores

```python
# ✅ GOOD - Filter by confidence
for chunk in search_result.chunks:
    if chunk.confidence_level == ConfidenceLevel.HIGH:
        # Safe to auto-delete
        pass
    else:
        # Require user review
        pass

# ❌ BAD - Delete all matches without checking
manager.delete_chunks([c.chunk_id for c in search_result.chunks])
```

### 3. Use Batch Operations

```python
# ✅ GOOD - Batch operation
result = manager.delete_documents(source_ids, progress_callback=print_progress)

# ❌ BAD - Individual deletions
for source_id in source_ids:
    manager.delete_document(source_id)  # Slow!
```

### 4. Handle Errors

```python
result = manager.delete_documents(source_ids)

if result.success:
    print(f"✓ Deleted {result.total_deleted} documents")
else:
    print(f"⚠️  Partial success: {result.total_deleted}/{result.total_requested}")
    print(f"Errors: {result.errors}")
```

## User Stories Mapping

| User Story | Method | Description |
|------------|--------|-------------|
| **Story 1**: Marketing Manager | `find_and_delete_by_content()` | Semantic search for "old CEO info" |
| **Story 2**: IT Admin | `find_and_delete_by_filename()` | Exact filename match deletion |
| **Story 3**: Content Manager | `browse_documents()` + `delete_documents()` | Visual browsing and selection |
| **Story 4**: Data Analyst | `delete_old_content()` | Advanced filtering by date/status |
| **Story 5**: Support Engineer | `cleanup_duplicates()` | Find and remove duplicate uploads |

## Advanced Features

### Progress Callbacks

```python
def my_progress(current, total):
    percent = (current / total) * 100
    print(f"Progress: [{current}/{total}] {percent:.0f}%")

result = manager.delete_documents(
    source_ids,
    progress_callback=my_progress
)
```

### Custom Filters

```python
# Combine multiple filters
filter_dict = {
    "category": "archived",
    "status": "inactive",
    "year": "2023"
}
result = manager.delete_by_filter(filter_dict, dry_run=True)
```

### Document Tree View

```python
# Get full document hierarchy
doc_tree = manager.get_document_details("src_abc123")
print(f"Document: {doc_tree.filename}")
print(f"Chunks: {doc_tree.chunk_count}")
for chunk in doc_tree.chunks:
    print(f"  - {chunk['id']}: {chunk['text'][:50]}...")
```

## Troubleshooting

### Issue: "No documents found"
- Check if vectors were uploaded with proper metadata (source_id, filename)
- Verify namespace is correct
- Try `manager.get_database_stats()` to see if DB has vectors

### Issue: "Deletion claimed success but chunks still exist"
- Enable verification: `manager.delete_document(source_id, verify=True)`
- Check if namespace is correct
- Some DBs have eventual consistency (wait a moment and check again)

### Issue: "Search returns too many irrelevant results"
- Lower `top_k` parameter
- Filter by confidence: only use HIGH confidence results
- Use metadata search instead of semantic search for exact matches

## Performance Tips

1. **Use batch operations** for deleting multiple items
2. **Limit `top_k`** in semantic search to reduce query time
3. **Use metadata search** when possible (faster than semantic)
4. **Cache document listings** if browsing frequently

## Security Considerations

1. **Always require confirmation** for bulk deletions
2. **Log all deletion operations** for audit trail
3. **Implement soft delete** for critical data (mark as deleted, don't actually delete)
4. **Use dry_run** mode in production workflows
5. **Add authentication/authorization** before exposing deletion API

## Next Steps

1. ✅ System is fully implemented and working
2. ✅ Works with Pinecone and Qdrant
3. ✅ Generalized for any vector database
4. 📋 Optional: Add CLI tool for interactive deletion
5. 📋 Optional: Build web UI for visual management
6. 📋 Optional: Add soft delete functionality
7. 📋 Optional: Implement undo/rollback features

## Support

For issues or questions:
- Check `examples/deletion_system_demo.py` for working examples
- Review `examples/simple_deletion_examples.py` for quick reference
- Examine adapter implementations for DB-specific details

---

**Built with flexibility in mind** - works with any vector database, now and in the future! 🚀

