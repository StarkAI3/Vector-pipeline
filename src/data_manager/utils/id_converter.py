"""
Universal ID Converter for Vector Databases
Provides deterministic, stable ID conversion for all vector database types
"""
import hashlib
import uuid
from typing import Union

from .logger import get_logger

logger = get_logger(__name__)


def string_to_stable_int(string_id: str) -> int:
    """
    Convert string ID to stable 63-bit positive integer.
    
    This function is DETERMINISTIC - the same string always produces
    the same integer, across all Python versions, machines, and restarts.
    
    Use cases:
    - Qdrant (requires integer IDs)
    - Milvus (requires integer IDs)
    - Any vector DB that needs integer IDs
    
    Args:
        string_id: String ID to convert (e.g., "src_abc123_chunk0001_xyz")
    
    Returns:
        63-bit positive integer (always the same for the same input)
    
    Example:
        >>> string_to_stable_int("src_abc_chunk0001_xyz")
        8234567890123456789
        
        # After restart, same result:
        >>> string_to_stable_int("src_abc_chunk0001_xyz")
        8234567890123456789
    """
    # SHA-256 is cryptographically stable (deterministic)
    hash_bytes = hashlib.sha256(string_id.encode('utf-8')).digest()
    
    # Take first 8 bytes and convert to integer
    # Use only 63 bits to keep it positive (some DBs require positive integers)
    stable_int = int.from_bytes(hash_bytes[:8], 'big') & ((1 << 63) - 1)
    
    logger.debug(f"Converted '{string_id}' to stable int: {stable_int}")
    
    return stable_int


def string_to_uuid(string_id: str) -> str:
    """
    Convert string ID to stable UUID string.
    
    This function is DETERMINISTIC - the same string always produces
    the same UUID, across all Python versions, machines, and restarts.
    
    Use cases:
    - Weaviate (prefers UUID IDs)
    - Any vector DB that prefers UUID format
    
    Args:
        string_id: String ID to convert (e.g., "src_abc123_chunk0001_xyz")
    
    Returns:
        UUID string (always the same for the same input)
    
    Example:
        >>> string_to_uuid("src_abc_chunk0001_xyz")
        'a1b2c3d4-e5f6-5789-abcd-ef0123456789'
        
        # After restart, same result:
        >>> string_to_uuid("src_abc_chunk0001_xyz")
        'a1b2c3d4-e5f6-5789-abcd-ef0123456789'
    """
    # UUID v5 uses SHA-1 internally (deterministic)
    namespace = uuid.NAMESPACE_DNS
    stable_uuid = str(uuid.uuid5(namespace, string_id))
    
    logger.debug(f"Converted '{string_id}' to stable UUID: {stable_uuid}")
    
    return stable_uuid


def stable_int_to_string(stable_int: int) -> str:
    """
    Convert stable integer back to string representation.
    
    Note: This does NOT recover the original string ID.
    It just converts the integer to a string format.
    To get the original ID, use metadata['_original_id'].
    
    Args:
        stable_int: Integer to convert
    
    Returns:
        String representation of the integer
    """
    return str(stable_int)


def validate_id_format(id_value: Union[str, int], expected_type: str = 'auto') -> bool:
    """
    Validate that an ID is in the expected format.
    
    Args:
        id_value: ID to validate
        expected_type: Expected type ('string', 'int', 'uuid', 'auto')
    
    Returns:
        True if valid, False otherwise
    """
    if expected_type == 'auto':
        # Any non-empty value is valid
        return bool(id_value)
    
    elif expected_type == 'string':
        return isinstance(id_value, str) and len(id_value) > 0
    
    elif expected_type == 'int':
        return isinstance(id_value, int) and id_value > 0
    
    elif expected_type == 'uuid':
        if not isinstance(id_value, str):
            return False
        try:
            uuid.UUID(id_value)
            return True
        except ValueError:
            return False
    
    return False


# Mapping of database types to their preferred ID formats
DB_ID_FORMAT_MAP = {
    'pinecone': 'string',
    'qdrant': 'int',
    'weaviate': 'uuid',
    'chroma': 'string',
    'milvus': 'int',
}


def get_db_preferred_format(db_type: str) -> str:
    """
    Get the preferred ID format for a vector database type.
    
    Args:
        db_type: Database type name (e.g., 'qdrant', 'pinecone')
    
    Returns:
        Preferred format: 'string', 'int', or 'uuid'
    """
    db_type_lower = db_type.lower()
    
    # Check exact match
    if db_type_lower in DB_ID_FORMAT_MAP:
        return DB_ID_FORMAT_MAP[db_type_lower]
    
    # Check partial match (for adapter class names like 'QdrantAdapter')
    for db_name, format_type in DB_ID_FORMAT_MAP.items():
        if db_name in db_type_lower:
            return format_type
    
    # Default to string (most compatible)
    return 'string'


__all__ = [
    'string_to_stable_int',
    'string_to_uuid',
    'stable_int_to_string',
    'validate_id_format',
    'get_db_preferred_format',
    'DB_ID_FORMAT_MAP'
]

