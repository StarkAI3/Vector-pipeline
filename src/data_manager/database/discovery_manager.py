"""
Vector Discovery Manager
High-level service for discovering and browsing vectors across all vector databases
"""
from typing import List, Dict, Any, Optional
import time
from .base_adapter import VectorDBAdapter
from .deletion_models import (
    DocumentInfo,
    ChunkInfo,
    SearchResult,
    PaginatedResult
)
from ..utils.logger import get_database_logger

logger = get_database_logger()


class VectorDiscoveryManager:
    """
    Discovery manager for browsing and searching vectors.
    
    Works with any VectorDBAdapter implementation (Pinecone, Qdrant, Weaviate, etc.)
    """
    
    def __init__(self, db_adapter: VectorDBAdapter):
        """
        Initialize discovery manager.
        
        Args:
            db_adapter: Any vector database adapter (must extend VectorDBAdapter)
        """
        self.db = db_adapter
        self.logger = get_database_logger()
    
    def list_all_documents(
        self,
        namespace: str = "",
        limit: int = 100
    ) -> List[DocumentInfo]:
        """
        List all documents in the database.
        
        Args:
            namespace: Optional namespace
            limit: Maximum number of documents to return
            
        Returns:
            List of DocumentInfo objects
        """
        self.logger.info(f"Listing all documents (limit={limit})")
        
        try:
            documents = self.db.list_documents(namespace=namespace, limit=limit)
            
            return [
                DocumentInfo(
                    source_id=doc['source_id'],
                    filename=doc['filename'],
                    chunk_count=doc['chunk_count'],
                    upload_date=doc.get('upload_date'),
                    category=doc.get('category'),
                    metadata=doc.get('metadata', {})
                )
                for doc in documents
            ]
        
        except Exception as e:
            self.logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    def browse_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        filter_dict: Optional[Dict] = None,
        namespace: str = ""
    ) -> PaginatedResult:
        """
        Browse documents with pagination.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of documents per page
            filter_dict: Optional metadata filters
            namespace: Optional namespace
            
        Returns:
            PaginatedResult with documents
        """
        self.logger.info(f"Browsing documents: page {page}, size {page_size}")
        
        try:
            # Get all documents (or filtered subset)
            all_documents = self.db.list_documents(
                namespace=namespace,
                filter_dict=filter_dict,
                limit=page * page_size + 100  # Get a bit more to know if there's more
            )
            
            # Calculate pagination
            total_items = len(all_documents)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Get page items
            page_documents = all_documents[start_idx:end_idx]
            
            # Convert to DocumentInfo
            items = [
                DocumentInfo(
                    source_id=doc['source_id'],
                    filename=doc['filename'],
                    chunk_count=doc['chunk_count'],
                    upload_date=doc.get('upload_date'),
                    category=doc.get('category'),
                    metadata=doc.get('metadata', {})
                )
                for doc in page_documents
            ]
            
            return PaginatedResult(
                items=items,
                page=page,
                page_size=page_size,
                total_items=total_items
            )
        
        except Exception as e:
            self.logger.error(f"Failed to browse documents: {str(e)}")
            return PaginatedResult(
                items=[],
                page=page,
                page_size=page_size,
                total_items=0
            )
    
    def search_documents(
        self,
        query: str,
        search_fields: List[str] = None,
        namespace: str = ""
    ) -> List[DocumentInfo]:
        """
        Search documents by text query in metadata fields.
        
        Args:
            query: Search query text
            search_fields: Fields to search in (default: filename, category)
            namespace: Optional namespace
            
        Returns:
            List of matching DocumentInfo objects
        """
        if search_fields is None:
            search_fields = ['filename', 'category']
        
        self.logger.info(f"Searching documents: query='{query}', fields={search_fields}")
        
        try:
            # Get all documents
            all_documents = self.db.list_documents(namespace=namespace, limit=1000)
            
            # Filter by search query
            query_lower = query.lower()
            matched_documents = []
            
            for doc in all_documents:
                # Check if query matches any search field
                for field in search_fields:
                    field_value = str(doc.get(field, '')).lower()
                    if query_lower in field_value:
                        matched_documents.append(
                            DocumentInfo(
                                source_id=doc['source_id'],
                                filename=doc['filename'],
                                chunk_count=doc['chunk_count'],
                                upload_date=doc.get('upload_date'),
                                category=doc.get('category'),
                                metadata=doc.get('metadata', {})
                            )
                        )
                        break
            
            self.logger.info(f"Found {len(matched_documents)} matching documents")
            return matched_documents
        
        except Exception as e:
            self.logger.error(f"Failed to search documents: {str(e)}")
            return []
    
    def search_by_filename(
        self,
        filename: str,
        exact_match: bool = False,
        namespace: str = ""
    ) -> List[DocumentInfo]:
        """
        Search documents by filename.
        
        Args:
            filename: Filename to search for
            exact_match: If True, require exact match
            namespace: Optional namespace
            
        Returns:
            List of matching DocumentInfo objects
        """
        self.logger.info(f"Searching by filename: '{filename}' (exact={exact_match})")
        
        try:
            if exact_match:
                # Use metadata search for exact match
                results = self.db.search_by_filename(filename, namespace)
                
                # Group by source_id
                doc_map = {}
                for result in results:
                    metadata = result.get('metadata', {})
                    source_id = metadata.get('source_id')
                    if source_id and source_id not in doc_map:
                        doc_map[source_id] = DocumentInfo(
                            source_id=source_id,
                            filename=metadata.get('source_filename', metadata.get('filename', filename)),
                            chunk_count=0,
                            upload_date=metadata.get('upload_date'),
                            category=metadata.get('category'),
                            metadata=metadata
                        )
                    if source_id:
                        doc_map[source_id].chunk_count += 1
                
                return list(doc_map.values())
            else:
                # Partial match using search_documents
                return self.search_documents(filename, ['filename'], namespace)
        
        except Exception as e:
            self.logger.error(f"Failed to search by filename: {str(e)}")
            return []
    
    def search_by_category(
        self,
        category: str,
        namespace: str = ""
    ) -> List[DocumentInfo]:
        """
        Search documents by category.
        
        Args:
            category: Category to search for
            namespace: Optional namespace
            
        Returns:
            List of matching DocumentInfo objects
        """
        self.logger.info(f"Searching by category: '{category}'")
        
        try:
            results = self.db.search_by_category(category, namespace)
            
            # Group by source_id
            doc_map = {}
            for result in results:
                metadata = result.get('metadata', {})
                source_id = metadata.get('source_id')
                if source_id and source_id not in doc_map:
                    doc_map[source_id] = DocumentInfo(
                        source_id=source_id,
                        filename=metadata.get('source_filename', metadata.get('filename', 'unknown')),
                        chunk_count=0,
                        upload_date=metadata.get('upload_date'),
                        category=category,
                        metadata=metadata
                    )
                if source_id:
                    doc_map[source_id].chunk_count += 1
            
            return list(doc_map.values())
        
        except Exception as e:
            self.logger.error(f"Failed to search by category: {str(e)}")
            return []
    
    def get_document_tree(
        self,
        source_id: str,
        namespace: str = ""
    ) -> Optional[DocumentInfo]:
        """
        Get hierarchical view of document with all its chunks.
        
        Args:
            source_id: Source ID
            namespace: Optional namespace
            
        Returns:
            DocumentInfo with chunks populated, or None if not found
        """
        self.logger.info(f"Getting document tree for: {source_id}")
        
        try:
            doc_info = self.db.get_document_info(source_id, namespace)
            if not doc_info:
                return None
            
            chunks = self.db.list_chunks(source_id, namespace)
            
            return DocumentInfo(
                source_id=source_id,
                filename=doc_info['filename'],
                chunk_count=len(chunks),
                upload_date=doc_info.get('upload_date'),
                category=doc_info.get('category'),
                metadata=doc_info.get('metadata', {}),
                chunks=chunks
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get document tree: {str(e)}")
            return None
    
    def find_duplicate_documents(
        self,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Find documents with duplicate filenames.
        
        Args:
            namespace: Optional namespace
            
        Returns:
            List of duplicate groups with format:
                [
                    {
                        "filename": "doc.pdf",
                        "count": 2,
                        "documents": [DocumentInfo, DocumentInfo]
                    }
                ]
        """
        self.logger.info("Finding duplicate documents")
        
        try:
            all_documents = self.list_all_documents(namespace, limit=1000)
            
            # Group by filename
            filename_map = {}
            for doc in all_documents:
                filename = doc.filename
                if filename not in filename_map:
                    filename_map[filename] = []
                filename_map[filename].append(doc)
            
            # Find duplicates
            duplicates = []
            for filename, docs in filename_map.items():
                if len(docs) > 1:
                    duplicates.append({
                        'filename': filename,
                        'count': len(docs),
                        'documents': docs
                    })
            
            self.logger.info(f"Found {len(duplicates)} duplicate filename groups")
            return duplicates
        
        except Exception as e:
            self.logger.error(f"Failed to find duplicates: {str(e)}")
            return []
    
    def search_chunks_by_content(
        self,
        text_query: str,
        query_embedding: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        namespace: str = ""
    ) -> SearchResult:
        """
        Search chunks by semantic similarity (content-based).
        
        This is the semantic search method for deletion discovery.
        
        Args:
            text_query: Original text query (for display)
            query_embedding: Embedding vector for the query
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace
            
        Returns:
            SearchResult with matching chunks
        """
        self.logger.info(f"Semantic search: '{text_query}' (top_k={top_k})")
        
        start_time = time.time()
        
        try:
            # Query vectors
            results = self.db.query_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                filter_dict=filter_dict,
                namespace=namespace,
                include_metadata=True
            )
            
            # Convert to ChunkInfo
            chunks = []
            for result in results:
                metadata = result.get('metadata', {})
                chunks.append(
                    ChunkInfo(
                        chunk_id=result['id'],
                        source_id=metadata.get('source_id', 'unknown'),
                        text_preview=metadata.get('text', '')[:200],
                        metadata=metadata,
                        similarity_score=result.get('score', 0.0)
                    )
                )
            
            search_time = time.time() - start_time
            
            return SearchResult(
                query=text_query,
                query_type="semantic",
                total_matches=len(chunks),
                chunks=chunks,
                search_time_seconds=search_time
            )
        
        except Exception as e:
            self.logger.error(f"Failed to search chunks: {str(e)}")
            return SearchResult(
                query=text_query,
                query_type="semantic",
                total_matches=0,
                chunks=[],
                search_time_seconds=time.time() - start_time
            )


__all__ = ['VectorDiscoveryManager']

