"""
Base Processor Class
Defines the interface for all content processors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger

logger = get_logger('processor')


@dataclass
class Chunk:
    """
    Represents a processed chunk of content ready for embedding.
    """
    chunk_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    quality_score: float = 1.0
    source_index: Optional[int] = None  # Index in source data
    chunk_index: int = 0  # Sequential index in processing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
            "language": self.language,
            "quality_score": self.quality_score,
            "source_index": self.source_index,
            "chunk_index": self.chunk_index
        }
    
    def __repr__(self):
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Chunk {self.chunk_id}: {text_preview}>"


@dataclass
class ProcessingResult:
    """Container for processing results with statistics"""
    
    chunks: List[Chunk] = field(default_factory=list)
    total_chunks: int = 0
    valid_chunks: int = 0
    rejected_chunks: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "total_chunks": self.total_chunks,
            "valid_chunks": self.valid_chunks,
            "rejected_chunks": self.rejected_chunks,
            "errors": self.errors,
            "warnings": self.warnings,
            "processing_stats": self.processing_stats,
            "success": self.success
        }
    
    def add_chunk(self, chunk: Chunk):
        """Add a valid chunk to results"""
        self.chunks.append(chunk)
        self.valid_chunks += 1
        self.total_chunks += 1
    
    def reject_chunk(self, reason: str):
        """Record a rejected chunk"""
        self.rejected_chunks += 1
        self.total_chunks += 1
        self.warnings.append(f"Chunk rejected: {reason}")
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<ProcessingResult {status}: {self.valid_chunks}/{self.total_chunks} chunks>"


class BaseProcessor(ABC):
    """
    Abstract base class for all content processors.
    Each processor handles a specific content structure/type.
    """
    
    def __init__(self):
        self.logger = get_logger(f'processor.{self.__class__.__name__}')
    
    @abstractmethod
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process content and create chunks.
        
        Args:
            content: Extracted content from extractor
            metadata: Metadata about the content
            **kwargs: Additional processing parameters
        
        Returns:
            ProcessingResult with created chunks
        """
        pass
    
    @abstractmethod
    def can_process(self, content: Any, structure: str) -> bool:
        """
        Check if this processor can handle the given content structure.
        
        Args:
            content: Content to process
            structure: Content structure type
        
        Returns:
            True if processor can handle this content
        """
        pass
    
    @abstractmethod
    def get_supported_structures(self) -> List[str]:
        """
        Get list of content structures this processor supports.
        
        Returns:
            List of structure type strings
        """
        pass
    
    def _create_chunk_id(
        self,
        source_id: str,
        chunk_index: int,
        text: str,
        language: str = "en"
    ) -> str:
        """
        Create a unique chunk ID.
        
        Args:
            source_id: Source document ID
            chunk_index: Index of this chunk
            language: Language code
            **kwargs: Additional identifiers
        
        Returns:
            Unique chunk ID
        """
        from ..utils.id_generator import IDGenerator
        
        metadata = {"language": language} if language else None
        content_sample = (text or "")[:200]
        return IDGenerator.generate_chunk_id(
            source_id=source_id,
            chunk_index=chunk_index,
            content_sample=content_sample,
            metadata=metadata
        )
    
    def _create_chunk(
        self,
        text: str,
        chunk_id: str,
        metadata: Dict[str, Any],
        language: str = "en",
        source_index: Optional[int] = None,
        chunk_index: int = 0
    ) -> Chunk:
        """
        Create a Chunk object.
        
        Args:
            text: Chunk text content
            chunk_id: Unique chunk ID
            metadata: Chunk metadata
            language: Language code
            source_index: Index in source data
            chunk_index: Sequential chunk index
        
        Returns:
            Chunk object
        """
        return Chunk(
            chunk_id=chunk_id,
            text=text,
            metadata=metadata,
            language=language,
            source_index=source_index,
            chunk_index=chunk_index
        )
    
    def _validate_chunk(self, chunk: Chunk, min_length: int = 10) -> tuple[bool, Optional[str]]:
        """
        Validate a chunk before adding to results.
        
        Args:
            chunk: Chunk to validate
            min_length: Minimum text length
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        # Check text length
        if not chunk.text or len(chunk.text.strip()) < min_length:
            return False, f"Text too short: {len(chunk.text if chunk.text else '')} chars"
        
        # Check if text is meaningful (not just whitespace/special chars)
        stripped = chunk.text.strip()
        if not any(c.isalnum() for c in stripped):
            return False, "No alphanumeric content"
        
        return True, None
    
    def _enrich_with_metadata(
        self,
        chunk: Chunk,
        user_metadata: Dict[str, Any],
        **additional_metadata
    ) -> Chunk:
        """
        Enrich chunk with metadata using MetadataEnricher.
        
        Args:
            chunk: Chunk to enrich
            user_metadata: User-provided metadata
            **additional_metadata: Additional metadata to add
        
        Returns:
            Enriched chunk
        """
        from ..enrichers.metadata_enricher import MetadataEnricher
        
        # Extract special elements to include in metadata
        special_elements = self._extract_special_elements(chunk.text)
        
        # Enrich metadata using classmethod
        enriched_metadata = MetadataEnricher.enrich_chunk_metadata(
            chunk_text=chunk.text,
            chunk_index=chunk.chunk_index,
            source_metadata={**user_metadata, **additional_metadata},
            language=chunk.language,
            special_elements=special_elements
        )
        
        # Update chunk metadata
        chunk.metadata = enriched_metadata
        
        return chunk
    
    def _extract_special_elements(self, text: str) -> Dict[str, List[str]]:
        """
        Extract special elements (URLs, emails, phones) from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            Dictionary of extracted elements
        """
        from ..enrichers.special_elements import SpecialElementsExtractor
        
        extractor = SpecialElementsExtractor()
        return extractor.extract_all(text)
    
    def _validate_chunk_quality(self, text: str, language: str = "en") -> tuple[float, bool]:
        """
        Validate chunk quality.
        
        Args:
            text: Chunk text
            language: Language code
        
        Returns:
            Tuple of (quality_score, is_acceptable)
        """
        from ..validators.quality_validator import QualityValidator
        from ..core.config import Config
        
        # Validate returns (is_valid, score, reason)
        is_valid, score, _ = QualityValidator.validate_chunk(text, {"language": language})
        return score, is_valid
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language of text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Language code
        """
        from ..analyzers.language_detector import LanguageDetector
        
        detector = LanguageDetector()
        result = detector.detect_language(text)
        return result.get("primary_language", "en")
    
    def _log_processing_start(self, content_type: str, item_count: int):
        """Log processing start"""
        self.logger.info(f"Starting processing: {content_type} ({item_count} items)")
    
    def _log_processing_complete(self, result: ProcessingResult):
        """Log processing completion"""
        self.logger.info(
            f"Processing complete: {result.valid_chunks} valid, "
            f"{result.rejected_chunks} rejected, "
            f"{len(result.errors)} errors"
        )
    
    def _create_error_result(self, error_message: str) -> ProcessingResult:
        """Create an error result"""
        result = ProcessingResult(success=False)
        result.add_error(error_message)
        return result

