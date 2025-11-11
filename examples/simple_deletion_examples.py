"""
Simple Deletion Examples
========================

Quick examples for common deletion tasks.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_manager.database.vector_db_factory import get_vector_db_adapter
from src.data_manager.database.vector_manager import VectorManager


# Initialize
db = get_vector_db_adapter()
manager = VectorManager(db)


# ============================================================================
# EXAMPLE 1: Delete a single chunk
# ============================================================================
def delete_single_chunk():
    """Delete one specific chunk"""
    chunk_id = "src_abc123_chunk0001_xyz"
    
    result = manager.delete_chunk(chunk_id)
    
    if result.success:
        print(f"✓ Deleted chunk {chunk_id}")
    else:
        print(f"✗ Failed: {result.message}")


# ============================================================================
# EXAMPLE 2: Delete an entire document
# ============================================================================
def delete_document():
    """Delete all chunks of a document"""
    source_id = "src_abc123"
    
    result = manager.delete_document(source_id)
    
    if result.success:
        print(f"✓ Deleted document {source_id} ({result.deleted_count} chunks)")
    else:
        print(f"✗ Failed: {result.message}")


# ============================================================================
# EXAMPLE 3: Delete by filename
# ============================================================================
def delete_by_filename():
    """Find and delete document by filename"""
    filename = "old_document.pdf"
    
    # Preview first
    result = manager.find_and_delete_by_filename(
        filename=filename,
        exact_match=True,
        dry_run=True  # Preview only
    )
    
    if result['documents']:
        print(f"Found: {result['documents'][0].filename}")
        print(f"Will delete {result['preview'].total_chunks} chunks")
        
        # Uncomment to actually delete:
        # result = manager.find_and_delete_by_filename(filename, dry_run=False)
        # print(f"✓ Deleted {result['deletion_result'].total_deleted} documents")
    else:
        print(f"No document found: {filename}")


# ============================================================================
# EXAMPLE 4: Delete by semantic search
# ============================================================================
def delete_by_content():
    """Find and delete chunks by content similarity"""
    from src.data_manager.embedding.embedder import get_embedder
    
    # What user wants to delete
    search_text = "old CEO information"
    
    # Generate embedding
    embedder = get_embedder()
    embedding = embedder.embed_text(search_text).tolist()
    
    # Find similar chunks (preview)
    result = manager.find_and_delete_by_content(
        text_query=search_text,
        query_embedding=embedding,
        top_k=5,
        auto_select_high_confidence=True,  # Auto-select score > 0.95
        dry_run=True
    )
    
    print(f"Found {result['search_result'].total_matches} matches")
    print(f"Auto-selected {len(result['selected_chunks'])} high-confidence chunks")
    
    # Show results
    for chunk in result['selected_chunks']:
        print(f"  - {chunk.chunk_id}: {chunk.text_preview[:60]}... (score: {chunk.similarity_score:.3f})")
    
    # Uncomment to delete:
    # result = manager.find_and_delete_by_content(..., dry_run=False)


# ============================================================================
# EXAMPLE 5: Batch delete multiple documents
# ============================================================================
def batch_delete_documents():
    """Delete multiple documents at once"""
    source_ids = [
        "src_old001",
        "src_old002",
        "src_old003"
    ]
    
    # Preview
    preview = manager.get_deletion_preview(source_ids=source_ids)
    print(f"Will delete {preview.total_documents} documents")
    print(f"Total chunks: {preview.total_chunks}")
    
    # Delete with progress
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f"Progress: {current}/{total} ({percent:.0f}%)")
    
    result = manager.delete_documents(
        source_ids,
        progress_callback=progress_callback
    )
    
    print(f"✓ Deleted {result.total_deleted}/{result.total_requested} documents")
    if result.errors:
        print(f"✗ {result.total_failed} failed")


# ============================================================================
# EXAMPLE 6: List and select
# ============================================================================
def list_and_select():
    """Browse documents and select for deletion"""
    # List all documents
    documents = manager.list_all_documents()
    
    print(f"Total documents: {len(documents)}\n")
    
    # Show first 5
    for i, doc in enumerate(documents[:5], 1):
        print(f"{i}. {doc.filename}")
        print(f"   ID: {doc.source_id}")
        print(f"   Chunks: {doc.chunk_count}")
        print(f"   Date: {doc.upload_date}\n")
    
    # User selects (example: select first document)
    selected = documents[0]
    
    # Get details
    details = manager.get_document_details(selected.source_id)
    print(f"Selected: {details.filename}")
    print(f"Contains {len(details.chunks)} chunks")
    
    # Delete
    # result = manager.delete_document(selected.source_id)


# ============================================================================
# EXAMPLE 7: Delete old content
# ============================================================================
def delete_old_content():
    """Delete content older than a date"""
    result = manager.delete_old_content(
        before_date="2024-01-01",
        dry_run=True
    )
    
    print(f"Found {result['count']} old documents")
    if result['old_documents']:
        for doc in result['old_documents'][:3]:
            print(f"  - {doc.filename} (uploaded: {doc.upload_date})")
    
    # Uncomment to delete:
    # result = manager.delete_old_content("2024-01-01", dry_run=False)


# ============================================================================
# EXAMPLE 8: Find and delete duplicates
# ============================================================================
def cleanup_duplicates():
    """Find and remove duplicate uploads"""
    result = manager.cleanup_duplicates(
        keep_strategy="latest",  # Keep most recent
        dry_run=True
    )
    
    if result['duplicates']:
        print(f"Found {len(result['duplicates'])} duplicate groups")
        for dup in result['duplicates'][:2]:
            print(f"\n'{dup['filename']}' has {dup['count']} copies:")
            for doc in dup['documents']:
                print(f"  - {doc.source_id} (uploaded: {doc.upload_date})")
    else:
        print("No duplicates found")
    
    # Uncomment to delete:
    # result = manager.cleanup_duplicates(keep_strategy="latest", dry_run=False)


# ============================================================================
# EXAMPLE 9: Search by category and delete
# ============================================================================
def delete_by_category():
    """Delete all documents in a category"""
    category = "archived"
    
    # Find documents
    documents = manager.search_by_category(category)
    
    print(f"Found {len(documents)} documents in category '{category}'")
    
    if documents:
        source_ids = [doc.source_id for doc in documents]
        
        # Preview
        preview = manager.get_deletion_preview(source_ids=source_ids)
        print(f"Will delete {preview.total_chunks} chunks from {preview.total_documents} documents")
        
        # Uncomment to delete:
        # result = manager.delete_documents(source_ids)


# ============================================================================
# EXAMPLE 10: Get deletion preview before any action
# ============================================================================
def always_preview_first():
    """Always preview before deleting"""
    source_ids = ["src_abc123", "src_def456"]
    
    # ALWAYS get preview first
    preview = manager.get_deletion_preview(source_ids=source_ids)
    
    print("=" * 50)
    print("DELETION PREVIEW")
    print("=" * 50)
    print(f"Documents: {preview.total_documents}")
    print(f"Chunks: {preview.total_chunks}")
    print(f"Size: {preview.estimated_size_kb:.2f} KB")
    
    if preview.warnings:
        print("\n⚠️  WARNINGS:")
        for warning in preview.warnings:
            print(f"  - {warning}")
    
    print("\nAffected documents:")
    for doc in preview.affected_documents:
        print(f"  - {doc.filename} ({doc.chunk_count} chunks)")
    
    # User reviews and confirms
    confirm = input("\nType 'DELETE' to confirm: ")
    
    if confirm == "DELETE":
        result = manager.delete_documents(source_ids)
        print(f"\n✓ Deleted {result.total_deleted} documents")
    else:
        print("\n✗ Cancelled")


# ============================================================================
# Run examples
# ============================================================================
if __name__ == "__main__":
    print("Simple Deletion Examples")
    print("=" * 50)
    
    # Test connection
    if manager.test_connection():
        print("✓ Connected to database\n")
        
        # Run any example function:
        # delete_single_chunk()
        # delete_document()
        # delete_by_filename()
        # delete_by_content()
        # batch_delete_documents()
        # list_and_select()
        # delete_old_content()
        # cleanup_duplicates()
        # delete_by_category()
        # always_preview_first()
        
        print("\n✓ Examples ready to use")
        print("Uncomment any function above to run it")
    else:
        print("✗ Failed to connect to database")

