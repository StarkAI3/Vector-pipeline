"""
Unified Vector Manager
Complete vector management system combining discovery and deletion
"""
from typing import List, Dict, Any, Optional, Callable
from .base_adapter import VectorDBAdapter
from .discovery_manager import VectorDiscoveryManager
from .deletion_manager import VectorDeletionManager
from .deletion_models import (
    DeletionResult,
    BatchDeletionResult,
    DeletionPreview,
    DocumentInfo,
    ChunkInfo,
    SearchResult
)
from ..utils.logger import get_database_logger

logger = get_database_logger()


class VectorManager:
    """
    Unified vector management system for discovery and deletion.
    
    This is the main entry point for all vector management operations.
    Works with any VectorDBAdapter implementation (Pinecone, Qdrant, Weaviate, etc.)
    
    Features:
    - Document discovery and browsing
    - Semantic and metadata-based search
    - Safe deletion with preview
    - Batch operations with progress tracking
    - Multi-method deletion (chunks, documents, filters)
    """
    
    def __init__(self, db_adapter: VectorDBAdapter):
        """
        Initialize vector manager.
        
        Args:
            db_adapter: Any vector database adapter (must extend VectorDBAdapter)
        """
        self.db = db_adapter
        self.discovery = VectorDiscoveryManager(db_adapter)
        self.deletion = VectorDeletionManager(db_adapter)
        self.logger = get_database_logger()
        self.logger.info(f"VectorManager initialized with {db_adapter.__class__.__name__}")
    
    # ============================================================================
    # DISCOVERY METHODS
    # ============================================================================
    
    def list_all_documents(self, namespace: str = "", limit: int = 100) -> List[DocumentInfo]:
        """List all documents in database"""
        return self.discovery.list_all_documents(namespace, limit=limit)
    
    def browse_documents(self, page: int = 1, page_size: int = 20, namespace: str = ""):
        """Browse documents with pagination"""
        return self.discovery.browse_documents(page, page_size, namespace=namespace)
    
    def search_documents(self, query: str, namespace: str = "") -> List[DocumentInfo]:
        """Search documents by filename/metadata"""
        return self.discovery.search_documents(query, namespace=namespace)
    
    def search_by_filename(self, filename: str, exact: bool = False, namespace: str = ""):
        """Search by filename"""
        return self.discovery.search_by_filename(filename, exact_match=exact, namespace=namespace)
    
    def search_by_category(self, category: str, namespace: str = ""):
        """Search by category"""
        return self.discovery.search_by_category(category, namespace)
    
    def get_document_details(self, source_id: str, namespace: str = "") -> Optional[DocumentInfo]:
        """Get full details of a document including all chunks"""
        return self.discovery.get_document_tree(source_id, namespace)
    
    def find_duplicates(self, namespace: str = "") -> List[Dict[str, Any]]:
        """Find duplicate documents by filename"""
        return self.discovery.find_duplicate_documents(namespace)
    
    def search_chunks_by_content(
        self,
        text_query: str,
        query_embedding: List[float],
        top_k: int = 10,
        namespace: str = ""
    ) -> SearchResult:
        """Semantic search for chunks by content"""
        return self.discovery.search_chunks_by_content(
            text_query, query_embedding, top_k, namespace=namespace
        )
    
    # ============================================================================
    # DELETION METHODS
    # ============================================================================
    
    def delete_chunk(self, chunk_id: str, namespace: str = "", verify: bool = True) -> DeletionResult:
        """Delete a single chunk"""
        return self.deletion.delete_chunk(chunk_id, namespace, verify)
    
    def delete_chunks(
        self,
        chunk_ids: List[str],
        namespace: str = "",
        progress_callback: Optional[Callable] = None
    ) -> BatchDeletionResult:
        """Delete multiple chunks"""
        return self.deletion.delete_chunks_batch(chunk_ids, namespace=namespace, progress_callback=progress_callback)
    
    def delete_document(self, source_id: str, namespace: str = "", verify: bool = True) -> DeletionResult:
        """Delete entire document"""
        return self.deletion.delete_document(source_id, namespace, verify)
    
    def delete_documents(
        self,
        source_ids: List[str],
        namespace: str = "",
        progress_callback: Optional[Callable] = None
    ) -> BatchDeletionResult:
        """Delete multiple documents"""
        return self.deletion.delete_documents_batch(source_ids, namespace, progress_callback)
    
    def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = "",
        dry_run: bool = False
    ) -> DeletionResult:
        """Delete by metadata filter"""
        return self.deletion.delete_by_filter(filter_dict, namespace, dry_run)
    
    def get_deletion_preview(
        self,
        source_ids: Optional[List[str]] = None,
        chunk_ids: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> DeletionPreview:
        """Preview deletion impact before executing"""
        return self.deletion.get_deletion_preview(source_ids, chunk_ids, filter_dict, namespace)
    
    # ============================================================================
    # COMBINED WORKFLOWS
    # ============================================================================
    
    def find_and_delete_by_content(
        self,
        text_query: str,
        query_embedding: List[float],
        top_k: int = 10,
        namespace: str = "",
        auto_select_high_confidence: bool = False,
        confidence_threshold: float = 0.95,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Find chunks by semantic search and optionally delete them.
        
        This implements the semantic search deletion workflow from user stories.
        
        Args:
            text_query: Text to search for
            query_embedding: Embedding of the query
            top_k: Number of results
            namespace: Optional namespace
            auto_select_high_confidence: Auto-select results above threshold
            confidence_threshold: Minimum score for auto-selection
            dry_run: If True, only preview without deleting
            
        Returns:
            Dict with search results and deletion preview/results
        """
        self.logger.info(f"Find and delete by content: '{text_query}' (dry_run={dry_run})")
        
        # Step 1: Search
        search_result = self.search_chunks_by_content(
            text_query, query_embedding, top_k, namespace
        )
        
        # Step 2: Filter by confidence if requested
        selected_chunks = []
        if auto_select_high_confidence:
            selected_chunks = [
                chunk for chunk in search_result.chunks
                if chunk.similarity_score and chunk.similarity_score >= confidence_threshold
            ]
        else:
            selected_chunks = search_result.chunks
        
        chunk_ids = [chunk.chunk_id for chunk in selected_chunks]
        
        # Step 3: Preview or delete
        if dry_run or not chunk_ids:
            preview = self.get_deletion_preview(chunk_ids=chunk_ids, namespace=namespace)
            return {
                'search_result': search_result,
                'selected_chunks': selected_chunks,
                'preview': preview,
                'dry_run': True
            }
        else:
            deletion_result = self.delete_chunks(chunk_ids, namespace)
            return {
                'search_result': search_result,
                'selected_chunks': selected_chunks,
                'deletion_result': deletion_result,
                'dry_run': False
            }
    
    def find_and_delete_by_filename(
        self,
        filename: str,
        namespace: str = "",
        exact_match: bool = True,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Find documents by filename and optionally delete them.
        
        Args:
            filename: Filename to search for
            namespace: Optional namespace
            exact_match: Require exact filename match
            dry_run: If True, only preview
            
        Returns:
            Dict with search results and deletion preview/results
        """
        self.logger.info(f"Find and delete by filename: '{filename}' (dry_run={dry_run})")
        
        # Search for documents
        documents = self.search_by_filename(filename, exact_match, namespace)
        
        if not documents:
            return {
                'documents': [],
                'message': 'No documents found',
                'dry_run': dry_run
            }
        
        source_ids = [doc.source_id for doc in documents]
        
        # Preview or delete
        if dry_run:
            preview = self.get_deletion_preview(source_ids=source_ids, namespace=namespace)
            return {
                'documents': documents,
                'preview': preview,
                'dry_run': True
            }
        else:
            deletion_result = self.delete_documents(source_ids, namespace)
            return {
                'documents': documents,
                'deletion_result': deletion_result,
                'dry_run': False
            }
    
    def cleanup_duplicates(
        self,
        namespace: str = "",
        keep_strategy: str = "latest",  # "latest", "earliest", "manual"
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Find and optionally delete duplicate documents.
        
        Args:
            namespace: Optional namespace
            keep_strategy: Which version to keep ("latest", "earliest", "manual")
            dry_run: If True, only preview
            
        Returns:
            Dict with duplicates and deletion preview/results
        """
        self.logger.info(f"Cleanup duplicates (strategy={keep_strategy}, dry_run={dry_run})")
        
        # Find duplicates
        duplicates = self.find_duplicates(namespace)
        
        if not duplicates:
            return {
                'duplicates': [],
                'message': 'No duplicates found',
                'dry_run': dry_run
            }
        
        # Determine which to delete based on strategy
        to_delete = []
        if keep_strategy != "manual":
            for dup_group in duplicates:
                docs = sorted(
                    dup_group['documents'],
                    key=lambda d: d.upload_date or "",
                    reverse=(keep_strategy == "latest")
                )
                # Keep first, delete rest
                to_delete.extend([doc.source_id for doc in docs[1:]])
        
        # Preview or delete
        if dry_run or keep_strategy == "manual":
            preview = self.get_deletion_preview(source_ids=to_delete, namespace=namespace) if to_delete else None
            return {
                'duplicates': duplicates,
                'to_delete': to_delete,
                'preview': preview,
                'dry_run': True
            }
        else:
            deletion_result = self.delete_documents(to_delete, namespace) if to_delete else None
            return {
                'duplicates': duplicates,
                'deleted': to_delete,
                'deletion_result': deletion_result,
                'dry_run': False
            }
    
    def delete_old_content(
        self,
        before_date: str,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Delete content uploaded before a specific date.
        
        Args:
            before_date: Date string (ISO format)
            namespace: Optional namespace
            filter_dict: Optional additional filters
            dry_run: If True, only preview
            
        Returns:
            Dict with affected documents and deletion preview/results
        """
        self.logger.info(f"Delete old content before {before_date} (dry_run={dry_run})")
        
        # Get all documents
        all_docs = self.list_all_documents(namespace)
        
        # Filter by date
        old_docs = [
            doc for doc in all_docs
            if doc.upload_date and doc.upload_date < before_date
        ]
        
        # Apply additional filters if provided
        if filter_dict:
            old_docs = [
                doc for doc in old_docs
                if all(
                    doc.metadata.get(key) == value
                    for key, value in filter_dict.items()
                )
            ]
        
        source_ids = [doc.source_id for doc in old_docs]
        
        # Preview or delete
        if dry_run or not source_ids:
            preview = self.get_deletion_preview(source_ids=source_ids, namespace=namespace) if source_ids else None
            return {
                'old_documents': old_docs,
                'count': len(old_docs),
                'preview': preview,
                'dry_run': True
            }
        else:
            deletion_result = self.delete_documents(source_ids, namespace)
            return {
                'old_documents': old_docs,
                'count': len(old_docs),
                'deletion_result': deletion_result,
                'dry_run': False
            }
    
    # ============================================================================
    # DATABASE INFO
    # ============================================================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db.get_index_stats()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        return self.db.test_connection()


__all__ = ['VectorManager']

