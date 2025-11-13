"""
Qdrant Adapter for Vector Database Operations
Implements VectorDBAdapter for Qdrant vector database (cloud and local)
"""
import time
from typing import List, Dict, Any, Tuple, Optional
from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, CollectionStatus
)

from .base_adapter import VectorDBAdapter
from ..core.config import config


class QdrantAdapter(VectorDBAdapter):
    """Qdrant implementation of VectorDBAdapter"""
    
    def __init__(self):
        """Initialize Qdrant connection"""
        super().__init__()
        self.client = None
        self.collection_name = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Qdrant client and collection"""
        try:
            deployment = config.get_vector_db_config('deployment', 'cloud')
            api_key = config.get_vector_db_config('api_key')
            host = config.get_vector_db_config('host', 'localhost')
            port = config.get_vector_db_config('port', 6333)
            
            self.logger.info(f"Initializing Qdrant client ({deployment})...")
            
            # Initialize Qdrant client based on deployment type
            if deployment == 'cloud':
                if not api_key:
                    self.logger.error("Qdrant API key not configured for cloud deployment")
                    raise ValueError("VECTOR_DB_API_KEY not set in environment")
                
                # For Qdrant Cloud, use API key and host
                self.client = QdrantClient(
                    url=host if host.startswith('http') else f"https://{host}",
                    api_key=api_key
                )
            else:
                # For local Qdrant, use host and port
                self.client = QdrantClient(
                    url=f"http://{host}:{port}"
                )
            
            # Get collection name
            self.collection_name = config.get_vector_db_config('index_name')
            
            # Check if collection exists
            existing_collections = self.list_indexes()
            
            if self.collection_name not in existing_collections:
                self.logger.info(f"Creating new Qdrant collection: {self.collection_name}")
                dimension = config.get_vector_db_config('dimension')
                metric = config.get_vector_db_config('metric')
                self._create_index(self.collection_name, dimension, metric)
            else:
                self.logger.info(f"Using existing Qdrant collection: {self.collection_name}")
                # Ensure payload indexes exist for filtering
                self._ensure_payload_indexes()
            
            # Verify collection is ready
            try:
                collection_info = self.client.get_collection(self.collection_name)
                self.logger.info(f"Collection stats: {collection_info.points_count} vectors, "
                               f"{collection_info.config.params.vectors.size} dimensions")
            except Exception as e:
                # If we can't get collection info (version mismatch), just log a warning
                # The collection still exists and works
                self.logger.warning(f"Could not retrieve collection info (collection still usable): {str(e)}")
                self.logger.info(f"Using Qdrant collection: {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {str(e)}")
            raise
    
    def _ensure_payload_indexes(self):
        """Ensure payload indexes exist for an existing collection"""
        try:
            from qdrant_client.models import PayloadSchemaType
            
            # Try to create indexes (will fail silently if they already exist)
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="source_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for 'source_id'")
            except Exception as e:
                if "already exists" in str(e).lower():
                    self.logger.debug(f"Payload index 'source_id' already exists")
                else:
                    self.logger.warning(f"Could not create 'source_id' index: {str(e)}")
            
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="_original_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for '_original_id'")
            except Exception as e:
                if "already exists" in str(e).lower():
                    self.logger.debug(f"Payload index '_original_id' already exists")
                else:
                    self.logger.warning(f"Could not create '_original_id' index: {str(e)}")
                    
        except Exception as e:
            self.logger.warning(f"Error ensuring payload indexes: {str(e)}")
    
    def _create_index(self, name: str, dimension: int, metric: str, **kwargs):
        """Create a new Qdrant collection with payload indexes for filtering"""
        try:
            # Map metric names to Qdrant Distance enum
            metric_mapping = {
                'cosine': Distance.COSINE,
                'euclidean': Distance.EUCLID,
                'dot_product': Distance.DOT
            }
            
            qdrant_metric = metric_mapping.get(metric.lower(), Distance.COSINE)
            
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=qdrant_metric
                )
            )
            
            # Wait for collection to be ready
            self.logger.info("Waiting for collection to be ready...")
            time.sleep(2)
            
            # Create payload indexes for efficient filtering
            # This allows us to filter by source_id and _original_id
            try:
                from qdrant_client.models import PayloadSchemaType
                
                # Index for source_id (used for deletion and verification)
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="source_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for 'source_id'")
                
                # Index for _original_id (used for lookups)
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="_original_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for '_original_id'")
                
                # Index for source_filename (used for filename search)
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="source_filename",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for 'source_filename'")
                
                # Index for category (used for category search)
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="category",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                self.logger.info(f"Created payload index for 'category'")
                
            except Exception as idx_error:
                # If index creation fails, log warning but continue
                # (collection is still usable, just filtering may be slower)
                self.logger.warning(f"Could not create payload indexes: {str(idx_error)}")
            
            self.logger.info(f"Collection {name} created successfully")
            
        except Exception as e:
            # If collection already exists, that's okay
            if "already exists" in str(e).lower():
                self.logger.info(f"Collection {name} already exists")
                # Try to create indexes if they don't exist
                try:
                    from qdrant_client.models import PayloadSchemaType
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="source_id",
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="_original_id",
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="source_filename",
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="category",
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                    self.logger.info(f"Created payload indexes for existing collection")
                except:
                    pass  # Indexes may already exist
            else:
                self.logger.error(f"Failed to create collection: {str(e)}")
                raise
    
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Tuple[bool, int, str]:
        """
        Upload vectors to Qdrant with stable ID conversion.
        
        Uses deterministic ID conversion to ensure the same chunk always
        gets the same Qdrant point ID, enabling proper deduplication.
        """
        if not vectors:
            return False, 0, "No vectors to upload"
        
        if not self.client or not self.collection_name:
            return False, 0, "Qdrant client not initialized"
        
        try:
            self.logger.info(f"Uploading {len(vectors)} vectors to Qdrant...")
            
            # Convert vectors to Qdrant PointStruct format
            points = []
            for v in vectors:
                normalized = self.normalize_vector_format(v)
                
                # Get components
                vector_values = normalized.get('values', [])
                vector_id = normalized.get('id')  # Original string ID
                metadata = normalized.get('metadata', {})
                
                # Add namespace to metadata if provided
                if namespace:
                    metadata['namespace'] = namespace
                
                # CRITICAL: Store original string ID in metadata for queries/deletion
                metadata = self.prepare_metadata_with_original_id(metadata, vector_id)
                
                # Convert string ID to stable integer for Qdrant
                # This uses SHA-256, which is deterministic across all runs
                point_id = self.convert_string_id_to_db_format(
                    vector_id,
                    target_format='int'
                )
                
                point = PointStruct(
                    id=point_id,
                    vector=vector_values,
                    payload=metadata
                )
                points.append(point)
            
            # Upsert points (insert or update if ID exists)
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            uploaded_count = len(points)
            self.logger.info(f"Successfully uploaded {uploaded_count} vectors to Qdrant")
            
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
        """Query similar vectors from Qdrant"""
        if not self.client or not self.collection_name:
            self.logger.error("Client not initialized")
            return []
        
        try:
            # Build filter if provided
            qdrant_filter = None
            if filter_dict or namespace:
                conditions = []
                
                # Add namespace filter if provided
                if namespace:
                    conditions.append(
                        FieldCondition(
                            key="namespace",
                            match=MatchValue(value=namespace)
                        )
                    )
                
                # Add other filters
                if filter_dict:
                    for key, value in filter_dict.items():
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Query Qdrant
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=include_metadata
            )
            
            matches = []
            for result in results:
                matches.append({
                    "id": str(result.id),
                    "score": result.score,
                    "metadata": result.payload if include_metadata else {}
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
        """
        Fetch specific vectors by IDs from Qdrant.
        
        Uses stable ID conversion to find vectors by their original string IDs.
        """
        if not self.client or not self.collection_name:
            return {}
        
        try:
            # Convert string IDs to stable integers (Qdrant format)
            point_ids = []
            for vid in vector_ids:
                point_id = self.convert_string_id_to_db_format(vid, target_format='int')
                point_ids.append(point_id)
            
            # Fetch points
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=point_ids,
                with_payload=True,
                with_vectors=True
            )
            
            # Convert to expected format
            # Return using original string IDs from metadata
            vectors_dict = {}
            for point in results:
                original_id = point.payload.get('_original_id', str(point.id))
                vectors_dict[original_id] = {
                    "id": original_id,
                    "values": point.vector,
                    "metadata": point.payload
                }
            
            return vectors_dict
            
        except Exception as e:
            self.logger.error(f"Fetch failed: {str(e)}")
            return {}
    
    def delete_vectors(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """
        Delete vectors by IDs from Qdrant.
        
        The vector_ids are Qdrant point IDs (as strings), which need to be converted to integers.
        """
        if not vector_ids:
            return False, "No vector IDs provided"
        
        if not self.client or not self.collection_name:
            return False, "Qdrant client not initialized"
        
        try:
            self.logger.info(f"Deleting {len(vector_ids)} vectors from Qdrant...")
            
            # CRITICAL FIX: The IDs we receive are already Qdrant point IDs (as strings from query results)
            # We just need to convert them to integers, NOT hash them again!
            point_ids = []
            for vid in vector_ids:
                try:
                    # Direct conversion from string to integer
                    point_id = int(vid)
                    point_ids.append(point_id)
                except ValueError:
                    self.logger.warning(f"Invalid point ID format: {vid}, trying hash conversion")
                    # Fallback to hash conversion if it's not a direct integer
                    point_id = self.convert_string_id_to_db_format(vid, target_format='int')
                    point_ids.append(point_id)
            
            self.logger.info(f"Deleting point IDs: {point_ids[:3]}... (showing first 3)")
            
            # Delete points - Use models.PointIdsList wrapper as per Qdrant API docs
            # Reference: https://api.qdrant.tech/api-reference/points/delete-points
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                ),
                wait=True  # Wait for deletion to complete
            )
            
            self.logger.info(f"Successfully deleted {len(vector_ids)} vectors from Qdrant")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete vectors: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def delete_by_filter(
        self,
        filter_dict: Dict[str, Any],
        namespace: str = ""
    ) -> Tuple[bool, str]:
        """Delete vectors matching a metadata filter"""
        if not self.client or not self.collection_name:
            return False, "Qdrant client not initialized"
        
        try:
            self.logger.info(f"Deleting vectors with filter: {filter_dict}")
            
            # CRITICAL FIX: If filtering by source_id, the points don't have that field
            # They only have _original_id, so we need to find matching points first
            if 'source_id' in filter_dict:
                source_id = filter_dict['source_id']
                self.logger.info(f"Filtering by source_id: {source_id}, finding matching points by _original_id prefix")
                
                # Get all points and filter by _original_id prefix
                all_points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False
                )
                
                # Find points whose _original_id starts with source_id
                matching_point_ids = [
                    point.id for point in all_points 
                    if point.payload and point.payload.get('_original_id', '').startswith(source_id)
                ]
                
                if not matching_point_ids:
                    self.logger.warning(f"No points found with _original_id starting with {source_id}")
                    return False, f"No points found matching source_id: {source_id}"
                
                self.logger.info(f"Found {len(matching_point_ids)} points to delete")
                
                # Delete by IDs
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=matching_point_ids
                    ),
                    wait=True
                )
                
                self.logger.info(f"Successfully deleted {len(matching_point_ids)} vectors")
                return True, "Deletion successful"
            
            # For other filters, use standard filter-based deletion
            conditions = []
            
            if namespace:
                conditions.append(
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace)
                    )
                )
            
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            qdrant_filter = Filter(must=conditions) if conditions else None
            
            # Delete by filter - Use models.FilterSelector wrapper as per Qdrant API docs
            # Reference: https://api.qdrant.tech/api-reference/points/delete-points
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=qdrant_filter
                ),
                wait=True  # Wait for deletion to complete
            )
            
            self.logger.info(f"Successfully deleted vectors matching filter")
            return True, "Deletion successful"
            
        except Exception as e:
            error_msg = f"Failed to delete by filter: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get Qdrant collection statistics"""
        if not self.client or not self.collection_name:
            return {"error": "Client not initialized"}
        
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "total_vectors": collection_info.points_count,
                "dimension": collection_info.config.params.vectors.size,
                "index_fullness": getattr(collection_info, 'indexed_vectors_count', 0) / max(collection_info.points_count, 1),
                "status": collection_info.status,
                "namespaces": {}  # Qdrant doesn't have namespaces like Pinecone
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test Qdrant connection"""
        try:
            if not self.client or not self.collection_name:
                return False
            
            # Try to get collection info
            collection_info = self.client.get_collection(self.collection_name)
            self.logger.info(f"Connection test passed. Collection has {collection_info.points_count} vectors")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def list_indexes(self) -> List[str]:
        """List all Qdrant collections"""
        try:
            if not self.client:
                return []
            
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
            
        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            return []

    def list_documents(
        self,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all unique documents in Qdrant.
        
        Uses Qdrant's scroll API for efficient retrieval.
        """
        if not self.client or not self.collection_name:
            self.logger.error("Client not initialized")
            return []
        
        try:
            self.logger.info(f"Listing documents from Qdrant collection: {self.collection_name}")
            
            # Build filter if namespace provided
            scroll_filter = None
            if namespace:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                scroll_filter = Filter(
                    must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]
                )
                self.logger.info(f"Using namespace filter: {namespace}")
            elif filter_dict:
                # Convert filter_dict to Qdrant filter
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                scroll_filter = Filter(must=conditions)
                self.logger.info(f"Using filter: {filter_dict}")
            
            # Use scroll to get points (without filter if none specified)
            # FIXED: Explicitly set scroll_filter to None for no filtering
            scroll_params = {
                'collection_name': self.collection_name,
                'limit': min(10000, limit * 10),  # Get more to find unique docs
                'with_payload': True,
                'with_vectors': False  # Don't need vectors
            }
            
            # Only add scroll_filter if it's not None
            if scroll_filter is not None:
                scroll_params['scroll_filter'] = scroll_filter
            
            self.logger.info(f"Scrolling with params: limit={scroll_params['limit']}, has_filter={scroll_filter is not None}")
            
            points, next_page = self.client.scroll(**scroll_params)
            
            self.logger.info(f"Retrieved {len(points)} points from Qdrant")
            
            # Group by source_id
            documents_map = {}
            for point in points:
                payload = point.payload or {}
                
                # Try to get source_id from payload, or extract from _original_id
                source_id = payload.get('source_id')
                
                if not source_id and '_original_id' in payload:
                    # Extract source_id from _original_id format: src_abc123_chunk0001_...
                    original_id = payload['_original_id']
                    if original_id.startswith('src_'):
                        # Extract the source_id part (everything between src_ and _chunk)
                        parts = original_id.split('_chunk')
                        if len(parts) > 0:
                            source_id = parts[0]  # This will be like "src_abd56bc77bfd7ba9"
                
                if not source_id:
                    self.logger.debug(f"Point {point.id} has no source_id or _original_id, skipping")
                    continue
                
                if source_id not in documents_map:
                    # Try to extract filename from _original_id if not in payload
                    filename = payload.get('source_filename', payload.get('filename', 'unknown'))
                    if filename == 'unknown' and '_original_id' in payload:
                        # Filename might be embedded in the chunk_id structure
                        filename = f"document_{source_id}"
                    
                    documents_map[source_id] = {
                        'source_id': source_id,
                        'filename': filename,
                        'chunk_count': 0,
                        'upload_date': payload.get('upload_date', payload.get('uploaded_at', 'unknown')),
                        'category': payload.get('category', 'unknown'),
                        'metadata': payload
                    }
                
                documents_map[source_id]['chunk_count'] += 1
            
            # Convert to list and limit
            documents = list(documents_map.values())[:limit]
            
            self.logger.info(f"Found {len(documents)} unique documents from {len(points)} points")
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to list documents: {str(e)}", exc_info=True)
            return []
    
    def list_chunks(
        self,
        source_id: str,
        namespace: str = "",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List all chunks for a specific document in Qdrant.
        """
        if not self.client or not self.collection_name:
            self.logger.error("Client not initialized")
            return []
        
        try:
            self.logger.info(f"Listing chunks for source_id: {source_id}")
            
            # First try with source_id field filter
            # If that doesn't work, we'll scroll all and filter by _original_id prefix
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                
                conditions = [FieldCondition(key="source_id", match=MatchValue(value=source_id))]
                if namespace:
                    conditions.append(FieldCondition(key="namespace", match=MatchValue(value=namespace)))
                
                scroll_filter = Filter(must=conditions)
                
                points, next_page = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False
                )
                
                # If no results, try alternative method with _original_id prefix matching
                if not points:
                    self.logger.info(f"No chunks found with source_id filter, trying _original_id prefix match")
                    # Get all points and filter by _original_id prefix
                    all_points, _ = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=10000,  # Get many to filter
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    # Filter points whose _original_id starts with source_id
                    points = [
                        p for p in all_points 
                        if p.payload and p.payload.get('_original_id', '').startswith(source_id)
                    ][:limit]
                    
                    self.logger.info(f"Found {len(points)} chunks by _original_id prefix")
            
            except Exception as filter_error:
                self.logger.warning(f"Filter failed, using prefix matching: {str(filter_error)}")
                # Fallback: get all and filter by prefix
                all_points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False
                )
                
                points = [
                    p for p in all_points 
                    if p.payload and p.payload.get('_original_id', '').startswith(source_id)
                ][:limit]
            
            # Format chunks
            chunks = []
            for point in points:
                payload = point.payload or {}
                # Get original ID from payload
                chunk_id = payload.get('_original_id', str(point.id))
                chunks.append({
                    'id': chunk_id,
                    'text': payload.get('text', '')[:200],  # Preview
                    'metadata': payload
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
        Search vectors by metadata filters in Qdrant.
        """
        if not self.client or not self.collection_name:
            self.logger.error("Client not initialized")
            return []
        
        try:
            self.logger.info(f"Searching by metadata: {filter_dict}")
            
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Build filter conditions
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            
            if namespace:
                conditions.append(FieldCondition(key="namespace", match=MatchValue(value=namespace)))
            
            scroll_filter = Filter(must=conditions)
            
            # Use scroll to search
            points, next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for point in points:
                payload = point.payload or {}
                chunk_id = payload.get('_original_id', str(point.id))
                results.append({
                    'id': chunk_id,
                    'score': 1.0,  # No score for metadata search
                    'metadata': payload
                })
            
            self.logger.info(f"Found {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search by metadata: {str(e)}")
            return []
    
    def check_source_exists(self, source_id: str, namespace: str = "") -> Tuple[bool, int]:
        """
        Check if vectors from a specific source already exist in Qdrant.
        
        Override the base class method to use Qdrant-specific _original_id prefix matching.
        
        Args:
            source_id: Source ID to check (e.g., 'src_abc123')
            namespace: Optional namespace (not used in Qdrant)
        
        Returns:
            Tuple of (exists: bool, count: int)
        """
        if not self.client or not self.collection_name:
            self.logger.warning("Qdrant client not initialized")
            return False, 0
        
        try:
            # Get all points and filter by _original_id prefix
            # We scroll with a limit since we just need to check existence
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,  # Reasonable limit for checking
                with_payload=True,
                with_vectors=False
            )
            
            # Count points whose _original_id starts with source_id
            matching_count = sum(
                1 for point in points 
                if point.payload and point.payload.get('_original_id', '').startswith(source_id)
            )
            
            if matching_count > 0:
                self.logger.info(f"Source {source_id} exists with {matching_count} vectors")
                return True, matching_count
            else:
                self.logger.debug(f"Source {source_id} does not exist")
                return False, 0
                
        except Exception as e:
            self.logger.warning(f"Error checking source existence: {str(e)}")
            return False, 0


__all__ = ['QdrantAdapter']

