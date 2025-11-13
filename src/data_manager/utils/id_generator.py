"""
ID Generator for DMA Bot Data Management System
Creates stable, unique IDs for tracking chunks, jobs, and sources
"""
import hashlib
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.id_generator")


class IDGenerator:
    """Generate various types of IDs for the system"""
    
    @staticmethod
    def generate_job_id() -> str:
        """
        Generate unique job ID
        
        Returns:
            Job ID string (format: job_TIMESTAMP_UUID)
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        job_id = f"job_{timestamp}_{short_uuid}"
        logger.debug(f"Generated job ID: {job_id}")
        return job_id
    
    @staticmethod
    def generate_source_id(filename: str, file_hash: str, user_metadata: Dict[str, Any]) -> str:
        """
        Generate stable source ID based on file content and metadata
        This allows tracking and updating the same source over time
        
        Args:
            filename: Original filename
            file_hash: SHA256 hash of file
            user_metadata: User-provided metadata (category, language, etc.)
            
        Returns:
            Source ID string
        
        Note: content_type/structure is intentionally NOT included in source ID
        to ensure same file with same category gets same ID regardless of
        which structure option user selects in the questionnaire.
        """
        # Create deterministic hash from key attributes
        # NOTE: We exclude content_type to make de-duplication more reliable
        # The same file + same category = same source, regardless of structure selection
        source_string = f"{filename}_{file_hash}_{user_metadata.get('category', '')}"
        source_hash = hashlib.sha256(source_string.encode()).hexdigest()[:16]
        
        source_id = f"src_{source_hash}"
        logger.debug(f"Generated source ID: {source_id} for {filename}")
        return source_id
    
    @staticmethod
    def generate_chunk_id(
        source_id: str,
        chunk_index: int,
        content_sample: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate unique chunk ID based on source and content
        Stable - same content generates same ID for deduplication
        
        Args:
            source_id: Source document ID
            chunk_index: Index of chunk in document
            content_sample: Sample of chunk content for uniqueness
            metadata: Optional metadata for additional uniqueness
            
        Returns:
            Chunk ID string
        """
        # Create deterministic hash
        content_hash = hashlib.sha256(content_sample.encode()).hexdigest()[:12]
        
        # Include language if present for bilingual chunks
        language = ""
        if metadata and 'language' in metadata:
            language = f"_{metadata['language']}"
        
        chunk_id = f"{source_id}_chunk{chunk_index:04d}_{content_hash}{language}"
        logger.debug(f"Generated chunk ID: {chunk_id}")
        return chunk_id
    
    @staticmethod
    def generate_batch_id(job_id: str, batch_number: int) -> str:
        """
        Generate batch ID for vector upsert batches
        
        Args:
            job_id: Parent job ID
            batch_number: Batch number in sequence
            
        Returns:
            Batch ID string
        """
        batch_id = f"{job_id}_batch{batch_number:03d}"
        logger.debug(f"Generated batch ID: {batch_id}")
        return batch_id
    
    @staticmethod
    def generate_tracking_id() -> str:
        """
        Generate simple tracking ID for temporary operations
        
        Returns:
            Tracking ID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def extract_timestamp_from_job_id(job_id: str) -> Optional[datetime]:
        """
        Extract timestamp from job ID
        
        Args:
            job_id: Job ID string
            
        Returns:
            Datetime object or None
        """
        try:
            # Extract timestamp part (format: job_YYYYMMDDHHMMSS_uuid)
            parts = job_id.split("_")
            if len(parts) >= 2:
                timestamp_str = parts[1]
                return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        except Exception as e:
            logger.error(f"Failed to extract timestamp from {job_id}: {str(e)}")
        
        return None
    
    @staticmethod
    def is_valid_job_id(job_id: str) -> bool:
        """
        Validate job ID format
        
        Args:
            job_id: Job ID to validate
            
        Returns:
            True if valid format
        """
        try:
            parts = job_id.split("_")
            if len(parts) != 3:
                return False
            if parts[0] != "job":
                return False
            # Check timestamp format
            datetime.strptime(parts[1], "%Y%m%d%H%M%S")
            return True
        except:
            return False
    
    @staticmethod
    def is_valid_source_id(source_id: str) -> bool:
        """
        Validate source ID format
        
        Args:
            source_id: Source ID to validate
            
        Returns:
            True if valid format
        """
        return source_id.startswith("src_") and len(source_id) == 20  # src_ + 16 chars
    
    @staticmethod
    def is_valid_chunk_id(chunk_id: str) -> bool:
        """
        Validate chunk ID format
        
        Args:
            chunk_id: Chunk ID to validate
            
        Returns:
            True if valid format
        """
        return "chunk" in chunk_id and chunk_id.startswith("src_")


# Export
__all__ = ['IDGenerator']

