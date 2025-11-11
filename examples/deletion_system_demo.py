"""
Vector Deletion System - Complete Demo
=======================================

This script demonstrates all features of the hybrid deletion system:
1. Discovery methods (list, browse, search)
2. Semantic content search
3. Metadata-based search
4. Deletion with preview
5. Batch operations
6. Combined workflows

The system works with ANY vector database (Pinecone, Qdrant, Weaviate, etc.)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_manager.database.vector_db_factory import get_vector_db_adapter
from src.data_manager.database.vector_manager import VectorManager
from src.data_manager.embedding.embedder import get_embedder


def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def demo_discovery(manager: VectorManager):
    """Demonstrate discovery features"""
    print_section("DISCOVERY FEATURES")
    
    # 1. List all documents
    print("1. LIST ALL DOCUMENTS")
    print("-" * 50)
    documents = manager.list_all_documents()
    print(f"Total documents: {len(documents)}")
    for i, doc in enumerate(documents[:5], 1):  # Show first 5
        print(f"  {i}. {doc.filename} (ID: {doc.source_id})")
        print(f"     Chunks: {doc.chunk_count}, Category: {doc.category}")
    if len(documents) > 5:
        print(f"  ... and {len(documents) - 5} more")
    
    # 2. Browse with pagination
    print("\n2. BROWSE WITH PAGINATION")
    print("-" * 50)
    page_result = manager.browse_documents(page=1, page_size=3)
    print(f"Page {page_result.page} of {page_result.total_pages}")
    print(f"Total documents: {page_result.total_items}")
    for doc in page_result.items:
        print(f"  - {doc.filename} ({doc.chunk_count} chunks)")
    
    # 3. Search by filename
    if documents:
        print("\n3. SEARCH BY FILENAME")
        print("-" * 50)
        # Search for first document's filename
        search_filename = documents[0].filename
        results = manager.search_documents(search_filename)
        print(f"Searching for: '{search_filename}'")
        print(f"Found {len(results)} matches")
    
    # 4. Find duplicates
    print("\n4. FIND DUPLICATE DOCUMENTS")
    print("-" * 50)
    duplicates = manager.find_duplicates()
    if duplicates:
        print(f"Found {len(duplicates)} duplicate groups:")
        for dup in duplicates[:3]:  # Show first 3
            print(f"  - '{dup['filename']}': {dup['count']} copies")
    else:
        print("No duplicates found")
    
    # 5. Get document details
    if documents:
        print("\n5. GET DOCUMENT DETAILS")
        print("-" * 50)
        source_id = documents[0].source_id
        details = manager.get_document_details(source_id)
        if details:
            print(f"Document: {details.filename}")
            print(f"Source ID: {details.source_id}")
            print(f"Chunks: {details.chunk_count}")
            print(f"Upload Date: {details.upload_date}")
            print(f"Category: {details.category}")
            if details.chunks:
                print(f"\nFirst chunk preview:")
                print(f"  ID: {details.chunks[0]['id']}")
                print(f"  Text: {details.chunks[0]['text'][:100]}...")


def demo_semantic_search_deletion(manager: VectorManager, embedder):
    """Demonstrate semantic search for deletion (User Story 1)"""
    print_section("SEMANTIC SEARCH DELETION (User Story 1)")
    
    print("Scenario: User wants to delete chunks about 'old CEO information'\n")
    
    # User input
    search_text = "John Smith is the CEO of TechCorp"
    print(f"User searches for: '{search_text}'")
    
    # Generate embedding
    print("Generating embedding...")
    embedding = embedder.embed_text(search_text).tolist()
    
    # Search for similar content
    print("Searching for similar content...")
    result = manager.find_and_delete_by_content(
        text_query=search_text,
        query_embedding=embedding,
        top_k=5,
        dry_run=True  # Preview only
    )
    
    search_result = result['search_result']
    print(f"\n✓ Found {search_result.total_matches} matches (in {search_result.search_time_seconds:.2f}s)")
    
    # Show results with confidence levels
    print("\nResults:")
    for i, chunk in enumerate(search_result.chunks, 1):
        confidence = chunk.confidence_level.value
        score = chunk.similarity_score
        icon = "✅" if confidence == "high" else "⚠️" if confidence == "medium" else "❌"
        
        print(f"\n[{i}] {icon} {confidence.upper()} Confidence (Score: {score:.3f})")
        print(f"    File: {chunk.metadata.get('filename', 'unknown')}")
        print(f"    Chunk ID: {chunk.chunk_id}")
        print(f"    Text: {chunk.text_preview[:80]}...")
    
    # Show deletion preview
    preview = result['preview']
    print(f"\n⚠️  DELETION PREVIEW:")
    print(f"   Total chunks to delete: {preview.total_chunks}")
    print(f"   Documents affected: {preview.total_documents}")
    if preview.warnings:
        for warning in preview.warnings:
            print(f"   ⚠️  {warning}")
    
    print("\n💡 User would now:")
    print("   1. Review each result")
    print("   2. Unselect low-confidence matches")
    print("   3. Confirm and delete selected chunks")


def demo_filename_deletion(manager: VectorManager):
    """Demonstrate exact filename deletion (User Story 2)"""
    print_section("FILENAME-BASED DELETION (User Story 2)")
    
    print("Scenario: IT Admin wants to delete 'hr_policy_2024.pdf'\n")
    
    # Get all documents first
    documents = manager.list_all_documents()
    
    if not documents:
        print("No documents found in database")
        return
    
    # Use first document as example
    target_filename = documents[0].filename
    print(f"Searching for document: '{target_filename}'")
    
    # Find and preview deletion
    result = manager.find_and_delete_by_filename(
        filename=target_filename,
        exact_match=True,
        dry_run=True
    )
    
    if result['documents']:
        doc = result['documents'][0]
        preview = result['preview']
        
        print(f"\n✓ Found document:")
        print(f"  Filename: {doc.filename}")
        print(f"  Source ID: {doc.source_id}")
        print(f"  Chunks: {doc.chunk_count}")
        print(f"  Upload Date: {doc.upload_date}")
        print(f"  Category: {doc.category}")
        
        print(f"\n⚠️  DELETION PREVIEW:")
        print(f"   This will delete {preview.total_chunks} chunks")
        print(f"   Affected documents: {preview.total_documents}")
        
        print("\n💡 Admin would now confirm to delete the entire document")
    else:
        print(f"No document found with filename: {target_filename}")


def demo_browse_and_delete(manager: VectorManager):
    """Demonstrate browsing for deletion (User Story 3)"""
    print_section("BROWSE & SELECT DELETION (User Story 3)")
    
    print("Scenario: Content Manager wants to explore and clean up old content\n")
    
    # Browse documents
    print("Browsing documents (page 1)...")
    page_result = manager.browse_documents(page=1, page_size=5)
    
    print(f"\n📚 Showing {len(page_result.items)} of {page_result.total_items} documents:\n")
    
    for i, doc in enumerate(page_result.items, 1):
        status = "⚠️  OLD" if doc.upload_date and doc.upload_date < "2024-01-01" else "✅ CURRENT"
        print(f"[{i}] {status}")
        print(f"    {doc.filename}")
        print(f"    Uploaded: {doc.upload_date}")
        print(f"    Chunks: {doc.chunk_count} | Category: {doc.category}")
        print(f"    Source ID: {doc.source_id}")
        print()
    
    print("💡 User would now:")
    print("   1. Check boxes next to documents to delete")
    print("   2. Click 'Delete Selected'")
    print("   3. Review preview")
    print("   4. Confirm deletion")


def demo_advanced_filtering(manager: VectorManager):
    """Demonstrate advanced filtering (User Story 4)"""
    print_section("ADVANCED FILTERING DELETION (User Story 4)")
    
    print("Scenario: Data Analyst wants to delete all archived content before 2024\n")
    
    # Delete old content
    print("Finding content uploaded before 2024-01-01...")
    result = manager.delete_old_content(
        before_date="2024-01-01",
        dry_run=True
    )
    
    print(f"\n✓ Found {result['count']} old documents")
    
    if result['old_documents']:
        print("\nDocuments to delete:")
        for doc in result['old_documents'][:5]:  # Show first 5
            print(f"  - {doc.filename} (uploaded: {doc.upload_date})")
        
        if len(result['old_documents']) > 5:
            print(f"  ... and {len(result['old_documents']) - 5} more")
        
        preview = result['preview']
        if preview:
            print(f"\n⚠️  DELETION PREVIEW:")
            print(f"   Total documents: {preview.total_documents}")
            print(f"   Total chunks: {preview.total_chunks}")
    else:
        print("No old documents found")


def demo_duplicate_cleanup(manager: VectorManager):
    """Demonstrate duplicate cleanup (User Story 5)"""
    print_section("DUPLICATE CLEANUP (User Story 5)")
    
    print("Scenario: Support Engineer wants to find and remove duplicate uploads\n")
    
    # Find duplicates
    result = manager.cleanup_duplicates(
        keep_strategy="latest",
        dry_run=True
    )
    
    duplicates = result['duplicates']
    
    if duplicates:
        print(f"✓ Found {len(duplicates)} duplicate groups:\n")
        
        for dup in duplicates[:3]:  # Show first 3
            print(f"Filename: '{dup['filename']}'")
            print(f"Copies: {dup['count']}")
            for doc in dup['documents']:
                print(f"  - {doc.source_id} (uploaded: {doc.upload_date})")
            print()
        
        print(f"Strategy: Keep LATEST version, delete others")
        print(f"Will delete: {len(result['to_delete'])} documents")
    else:
        print("No duplicates found")


def demo_batch_operations(manager: VectorManager):
    """Demonstrate batch operations"""
    print_section("BATCH OPERATIONS")
    
    print("Scenario: Delete multiple documents efficiently\n")
    
    # Get some documents
    documents = manager.list_all_documents()
    
    if len(documents) >= 2:
        # Select first 2 documents for demo
        source_ids = [documents[0].source_id, documents[1].source_id]
        
        print(f"Selected {len(source_ids)} documents for batch deletion:")
        for sid in source_ids:
            doc = next(d for d in documents if d.source_id == sid)
            print(f"  - {doc.filename} ({doc.chunk_count} chunks)")
        
        # Preview
        print("\nGenerating preview...")
        preview = manager.get_deletion_preview(source_ids=source_ids)
        
        print(f"\n⚠️  BATCH DELETION PREVIEW:")
        print(f"   Documents: {preview.total_documents}")
        print(f"   Total chunks: {preview.total_chunks}")
        print(f"   Estimated size: {preview.estimated_size_kb:.2f} KB")
        
        print("\n💡 With confirmation, this would:")
        print("   1. Delete documents in batch")
        print("   2. Show progress: [===>____] 50%")
        print("   3. Verify each deletion")
        print("   4. Report final results")
    else:
        print("Need at least 2 documents for batch demo")


def demo_database_stats(manager: VectorManager):
    """Show database statistics"""
    print_section("DATABASE STATISTICS")
    
    stats = manager.get_database_stats()
    
    print("Current Database Stats:")
    print(f"  Total vectors: {stats.get('total_vectors', 0)}")
    print(f"  Dimension: {stats.get('dimension', 0)}")
    print(f"  Index fullness: {stats.get('index_fullness', 0):.2%}")
    
    # Count documents
    documents = manager.list_all_documents()
    print(f"  Total documents: {len(documents)}")
    
    if documents:
        total_chunks = sum(doc.chunk_count for doc in documents)
        avg_chunks = total_chunks / len(documents)
        print(f"  Average chunks per document: {avg_chunks:.1f}")


def main():
    """Main demo function"""
    print("\n" + "="*70)
    print("  VECTOR DELETION SYSTEM - COMPLETE DEMO")
    print("  Hybrid approach: Semantic + Metadata + Browsing")
    print("  Works with: Pinecone, Qdrant, Weaviate, Chroma, Milvus")
    print("="*70)
    
    try:
        # Initialize system
        print("\n🔧 Initializing system...")
        db_adapter = get_vector_db_adapter()
        manager = VectorManager(db_adapter)
        
        # Test connection
        if not manager.test_connection():
            print("❌ Failed to connect to vector database")
            return
        
        print("✓ Connected to vector database")
        
        # Initialize embedder for semantic search
        print("✓ Initializing embedder...")
        embedder = get_embedder()
        
        # Run demos
        demo_database_stats(manager)
        demo_discovery(manager)
        demo_semantic_search_deletion(manager, embedder)
        demo_filename_deletion(manager)
        demo_browse_and_delete(manager)
        demo_advanced_filtering(manager)
        demo_duplicate_cleanup(manager)
        demo_batch_operations(manager)
        
        # Summary
        print_section("SUMMARY")
        print("✅ The hybrid deletion system provides:")
        print("   1. ✓ Semantic search - Find content by meaning")
        print("   2. ✓ Metadata search - Exact matches by filename/category/date")
        print("   3. ✓ Browsing - Explore all content visually")
        print("   4. ✓ Advanced filters - Complex queries")
        print("   5. ✓ Batch operations - Efficient bulk deletion")
        print("   6. ✓ Safety features - Preview, verification, confidence scores")
        print("   7. ✓ Universal - Works with ANY vector database\n")
        
        print("📖 Next steps:")
        print("   - Use vector_manager.py for programmatic access")
        print("   - Check deletion_manager.py for deletion operations")
        print("   - Check discovery_manager.py for search operations")
        print("   - Extend base_adapter.py to add new vector databases\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

