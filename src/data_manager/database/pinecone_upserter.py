"""
Pinecone Upserter for DMA Bot Data Management System
Uploads vectors to Pinecone with batch processing
"""
import time
from typing import List, Dict, Any, Tuple
from pinecone import Pinecone, ServerlessSpec

from ..core.config import config
from ..utils.logger import get_database_logger

logger = get_database_logger()


class PineconeUpserter:
    """Handle Pinecone vector database operations"""
    
    def __init__(self):
        """Initialize Pinecone connection"""
        self.pc = None
        self.index = None
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            if not config.PINECONE_API_KEY:
                logger.error("Pinecone API key not configured")
                raise ValueError("PINECONE_API_KEY not set in environment")
            
            logger.info("Initializing Pinecone client...")
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [index.name for index in existing_indexes]
            
            if config.PINECONE_INDEX_NAME not in index_names:
                logger.info(f"Creating new Pinecone index: {config.PINECONE_INDEX_NAME}")
                self._create_index()
            else:
                logger.info(f"Using existing Pinecone index: {config.PINECONE_INDEX_NAME}")
            
            # Connect to index
            self.index = self.pc.Index(config.PINECONE_INDEX_NAME)
            
            # Get index stats
            stats = self.index.describe_index_stats()
            logger.info(f"Index stats: {stats.total_vector_count} vectors, "
                       f"{stats.dimension} dimensions")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise
    
    def _create_index(self):
        """Create a new Pinecone index"""
        try:
            self.pc.create_index(
                name=config.PINECONE_INDEX_NAME,
                dimension=config.PINECONE_DIMENSION,
                metric=config.PINECONE_METRIC,
                spec=ServerlessSpec(
                    cloud='aws',
                    region=config.PINECONE_ENVIRONMENT
                )
            )
            
            # Wait for index to be ready
            logger.info("Waiting for index to be ready...")
            time.sleep(10)
            
            logger.info(f"Index {config.PINECONE_INDEX_NAME} created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise
    
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Tuple[bool, int, str]:
        """
        Upload vectors to Pinecone
        
        Args:
            vectors: List of vectors in Pinecone format
            namespace: Optional namespace for organizing vectors
            
        Returns:
            Tuple of (success, count_uploaded, message)
        """
        if not vectors:
            return False, 0, "No vectors to upload"
        
        if not self.index:
            return False, 0, "Pinecone index not initialized"
        
        try:
            logger.info(f"Uploading {len(vectors)} vectors to Pinecone...")
            
            # Upsert vectors
            response = self.index.upsert(
                vectors=vectors,
                namespace=namespace
            )
            
            uploaded_count = response.upserted_count
            
            logger.info(f"Successfully uploaded {uploaded_count} vectors")
            
            return True, uploaded_count, "Upload successful"
            
        except Exception as e:
            error_msg = f"Failed to upsert vectors: {str(e)}"
            logger.error(error_msg)
            return False, 0, error_msg
    
    def upsert_batch(
        self,
        vectors: List[Dict[str, Any]],
        batch_size: int = None,
        namespace: str = ""
    ) -> Tuple[bool, int, List[str]]:
        """
        Upload vectors in batches
        
        Args:
            vectors: List of vectors
            batch_size: Size of each batch
            namespace: Optional namespace
            
        Returns:
            Tuple of (success, total_uploaded, errors)
        """
        batch_size = batch_size or config.PINECONE_BATCH_SIZE
        
        if not vectors:
            return False, 0, ["No vectors to upload"]
        
        total_uploaded = 0
        errors = []
        
        # Split into batches
        batches = [vectors[i:i + batch_size] for i in range(0, len(vectors), batch_size)]
        
        logger.info(f"Uploading {len(vectors)} vectors in {len(batches)} batches...")
        
        for i, batch in enumerate(batches, 1):
            try:
                success, count, message = self.upsert_vectors(batch, namespace)
                
                if success:
                    total_uploaded += count
                    logger.info(f"Batch {i}/{len(batches)}: Uploaded {count} vectors")
                else:
                    error_msg = f"Batch {i} failed: {message}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                
                # Small delay between batches to avoid rate limiting
                if i < len(batches):
                    time.sleep(0.5)
                    
            except Exception as e:
                error_msg = f"Batch {i} exception: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        success = total_uploaded > 0 and len(errors) == 0
        
        logger.info(f"Batch upload complete: {total_uploaded}/{len(vectors)} vectors uploaded")
        
        return success, total_uploaded, errors
    
    def delete_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete vectors by IDs
        
        Args:
            vector_ids: List of vector IDs to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success, message)
        """
        if not vector_ids:
            return False, "No vector IDs provided"
        
        if not self.index:
            return False, "Pinecone index not initialized"
        
        try:
            logger.info(f"Deleting {len(vector_ids)} vectors from Pinecone...")
            
            self.index.delete(
                ids=vector_ids,
                namespace=namespace
            )
            
            logger.info(f"Successfully deleted {len(vector_ids)} vectors")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete vectors: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_by_source(
        self,
        source_id: str,
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete all vectors from a specific source
        
        Args:
            source_id: Source ID to delete
            namespace: Optional namespace
            
        Returns:
            Tuple of (success, message)
        """
        if not self.index:
            return False, "Pinecone index not initialized"
        
        try:
            logger.info(f"Deleting all vectors from source: {source_id}")
            
            # Delete by metadata filter
            self.index.delete(
                filter={"source_id": source_id},
                namespace=namespace
            )
            
            logger.info(f"Successfully deleted vectors from source {source_id}")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete by source: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            Dict with index stats
        """
        if not self.index:
            return {"error": "Index not initialized"}
        
        try:
            stats = self.index.describe_index_stats()
            
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": getattr(stats, 'index_fullness', 0),
                "namespaces": dict(stats.namespaces) if hasattr(stats, 'namespaces') else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {"error": str(e)}
    
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Dict = None,
        namespace: str = "",
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query similar vectors
        
        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            namespace: Optional namespace
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of matching vectors with scores
        """
        if not self.index:
            logger.error("Index not initialized")
            return []
        
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter_dict,
                namespace=namespace,
                include_metadata=include_metadata
            )
            
            matches = []
            for match in results.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else {}
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return []
    
    def fetch_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Dict[str, Any]:
        """
        Fetch specific vectors by IDs
        
        Args:
            vector_ids: List of vector IDs
            namespace: Optional namespace
            
        Returns:
            Dict of vectors
        """
        if not self.index:
            return {}
        
        try:
            response = self.index.fetch(
                ids=vector_ids,
                namespace=namespace
            )
            
            return response.vectors
            
        except Exception as e:
            logger.error(f"Fetch failed: {str(e)}")
            return {}
    
    def test_connection(self) -> bool:
        """
        Test Pinecone connection
        
        Returns:
            True if connection works
        """
        try:
            if not self.index:
                return False
            
            stats = self.index.describe_index_stats()
            logger.info(f"Connection test passed. Index has {stats.total_vector_count} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False


# Singleton instance
_upserter_instance = None


def get_pinecone_upserter() -> PineconeUpserter:
    """
    Get singleton Pinecone upserter instance
    
    Returns:
        PineconeUpserter instance
    """
    global _upserter_instance
    
    if _upserter_instance is None:
        _upserter_instance = PineconeUpserter()
    
    return _upserter_instance


# Export
__all__ = ['PineconeUpserter', 'get_pinecone_upserter']

