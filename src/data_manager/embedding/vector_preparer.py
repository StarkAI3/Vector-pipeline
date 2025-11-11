"""
Vector Preparer for DMA Bot Data Management System
Formats vectors for Pinecone upload
"""
import numpy as np
from typing import List, Dict, Any, Tuple

from ..core.config import config
from ..utils.logger import get_embedder_logger
from ..enrichers.metadata_enricher import MetadataEnricher

logger = get_embedder_logger()


class VectorPreparer:
    """Prepare vectors for Pinecone upsert"""
    
    @classmethod
    def prepare_single_vector(
        cls,
        chunk_id: str,
        embedding: np.ndarray,
        text: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare a single vector for Pinecone
        
        Args:
            chunk_id: Unique chunk ID
            embedding: Embedding array
            text: Original text
            metadata: Chunk metadata
            
        Returns:
            Dict in Pinecone format
        """
        # Convert numpy array to list for JSON serialization
        if isinstance(embedding, np.ndarray):
            embedding_list = embedding.tolist()
        else:
            embedding_list = list(embedding)
        
        # Prepare Pinecone-compatible metadata
        pinecone_metadata = MetadataEnricher.prepare_metadata_for_pinecone(metadata)
        
        # Add the text to metadata (Pinecone stores metadata with vectors)
        pinecone_metadata['text'] = text[:2000]  # Limit text length for metadata
        
        # Create vector dict in Pinecone format
        vector = {
            'id': chunk_id,
            'values': embedding_list,
            'metadata': pinecone_metadata
        }
        
        return vector
    
    @classmethod
    def prepare_batch(
        cls,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare a batch of vectors for Pinecone
        
        Args:
            chunks: List of chunk dicts with id, embedding, text, and metadata
            
        Returns:
            List of vectors in Pinecone format
        """
        if not chunks:
            logger.warning("Empty chunks list provided to vector preparer")
            return []
        
        vectors = []
        
        for chunk in chunks:
            try:
                vector = cls.prepare_single_vector(
                    chunk_id=chunk.get('id', ''),
                    embedding=chunk.get('embedding', np.zeros(config.EMBEDDING_DIMENSION)),
                    text=chunk.get('text', ''),
                    metadata=chunk.get('metadata', {})
                )
                vectors.append(vector)
                
            except Exception as e:
                logger.error(f"Failed to prepare vector for chunk {chunk.get('id', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Prepared {len(vectors)} vectors for upload")
        
        return vectors
    
    @classmethod
    def create_upload_batches(
        cls,
        vectors: List[Dict[str, Any]],
        batch_size: int = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Split vectors into batches for upload
        
        Args:
            vectors: List of prepared vectors
            batch_size: Size of each batch (default from config)
            
        Returns:
            List of vector batches
        """
        batch_size = batch_size or config.PINECONE_BATCH_SIZE
        
        if not vectors:
            return []
        
        batches = []
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches from {len(vectors)} vectors "
                   f"(batch size: {batch_size})")
        
        return batches
    
    @classmethod
    def validate_vector_format(cls, vector: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that a vector matches Pinecone requirements
        
        Args:
            vector: Vector dict to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if 'id' not in vector:
            return False, "Missing 'id' field"
        
        if 'values' not in vector:
            return False, "Missing 'values' field"
        
        # Validate ID
        if not vector['id'] or not isinstance(vector['id'], str):
            return False, "Invalid ID format"
        
        # Validate values
        values = vector['values']
        if not isinstance(values, list):
            return False, "Values must be a list"
        
        if len(values) != config.EMBEDDING_DIMENSION:
            return False, f"Wrong embedding dimension: {len(values)} != {config.EMBEDDING_DIMENSION}"
        
        # Check if values are numbers
        if not all(isinstance(v, (int, float)) for v in values):
            return False, "Values must be numbers"
        
        # Check for NaN or Inf
        if any(np.isnan(v) or np.isinf(v) for v in values):
            return False, "Values contain NaN or Inf"
        
        # Validate metadata (optional but should be dict if present)
        if 'metadata' in vector and not isinstance(vector['metadata'], dict):
            return False, "Metadata must be a dictionary"
        
        return True, "Valid"
    
    @classmethod
    def validate_batch(cls, vectors: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate a batch of vectors and return valid ones
        
        Args:
            vectors: List of vectors to validate
            
        Returns:
            Tuple of (valid_vectors, error_messages)
        """
        valid_vectors = []
        errors = []
        
        for i, vector in enumerate(vectors):
            is_valid, error_msg = cls.validate_vector_format(vector)
            
            if is_valid:
                valid_vectors.append(vector)
            else:
                error_id = vector.get('id', f'index_{i}')
                errors.append(f"Vector {error_id}: {error_msg}")
                logger.warning(f"Invalid vector {error_id}: {error_msg}")
        
        if errors:
            logger.warning(f"Batch validation: {len(valid_vectors)}/{len(vectors)} valid")
        else:
            logger.info(f"Batch validation: All {len(vectors)} vectors valid")
        
        return valid_vectors, errors
    
    @classmethod
    def get_vector_stats(cls, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about a batch of vectors
        
        Args:
            vectors: List of vectors
            
        Returns:
            Dict with statistics
        """
        if not vectors:
            return {
                "count": 0,
                "total_size_bytes": 0,
                "avg_metadata_size": 0
            }
        
        import json
        
        total_size = 0
        metadata_sizes = []
        
        for vector in vectors:
            # Estimate size
            vector_json = json.dumps(vector)
            total_size += len(vector_json.encode('utf-8'))
            
            # Metadata size
            if 'metadata' in vector:
                metadata_json = json.dumps(vector['metadata'])
                metadata_sizes.append(len(metadata_json.encode('utf-8')))
        
        stats = {
            "count": len(vectors),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "avg_size_bytes": total_size // len(vectors),
            "avg_metadata_size": sum(metadata_sizes) // len(metadata_sizes) if metadata_sizes else 0
        }
        
        return stats


# Export
__all__ = ['VectorPreparer']

