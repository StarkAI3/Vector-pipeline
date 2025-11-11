"""
Abstract Base Adapter for Vector Databases
Provides a common interface for all vector database implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional, Union

from ..utils.logger import get_database_logger
from ..utils.id_converter import (
    string_to_stable_int,
    string_to_uuid,
    get_db_preferred_format
)

logger = get_database_logger()


class VectorDBAdapter(ABC):
    """
    Abstract base class for vector database adapters.
    All vector database implementations must extend this class.
    
    This enables easy switching between different vector databases
    (Pinecone, Qdrant, Weaviate, Chroma, Milvus, etc.) by just changing
    configuration in .env file.
    """
    
    def __init__(self):
        """Initialize the vector database adapter"""
        self.client = None
        self.index = None
        self.logger = get_database_logger()
    
    @abstractmethod
    def _initialize_connection(self):
        """
        Initialize connection to the vector database.
        Must be implemented by each adapter.
        """
        pass
    
    @abstractmethod
    def _create_index(self, name: str, dimension: int, metric: str, **kwargs):
        """
        Create a new index/collection in the vector database.
        
        Args:
            name: Name of the index/collection
            dimension: Vector dimension
            metric: Distance metric (cosine, euclidean, dot_product, etc.)
            **kwargs: Additional database-specific parameters
        """
        pass
    
    @abstractmethod
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Tuple[bool, int, str]:
        """
        Upload/update vectors in the database.
        
        Args:
            vectors: List of vectors with format:
                [
                    {
                        "id": "unique_id",
                        "values": [0.1, 0.2, ...],  # embedding vector
                        "metadata": {"key": "value"}
                    }
                ]
            namespace: Optional namespace/partition for organizing vectors
            
        Returns:
            Tuple of (success: bool, count_uploaded: int, message: str)
        """
        pass
    
    @abstractmethod
    def upsert_batch(
        self,
        vectors: List[Dict[str, Any]],
        batch_size: int,
        namespace: str = ""
    ) -> Tuple[bool, int, List[str]]:
        """
        Upload vectors in batches for better performance.
        
        Args:
            vectors: List of vectors
            batch_size: Number of vectors per batch
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, total_uploaded: int, errors: List[str])
        """
        pass
    
    @abstractmethod
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None,
        namespace: str = "",
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query similar vectors from the database.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of matches with format:
                [
                    {
                        "id": "vector_id",
                        "score": 0.95,
                        "metadata": {"key": "value"}
                    }
                ]
        """
        pass
    
    @abstractmethod
    def fetch_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Dict[str, Any]:
        """
        Fetch specific vectors by their IDs.
        
        Args:
            vector_ids: List of vector IDs to fetch
            namespace: Optional namespace
            
        Returns:
            Dict of vectors by ID
        """
        pass
    
    @abstractmethod
    def delete_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete vectors by their IDs.
        
        Args:
            vector_ids: List of vector IDs to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    @abstractmethod
    def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete vectors matching a metadata filter.
        
        Args:
            filter_dict: Metadata filter (e.g., {"source_id": "abc123"})
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index/collection.
        
        Returns:
            Dict with stats like:
                {
                    "total_vectors": 1000,
                    "dimension": 768,
                    "index_fullness": 0.5,
                    "namespaces": {...}
                }
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if connection to vector database is working.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def list_indexes(self) -> List[str]:
        """
        List all available indexes/collections.
        
        Returns:
            List of index/collection names
        """
        pass
    
    @abstractmethod
    def list_documents(
        self,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all unique documents (source_ids) in the database.
        
        This is a key discovery method that allows users to browse what's in the DB.
        
        Args:
            namespace: Optional namespace to filter by
            filter_dict: Optional additional metadata filters
            limit: Maximum number of documents to return
            
        Returns:
            List of documents with format:
                [
                    {
                        "source_id": "src_abc123",
                        "filename": "document.pdf",
                        "chunk_count": 42,
                        "upload_date": "2025-01-07",
                        "category": "HR",
                        "metadata": {...}  # First chunk's metadata
                    }
                ]
        """
        pass
    
    @abstractmethod
    def list_chunks(
        self,
        source_id: str,
        namespace: str = "",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List all chunks for a specific document.
        
        Args:
            source_id: Source ID to get chunks for
            namespace: Optional namespace
            limit: Maximum number of chunks to return
            
        Returns:
            List of chunks with format:
                [
                    {
                        "id": "chunk_id",
                        "text": "chunk text preview",
                        "metadata": {...}
                    }
                ]
        """
        pass
    
    @abstractmethod
    def search_by_metadata(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search vectors by metadata filters (no embedding needed).
        
        This enables exact searches without semantic similarity.
        
        Args:
            filter_dict: Metadata filter (e.g., {"filename": "test.pdf", "category": "HR"})
            namespace: Optional namespace
            limit: Maximum number of results
            
        Returns:
            List of matching vectors with metadata
        """
        pass
    
    # Helper methods that can be used by all adapters
    
    def delete_by_source(
        self,
        source_id: str,
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete all vectors from a specific source.
        This is a convenience method using delete_by_filter.
        
        Args:
            source_id: Source ID to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.delete_by_filter(
            filter_dict={"source_id": source_id},
            namespace=namespace
        )
    
    def validate_vector_format(self, vector: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that a vector has the required format.
        
        Args:
            vector: Vector dict to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not isinstance(vector, dict):
            return False, "Vector must be a dictionary"
        
        if "id" not in vector:
            return False, "Vector must have an 'id' field"
        
        if "values" not in vector and "embedding" not in vector:
            return False, "Vector must have 'values' or 'embedding' field"
        
        values = vector.get("values") or vector.get("embedding")
        if not isinstance(values, (list, tuple)):
            return False, "Vector values must be a list or tuple"
        
        if len(values) == 0:
            return False, "Vector values cannot be empty"
        
        return True, ""
    
    def normalize_vector_format(self, vector: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize vector format to have consistent 'values' field.
        Some DBs use 'values', others use 'embedding' or 'vector'.
        
        Args:
            vector: Vector dict to normalize
            
        Returns:
            Normalized vector dict
        """
        normalized = vector.copy()
        
        # Ensure 'values' field exists
        if "values" not in normalized:
            if "embedding" in normalized:
                normalized["values"] = normalized["embedding"]
            elif "vector" in normalized:
                normalized["values"] = normalized["vector"]
        
        return normalized
    
    def convert_string_id_to_db_format(
        self,
        string_id: str,
        target_format: str = 'auto'
    ) -> Union[str, int]:
        """
        Universal ID converter for all vector databases.
        
        This method ensures that the same string ID always produces the same
        database-specific ID, regardless of restarts, machines, or Python versions.
        
        This is the KEY to universal deduplication across all vector databases.
        
        Args:
            string_id: Original string ID (e.g., "src_abc123_chunk0001_xyz")
            target_format: Target ID format:
                - 'string': Keep as string (Pinecone, Chroma)
                - 'int': Convert to stable integer (Qdrant, Milvus)
                - 'uuid': Convert to stable UUID (Weaviate)
                - 'auto': Auto-detect based on database type
        
        Returns:
            ID in the format required by the vector database
        
        Example:
            # Pinecone adapter
            db_id = self.convert_string_id_to_db_format(
                "src_abc_chunk0001_xyz",
                target_format='string'
            )
            # Returns: "src_abc_chunk0001_xyz"
            
            # Qdrant adapter
            db_id = self.convert_string_id_to_db_format(
                "src_abc_chunk0001_xyz",
                target_format='int'
            )
            # Returns: 8234567890123456789 (always same for same input)
            
            # Weaviate adapter
            db_id = self.convert_string_id_to_db_format(
                "src_abc_chunk0001_xyz",
                target_format='uuid'
            )
            # Returns: "a1b2c3d4-e5f6-5789-abcd-ef0123456789"
        """
        if target_format == 'string':
            return string_id
        
        elif target_format == 'int':
            return string_to_stable_int(string_id)
        
        elif target_format == 'uuid':
            return string_to_uuid(string_id)
        
        elif target_format == 'auto':
            # Auto-detect based on database type
            db_type = self.__class__.__name__  # e.g., "QdrantAdapter"
            preferred_format = get_db_preferred_format(db_type)
            
            if preferred_format == 'int':
                return string_to_stable_int(string_id)
            elif preferred_format == 'uuid':
                return string_to_uuid(string_id)
            else:
                return string_id
        
        # Default: return as string
        return string_id
    
    def prepare_metadata_with_original_id(
        self,
        metadata: Dict[str, Any],
        original_id: str
    ) -> Dict[str, Any]:
        """
        Add original string ID to metadata for universal tracking.
        
        This ensures we can always query/filter/delete by the original string ID,
        even if the database uses a different ID format internally.
        
        Args:
            metadata: Original metadata dict
            original_id: Original string ID
        
        Returns:
            Metadata dict with _original_id field added
        """
        enhanced_metadata = metadata.copy()
        enhanced_metadata['_original_id'] = original_id
        return enhanced_metadata
    
    def check_source_exists(self, source_id: str, namespace: str = "") -> Tuple[bool, int]:
        """
        Check if vectors from a specific source already exist in the database.
        
        This is used for duplicate detection before uploading.
        
        Args:
            source_id: Source ID to check
            namespace: Optional namespace
        
        Returns:
            Tuple of (exists: bool, count: int)
            - exists: True if source has vectors in DB
            - count: Number of vectors found for this source
        """
        try:
            # Query for vectors with this source_id
            # We just need to check if any exist
            results = self.query_vectors(
                query_vector=[0.0] * 768,  # Dummy vector (not used in filter-only query)
                top_k=1,
                filter_dict={"source_id": source_id},
                namespace=namespace,
                include_metadata=True
            )
            
            if results and len(results) > 0:
                # Source exists, try to get count
                # Note: Most DBs don't return count from query, so we return True with found count
                return True, len(results)
            else:
                return False, 0
                
        except Exception as e:
            # If query fails, assume doesn't exist (safe default)
            self.logger.warning(f"Error checking source existence: {str(e)}")
            return False, 0
    
    # Discovery convenience methods
    
    def search_by_filename(
        self,
        filename: str,
        namespace: str = "",
        exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search vectors by filename.
        
        Args:
            filename: Filename to search for
            namespace: Optional namespace
            exact_match: If True, only exact matches; if False, partial matches
            
        Returns:
            List of matching vectors
        """
        # Note: metadata uses 'source_filename' field (from MetadataEnricher)
        filter_dict = {"source_filename": filename}
        return self.search_by_metadata(filter_dict, namespace)
    
    def search_by_category(
        self,
        category: str,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """Search vectors by category"""
        return self.search_by_metadata({"category": category}, namespace)
    
    def get_document_info(
        self,
        source_id: str,
        namespace: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific document.
        
        Args:
            source_id: Source ID to get info for
            namespace: Optional namespace
            
        Returns:
            Dict with document details or None if not found:
                {
                    "source_id": "src_abc123",
                    "filename": "doc.pdf",
                    "chunk_count": 42,
                    "chunks": [...],
                    "metadata": {...}
                }
        """
        try:
            chunks = self.list_chunks(source_id, namespace)
            if not chunks:
                return None
            
            # Get metadata from first chunk
            first_chunk_metadata = chunks[0].get("metadata", {}) if chunks else {}
            
            return {
                "source_id": source_id,
                "filename": first_chunk_metadata.get("filename", "unknown"),
                "chunk_count": len(chunks),
                "chunks": chunks,
                "metadata": first_chunk_metadata,
                "upload_date": first_chunk_metadata.get("upload_date", "unknown"),
                "category": first_chunk_metadata.get("category", "unknown")
            }
        except Exception as e:
            self.logger.error(f"Failed to get document info: {str(e)}")
            return None
    
    # Enhanced deletion methods
    
    def delete_chunk(
        self,
        chunk_id: str,
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete a specific chunk by its chunk_id.
        
        Args:
            chunk_id: Chunk ID to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Try to delete by vector ID first
        success, message = self.delete_vectors([chunk_id], namespace)
        if success:
            return success, message
        
        # Fallback: try metadata filter with _original_id
        return self.delete_by_filter(
            filter_dict={"_original_id": chunk_id},
            namespace=namespace
        )
    
    def delete_chunks_batch(
        self,
        chunk_ids: List[str],
        namespace: str = "",
        batch_size: int = 100
    ) -> Tuple[bool, int, List[str]]:
        """
        Delete multiple chunks in batches.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            namespace: Optional namespace
            batch_size: Number of chunks to delete per batch
            
        Returns:
            Tuple of (success: bool, deleted_count: int, errors: List[str])
        """
        if not chunk_ids:
            return False, 0, ["No chunk IDs provided"]
        
        deleted_count = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i:i + batch_size]
            
            try:
                success, message = self.delete_vectors(batch, namespace)
                if success:
                    deleted_count += len(batch)
                else:
                    errors.append(f"Batch {i//batch_size + 1}: {message}")
            except Exception as e:
                errors.append(f"Batch {i//batch_size + 1}: {str(e)}")
        
        overall_success = deleted_count > 0 and len(errors) == 0
        return overall_success, deleted_count, errors
    
    def delete_document(
        self,
        source_id: str,
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete an entire document (all its chunks).
        Alias for delete_by_source for clarity.
        
        Args:
            source_id: Source ID to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.delete_by_source(source_id, namespace)
    
    def delete_documents_batch(
        self,
        source_ids: List[str],
        namespace: str = ""
    ) -> Tuple[bool, int, List[str]]:
        """
        Delete multiple documents.
        
        Args:
            source_ids: List of source IDs to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success: bool, deleted_count: int, errors: List[str])
        """
        if not source_ids:
            return False, 0, ["No source IDs provided"]
        
        deleted_count = 0
        errors = []
        
        for source_id in source_ids:
            try:
                success, message = self.delete_document(source_id, namespace)
                if success:
                    deleted_count += 1
                    self.logger.info(f"Deleted document {source_id}")
                else:
                    errors.append(f"{source_id}: {message}")
            except Exception as e:
                errors.append(f"{source_id}: {str(e)}")
        
        overall_success = deleted_count > 0 and len(errors) == 0
        return overall_success, deleted_count, errors


__all__ = ['VectorDBAdapter']

