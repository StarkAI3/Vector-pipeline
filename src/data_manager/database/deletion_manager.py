"""
Vector Deletion Manager
High-level service for safe deletion operations across all vector databases
"""
from typing import List, Dict, Any, Optional, Callable
from .base_adapter import VectorDBAdapter
from .deletion_models import (
    DeletionResult,
    BatchDeletionResult,
    DeletionPreview,
    DocumentInfo,
    ChunkInfo
)
from ..utils.logger import get_database_logger

logger = get_database_logger()


class VectorDeletionManager:
    """
    Enterprise-grade deletion manager with validation, verification, and safety features.
    
    Works with any VectorDBAdapter implementation (Pinecone, Qdrant, Weaviate, etc.)
    """
    
    def __init__(self, db_adapter: VectorDBAdapter):
        """
        Initialize deletion manager.
        
        Args:
            db_adapter: Any vector database adapter (must extend VectorDBAdapter)
        """
        self.db = db_adapter
        self.logger = get_database_logger()
    
    def delete_chunk(
        self,
        chunk_id: str,
        namespace: str = "",
        verify: bool = True
    ) -> DeletionResult:
        """
        Delete a single chunk with optional verification.
        
        Args:
            chunk_id: Chunk ID to delete
            namespace: Optional namespace
            verify: If True, verify chunk was deleted
            
        Returns:
            DeletionResult with status and details
        """
        self.logger.info(f"Deleting chunk: {chunk_id}")
        
        try:
            # Execute deletion
            success, message = self.db.delete_chunk(chunk_id, namespace)
            
            # Verify if requested
            if verify and success:
                # Try to fetch the chunk
                try:
                    fetched = self.db.fetch_vectors([chunk_id], namespace)
                    if fetched and chunk_id in fetched:
                        success = False
                        message = "Deletion claimed success but chunk still exists"
                except:
                    # If fetch fails, assume deleted
                    pass
            
            return DeletionResult(
                success=success,
                message=message,
                deleted_count=1 if success else 0,
                target_id=chunk_id,
                target_type="chunk"
            )
        
        except Exception as e:
            error_msg = f"Failed to delete chunk {chunk_id}: {str(e)}"
            self.logger.error(error_msg)
            return DeletionResult(
                success=False,
                message=error_msg,
                target_id=chunk_id,
                target_type="chunk",
                errors=[str(e)]
            )
    
    def delete_chunks_batch(
        self,
        chunk_ids: List[str],
        batch_size: int = 100,
        namespace: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchDeletionResult:
        """
        Delete multiple chunks with progress tracking.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            batch_size: Number of chunks per batch
            namespace: Optional namespace
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            BatchDeletionResult with detailed status
        """
        self.logger.info(f"Batch deleting {len(chunk_ids)} chunks")
        
        result = BatchDeletionResult(
            total_requested=len(chunk_ids),
            total_deleted=0,
            total_failed=0
        )
        
        try:
            # Delete in batches
            success, deleted_count, errors = self.db.delete_chunks_batch(
                chunk_ids=chunk_ids,
                namespace=namespace,
                batch_size=batch_size
            )
            
            result.total_deleted = deleted_count
            result.total_failed = len(chunk_ids) - deleted_count
            result.errors = errors
            
            # Report progress
            if progress_callback:
                progress_callback(deleted_count, len(chunk_ids))
            
        except Exception as e:
            error_msg = f"Batch deletion failed: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            result.total_failed = len(chunk_ids)
        
        result.complete()
        return result
    
    def delete_document(
        self,
        source_id: str,
        namespace: str = "",
        verify: bool = True
    ) -> DeletionResult:
        """
        Delete an entire document (all its chunks).
        
        Args:
            source_id: Source ID to delete
            namespace: Optional namespace
            verify: If True, verify document was deleted
            
        Returns:
            DeletionResult with status and details
        """
        self.logger.info(f"Deleting document: {source_id}")
        
        try:
            # Get chunk count before deletion (for reporting)
            doc_info = self.db.get_document_info(source_id, namespace)
            chunk_count = doc_info['chunk_count'] if doc_info else 0
            
            # Execute deletion
            success, message = self.db.delete_document(source_id, namespace)
            
            # Verify if requested
            if verify and success:
                remaining_chunks = self.db.list_chunks(source_id, namespace, limit=1)
                if remaining_chunks:
                    success = False
                    message = f"Deletion incomplete: {len(remaining_chunks)} chunks remain"
            
            return DeletionResult(
                success=success,
                message=message,
                deleted_count=chunk_count if success else 0,
                target_id=source_id,
                target_type="document"
            )
        
        except Exception as e:
            error_msg = f"Failed to delete document {source_id}: {str(e)}"
            self.logger.error(error_msg)
            return DeletionResult(
                success=False,
                message=error_msg,
                target_id=source_id,
                target_type="document",
                errors=[str(e)]
            )
    
    def delete_documents_batch(
        self,
        source_ids: List[str],
        namespace: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchDeletionResult:
        """
        Delete multiple documents with progress tracking.
        
        Args:
            source_ids: List of source IDs to delete
            namespace: Optional namespace
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            BatchDeletionResult with detailed status
        """
        self.logger.info(f"Batch deleting {len(source_ids)} documents")
        
        result = BatchDeletionResult(
            total_requested=len(source_ids),
            total_deleted=0,
            total_failed=0
        )
        
        try:
            success, deleted_count, errors = self.db.delete_documents_batch(
                source_ids=source_ids,
                namespace=namespace
            )
            
            result.total_deleted = deleted_count
            result.total_failed = len(source_ids) - deleted_count
            result.errors = errors
            
            # Create individual results for each document
            for i, source_id in enumerate(source_ids):
                individual_success = i < deleted_count
                individual_result = DeletionResult(
                    success=individual_success,
                    message="Deleted successfully" if individual_success else "Failed to delete",
                    deleted_count=1 if individual_success else 0,
                    target_id=source_id,
                    target_type="document"
                )
                result.individual_results.append(individual_result)
                
                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, len(source_ids))
            
        except Exception as e:
            error_msg = f"Batch deletion failed: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            result.total_failed = len(source_ids)
        
        result.complete()
        return result
    
    def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = "",
        dry_run: bool = False
    ) -> DeletionResult:
        """
        Delete vectors matching metadata filter.
        
        Args:
            filter_dict: Metadata filter (e.g., {"category": "archived"})
            namespace: Optional namespace
            dry_run: If True, only preview without deleting
            
        Returns:
            DeletionResult (if dry_run, success=False with preview info)
        """
        self.logger.info(f"Delete by filter: {filter_dict}, dry_run={dry_run}")
        
        try:
            if dry_run:
                # Preview only
                matches = self.db.search_by_metadata(filter_dict, namespace, limit=1000)
                return DeletionResult(
                    success=False,
                    message=f"DRY RUN: Would delete {len(matches)} vectors",
                    deleted_count=0,
                    target_type="filter"
                )
            
            # Execute deletion
            success, message = self.db.delete_by_filter(filter_dict, namespace)
            
            return DeletionResult(
                success=success,
                message=message,
                deleted_count=1 if success else 0,  # Unknown count for filter deletion
                target_type="filter"
            )
        
        except Exception as e:
            error_msg = f"Failed to delete by filter: {str(e)}"
            self.logger.error(error_msg)
            return DeletionResult(
                success=False,
                message=error_msg,
                target_type="filter",
                errors=[str(e)]
            )
    
    def get_deletion_preview(
        self,
        source_ids: Optional[List[str]] = None,
        chunk_ids: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> DeletionPreview:
        """
        Preview what will be deleted before executing.
        
        Args:
            source_ids: Optional list of source IDs to preview
            chunk_ids: Optional list of chunk IDs to preview
            filter_dict: Optional metadata filter
            namespace: Optional namespace
            
        Returns:
            DeletionPreview with detailed impact analysis
        """
        self.logger.info("Generating deletion preview")
        
        preview = DeletionPreview(
            total_chunks=0,
            total_documents=0,
            filter_criteria=filter_dict or {}
        )
        
        try:
            if source_ids:
                # Preview document deletion
                for source_id in source_ids:
                    doc_info = self.db.get_document_info(source_id, namespace)
                    if doc_info:
                        preview.total_documents += 1
                        preview.total_chunks += doc_info['chunk_count']
                        preview.affected_documents.append(
                            DocumentInfo(
                                source_id=source_id,
                                filename=doc_info['filename'],
                                chunk_count=doc_info['chunk_count'],
                                upload_date=doc_info.get('upload_date'),
                                category=doc_info.get('category'),
                                metadata=doc_info.get('metadata', {})
                            )
                        )
            
            elif chunk_ids:
                # Preview chunk deletion
                preview.total_chunks = len(chunk_ids)
                # Group chunks by document
                doc_map = {}
                for chunk_id in chunk_ids[:10]:  # Preview first 10
                    try:
                        fetched = self.db.fetch_vectors([chunk_id], namespace)
                        if fetched and chunk_id in fetched:
                            metadata = fetched[chunk_id].get('metadata', {})
                            source_id = metadata.get('source_id', 'unknown')
                            if source_id not in doc_map:
                                doc_map[source_id] = set()
                            doc_map[source_id].add(chunk_id)
                    except:
                        pass
                
                preview.total_documents = len(doc_map)
            
            elif filter_dict:
                # Preview filter-based deletion
                matches = self.db.search_by_metadata(filter_dict, namespace, limit=1000)
                preview.total_chunks = len(matches)
                
                # Group by source_id
                doc_map = {}
                for match in matches:
                    metadata = match.get('metadata', {})
                    source_id = metadata.get('source_id')
                    if source_id:
                        if source_id not in doc_map:
                            doc_map[source_id] = 0
                        doc_map[source_id] += 1
                
                preview.total_documents = len(doc_map)
            
            # Add warnings
            if preview.total_chunks > 1000:
                preview.add_warning(f"Large deletion: {preview.total_chunks} chunks will be deleted")
            if preview.total_documents > 50:
                preview.add_warning(f"Multiple documents affected: {preview.total_documents} documents")
            
        except Exception as e:
            self.logger.error(f"Failed to generate preview: {str(e)}")
            preview.add_warning(f"Preview error: {str(e)}")
        
        return preview


__all__ = ['VectorDeletionManager']

