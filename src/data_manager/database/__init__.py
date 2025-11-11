"""
Database Module - Vector Database Adapters
Modular design supporting multiple vector databases
"""

# Import base adapter
from .base_adapter import VectorDBAdapter

# Import concrete adapters
from .pinecone_adapter import PineconeAdapter
from .qdrant_adapter import QdrantAdapter

# Import factory
from .vector_db_factory import (
    VectorDBFactory,
    get_vector_db_adapter,
    reset_adapter
)

# Import verifier
from .verifier import UploadVerifier, get_verifier

# Backward compatibility - Legacy imports
# These allow old code to continue working without changes
from .pinecone_upserter import PineconeUpserter, get_pinecone_upserter

__all__ = [
    # Base adapter
    'VectorDBAdapter',
    
    # Concrete adapters
    'PineconeAdapter',
    'QdrantAdapter',
    
    # Factory
    'VectorDBFactory',
    'get_vector_db_adapter',
    'reset_adapter',
    
    # Verifier
    'UploadVerifier',
    'get_verifier',
    
    # Backward compatibility
    'PineconeUpserter',
    'get_pinecone_upserter',
]

