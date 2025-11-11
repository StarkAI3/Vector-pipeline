"""
Pinecone Adapter for Vector Database Operations
Implements VectorDBAdapter for Pinecone vector database
"""
import time
from typing import List, Dict, Any, Tuple, Optional
from pinecone import Pinecone, ServerlessSpec

from .base_adapter import VectorDBAdapter
from ..core.config import config


class PineconeAdapter(VectorDBAdapter):
    """Pinecone implementation of VectorDBAdapter"""
    
    def __init__(self):
        """Initialize Pinecone connection"""
        super().__init__()
        self.pc = None
        self.index = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Pinecone client and index"""
        try:
            api_key = config.get_vector_db_config('api_key')
            if not api_key:
                self.logger.error("Pinecone API key not configured")
                raise ValueError("VECTOR_DB_API_KEY not set in environment")
            
            self.logger.info("Initializing Pinecone client...")
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=api_key)
            self.client = self.pc
            
            # Get index name
            index_name = config.get_vector_db_config('index_name')
            
            # Check if index exists
            existing_indexes = self.list_indexes()
            
            if index_name not in existing_indexes:
                self.logger.info(f"Creating new Pinecone index: {index_name}")
                dimension = config.get_vector_db_config('dimension')
                metric = config.get_vector_db_config('metric')
                self._create_index(index_name, dimension, metric)
            else:
                self.logger.info(f"Using existing Pinecone index: {index_name}")
            
            # Connect to index
            self.index = self.pc.Index(index_name)
            
            # Get index stats
            stats = self.index.describe_index_stats()
            self.logger.info(f"Index stats: {stats.total_vector_count} vectors, "
                           f"{stats.dimension} dimensions")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise
    
    def _create_index(self, name: str, dimension: int, metric: str, **kwargs):
        """Create a new Pinecone index"""
        try:
            # Get cloud and region from config
            cloud_provider = config.get_vector_db_config('cloud_provider', 'aws')
            region = config.get_vector_db_config('region', 'us-east-1')
            
            self.pc.create_index(
                name=name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud=cloud_provider,
                    region=region
                )
            )
            
            # Wait for index to be ready
            self.logger.info("Waiting for index to be ready...")
            time.sleep(10)
            
            self.logger.info(f"Index {name} created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create index: {str(e)}")
            raise
    
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Tuple[bool, int, str]:
        """Upload vectors to Pinecone"""
        if not vectors:
            return False, 0, "No vectors to upload"
        
        if not self.index:
            return False, 0, "Pinecone index not initialized"
        
        try:
            self.logger.info(f"Uploading {len(vectors)} vectors to Pinecone...")
            
            # Normalize vector format for Pinecone (expects 'values' field)
            normalized_vectors = []
            for v in vectors:
                normalized = self.normalize_vector_format(v)
                normalized_vectors.append(normalized)
            
            # Upsert vectors
            response = self.index.upsert(
                vectors=normalized_vectors,
                namespace=namespace
            )
            
            uploaded_count = response.upserted_count
            
            self.logger.info(f"Successfully uploaded {uploaded_count} vectors")
            
            return True, uploaded_count, "Upload successful"
            
        except Exception as e:
            error_msg = f"Failed to upsert vectors: {str(e)}"
            self.logger.error(error_msg)
            return False, 0, error_msg
    
    def upsert_batch(
        self,
        vectors: List[Dict[str, Any]],
        batch_size: int = None,
        namespace: str = ""
    ) -> Tuple[bool, int, List[str]]:
        """Upload vectors in batches"""
        batch_size = batch_size or config.get_vector_db_config('batch_size', 100)
        
        if not vectors:
            return False, 0, ["No vectors to upload"]
        
        total_uploaded = 0
        errors = []
        
        # Split into batches
        batches = [vectors[i:i + batch_size] for i in range(0, len(vectors), batch_size)]
        
        self.logger.info(f"Uploading {len(vectors)} vectors in {len(batches)} batches...")
        
        for i, batch in enumerate(batches, 1):
            try:
                success, count, message = self.upsert_vectors(batch, namespace)
                
                if success:
                    total_uploaded += count
                    self.logger.info(f"Batch {i}/{len(batches)}: Uploaded {count} vectors")
                else:
                    error_msg = f"Batch {i} failed: {message}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Small delay between batches to avoid rate limiting
                if i < len(batches):
                    time.sleep(0.5)
                    
            except Exception as e:
                error_msg = f"Batch {i} exception: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        
        success = total_uploaded > 0 and len(errors) == 0
        
        self.logger.info(f"Batch upload complete: {total_uploaded}/{len(vectors)} vectors uploaded")
        
        return success, total_uploaded, errors
    
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None,
        namespace: str = "",
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """Query similar vectors from Pinecone"""
        if not self.index:
            self.logger.error("Index not initialized")
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
            self.logger.error(f"Query failed: {str(e)}")
            return []
    
    def fetch_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Dict[str, Any]:
        """Fetch specific vectors by IDs from Pinecone"""
        if not self.index:
            return {}
        
        try:
            response = self.index.fetch(
                ids=vector_ids,
                namespace=namespace
            )
            
            return response.vectors
            
        except Exception as e:
            self.logger.error(f"Fetch failed: {str(e)}")
            return {}
    
    def delete_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """Delete vectors by IDs from Pinecone"""
        if not vector_ids:
            return False, "No vector IDs provided"
        
        if not self.index:
            return False, "Pinecone index not initialized"
        
        try:
            self.logger.info(f"Deleting {len(vector_ids)} vectors from Pinecone...")
            
            self.index.delete(
                ids=vector_ids,
                namespace=namespace
            )
            
            self.logger.info(f"Successfully deleted {len(vector_ids)} vectors")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete vectors: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """Delete vectors matching a metadata filter"""
        if not self.index:
            return False, "Pinecone index not initialized"
        
        try:
            self.logger.info(f"Deleting vectors with filter: {filter_dict}")
            
            # Delete by metadata filter
            self.index.delete(
                filter=filter_dict,
                namespace=namespace
            )
            
            self.logger.info(f"Successfully deleted vectors matching filter")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete by filter: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
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
            self.logger.error(f"Failed to get index stats: {str(e)}")
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test Pinecone connection"""
        try:
            if not self.index:
                return False
            
            stats = self.index.describe_index_stats()
            self.logger.info(f"Connection test passed. Index has {stats.total_vector_count} vectors")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def list_indexes(self) -> List[str]:
        """List all Pinecone indexes"""
        try:
            if not self.pc:
                return []
            
            indexes = self.pc.list_indexes()
            return [index.name for index in indexes]
            
        except Exception as e:
            self.logger.error(f"Failed to list indexes: {str(e)}")
            return []

    def list_documents(
        self,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all unique documents in Pinecone.
        
        Uses dummy vector query to retrieve vectors and groups by source_id.
        """
        if not self.index:
            self.logger.error("Index not initialized")
            return []
        
        try:
            self.logger.info(f"Listing documents in namespace: {namespace or 'default'}")
            
            # Use dummy vector to query (Pinecone doesn't have native list operation)
            # Get dimension from index stats
            stats = self.index.describe_index_stats()
            dimension = stats.dimension
            
            dummy_vector = [0.0] * dimension
            
            # Query with high top_k to get many results
            results = self.query_vectors(
                query_vector=dummy_vector,
                top_k=min(10000, limit * 10),  # Query more than limit to ensure we get all unique docs
                filter_dict=filter_dict,
                namespace=namespace,
                include_metadata=True
            )
            
            # Group by source_id
            documents_map = {}
            for result in results:
                metadata = result.get('metadata', {})
                source_id = metadata.get('source_id')
                
                if not source_id:
                    continue
                
                if source_id not in documents_map:
                    documents_map[source_id] = {
                        'source_id': source_id,
                        'filename': metadata.get('source_filename', metadata.get('filename', 'unknown')),
                        'chunk_count': 0,
                        'upload_date': metadata.get('upload_date', 'unknown'),
                        'category': metadata.get('category', 'unknown'),
                        'metadata': metadata
                    }
                
                documents_map[source_id]['chunk_count'] += 1
            
            # Convert to list and limit
            documents = list(documents_map.values())[:limit]
            
            self.logger.info(f"Found {len(documents)} unique documents")
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    def list_chunks(
        self,
        source_id: str,
        namespace: str = "",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List all chunks for a specific document in Pinecone.
        """
        if not self.index:
            self.logger.error("Index not initialized")
            return []
        
        try:
            self.logger.info(f"Listing chunks for source_id: {source_id}")
            
            # Get dimension from index
            stats = self.index.describe_index_stats()
            dimension = stats.dimension
            dummy_vector = [0.0] * dimension
            
            # Query with source_id filter
            results = self.query_vectors(
                query_vector=dummy_vector,
                top_k=limit,
                filter_dict={'source_id': source_id},
                namespace=namespace,
                include_metadata=True
            )
            
            # Format chunks
            chunks = []
            for result in results:
                metadata = result.get('metadata', {})
                chunks.append({
                    'id': result.get('id'),
                    'text': metadata.get('text', '')[:200],  # Preview
                    'metadata': metadata
                })
            
            self.logger.info(f"Found {len(chunks)} chunks for {source_id}")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to list chunks: {str(e)}")
            return []
    
    def search_by_metadata(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search vectors by metadata filters in Pinecone.
        """
        if not self.index:
            self.logger.error("Index not initialized")
            return []
        
        try:
            self.logger.info(f"Searching by metadata: {filter_dict}")
            
            # Get dimension
            stats = self.index.describe_index_stats()
            dimension = stats.dimension
            dummy_vector = [0.0] * dimension
            
            # Query with metadata filter
            results = self.query_vectors(
                query_vector=dummy_vector,
                top_k=limit,
                filter_dict=filter_dict,
                namespace=namespace,
                include_metadata=True
            )
            
            self.logger.info(f"Found {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search by metadata: {str(e)}")
            return []


__all__ = ['PineconeAdapter']

