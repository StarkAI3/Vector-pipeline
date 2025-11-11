"""
Vector Database Factory
Factory pattern for creating vector database adapters based on configuration
"""
from typing import Optional
from .base_adapter import VectorDBAdapter
from .pinecone_adapter import PineconeAdapter
from .qdrant_adapter import QdrantAdapter
from ..core.config import config
from ..utils.logger import get_database_logger

logger = get_database_logger()


class VectorDBFactory:
    """
    Factory class for creating vector database adapters.
    
    Supports multiple vector databases:
    - Pinecone (cloud/serverless)
    - Qdrant (cloud/local)
    - Weaviate (cloud/local)
    - Chroma (local)
    - Milvus (cloud/local)
    
    To add a new vector database:
    1. Create a new adapter class that extends VectorDBAdapter
    2. Add the adapter to _adapters dict below
    3. Update .env with appropriate configuration
    """
    
    # Registry of available adapters
    _adapters = {
        'pinecone': PineconeAdapter,
        'qdrant': QdrantAdapter,
        # Future adapters can be added here:
        # 'weaviate': WeaviateAdapter,
        # 'chroma': ChromaAdapter,
        # 'milvus': MilvusAdapter,
    }
    
    @classmethod
    def create_adapter(cls, db_type: Optional[str] = None) -> VectorDBAdapter:
        """
        Create and return a vector database adapter based on configuration.
        
        Args:
            db_type: Type of vector database. If None, reads from config.
                    Supported: 'pinecone', 'qdrant', 'weaviate', 'chroma', 'milvus'
        
        Returns:
            Initialized VectorDBAdapter instance
        
        Raises:
            ValueError: If vector database type is not supported
        """
        # Get database type from config if not provided
        if db_type is None:
            db_type = config.get_vector_db_type()
        
        db_type = db_type.lower()
        
        # Check if adapter exists
        if db_type not in cls._adapters:
            available = ', '.join(cls._adapters.keys())
            error_msg = (
                f"Unsupported vector database type: '{db_type}'. "
                f"Available options: {available}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get adapter class
        adapter_class = cls._adapters[db_type]
        
        logger.info(f"Creating {db_type.upper()} vector database adapter...")
        
        try:
            # Instantiate and return adapter
            adapter = adapter_class()
            logger.info(f"{db_type.upper()} adapter initialized successfully")
            return adapter
        except Exception as e:
            error_msg = f"Failed to initialize {db_type} adapter: {str(e)}"
            logger.error(error_msg)
            raise
    
    @classmethod
    def register_adapter(cls, db_type: str, adapter_class: type):
        """
        Register a new adapter type.
        Useful for custom or third-party adapters.
        
        Args:
            db_type: Name of the database type (e.g., 'custom_db')
            adapter_class: Adapter class that extends VectorDBAdapter
        """
        if not issubclass(adapter_class, VectorDBAdapter):
            raise TypeError(
                f"Adapter class must extend VectorDBAdapter. "
                f"Got: {adapter_class.__name__}"
            )
        
        cls._adapters[db_type.lower()] = adapter_class
        logger.info(f"Registered new adapter: {db_type}")
    
    @classmethod
    def list_available_adapters(cls) -> list:
        """
        Get list of available vector database types.
        
        Returns:
            List of supported database type names
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def is_adapter_available(cls, db_type: str) -> bool:
        """
        Check if an adapter is available for the given database type.
        
        Args:
            db_type: Database type to check
        
        Returns:
            True if adapter is available, False otherwise
        """
        return db_type.lower() in cls._adapters


# Singleton instance
_adapter_instance: Optional[VectorDBAdapter] = None


def get_vector_db_adapter(force_new: bool = False) -> VectorDBAdapter:
    """
    Get singleton vector database adapter instance.
    
    This ensures that throughout the application, we use the same
    connection to the vector database.
    
    Args:
        force_new: If True, creates a new instance even if one exists
    
    Returns:
        VectorDBAdapter instance configured from .env
    """
    global _adapter_instance
    
    if _adapter_instance is None or force_new:
        _adapter_instance = VectorDBFactory.create_adapter()
    
    return _adapter_instance


def reset_adapter():
    """
    Reset the singleton adapter instance.
    Useful for testing or when switching databases at runtime.
    """
    global _adapter_instance
    _adapter_instance = None
    logger.info("Vector database adapter reset")


__all__ = [
    'VectorDBFactory',
    'get_vector_db_adapter',
    'reset_adapter'
]

