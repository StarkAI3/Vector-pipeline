"""
Base Extractor Class
Defines the interface and common functionality for all content extractors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from ..utils.logger import get_logger

logger = get_logger('extractor')


class ExtractionResult:
    """Container for extraction results with metadata"""
    
    def __init__(
        self,
        content: Any,
        file_type: str,
        extracted_structure: str,
        metadata: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.content = content
        self.file_type = file_type
        self.extracted_structure = extracted_structure
        self.metadata = metadata or {}
        self.errors = errors or []
        self.warnings = warnings or []
        self.success = len(self.errors) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "content": self.content,
            "file_type": self.file_type,
            "extracted_structure": self.extracted_structure,
            "metadata": self.metadata,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": self.success
        }
    
    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<ExtractionResult {status}: {self.file_type}/{self.extracted_structure}>"


class BaseExtractor(ABC):
    """
    Abstract base class for all content extractors.
    Each file type (JSON, Excel, PDF, etc.) will have its own extractor.
    """
    
    def __init__(self):
        self.logger = get_logger(f'extractor.{self.__class__.__name__}')
    
    @abstractmethod
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from the given file.
        
        Args:
            file_path: Path to the file to extract
            **kwargs: Additional parameters specific to the extractor
        
        Returns:
            ExtractionResult object containing extracted content and metadata
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate if the file can be processed by this extractor.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions supported by this extractor.
        
        Returns:
            List of supported extensions (e.g., ['.json', '.txt'])
        """
        pass
    
    def _validate_file_exists(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Common validation: check if file exists and is readable"""
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        if file_path.stat().st_size == 0:
            return False, "File is empty"
        
        try:
            # Check if file is readable
            with open(file_path, 'rb') as f:
                f.read(1)
            return True, None
        except Exception as e:
            return False, f"File is not readable: {str(e)}"
    
    def _validate_extension(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Common validation: check if file extension is supported"""
        ext = file_path.suffix.lower()
        supported = self.get_supported_extensions()
        
        if ext not in supported:
            return False, f"Unsupported file extension: {ext}. Supported: {', '.join(supported)}"
        
        return True, None
    
    def _create_error_result(
        self,
        file_type: str,
        error_message: str,
        extracted_structure: str = "unknown"
    ) -> ExtractionResult:
        """Helper to create an error result"""
        return ExtractionResult(
            content=None,
            file_type=file_type,
            extracted_structure=extracted_structure,
            errors=[error_message]
        )
    
    def _log_extraction_start(self, file_path: Path):
        """Log extraction start"""
        self.logger.info(f"Starting extraction: {file_path.name}")
    
    def _log_extraction_success(self, file_path: Path, result: ExtractionResult):
        """Log successful extraction"""
        self.logger.info(
            f"Extraction successful: {file_path.name} "
            f"(type: {result.extracted_structure})"
        )
    
    def _log_extraction_failure(self, file_path: Path, error: str):
        """Log extraction failure"""
        self.logger.error(f"Extraction failed: {file_path.name} - {error}")


class ExtractorMetadata:
    """Helper class to store metadata about extracted content"""
    
    @staticmethod
    def create_metadata(
        file_path: Path,
        file_size: int = None,
        item_count: int = None,
        detected_structure: str = None,
        detected_language: str = None,
        **additional_fields
    ) -> Dict[str, Any]:
        """
        Create standardized metadata dictionary.
        
        Args:
            file_path: Path to the source file
            file_size: Size of file in bytes
            item_count: Number of items extracted (rows, entries, etc.)
            detected_structure: Detected content structure
            detected_language: Detected language
            **additional_fields: Any additional metadata fields
        
        Returns:
            Metadata dictionary
        """
        metadata = {
            "source_file": str(file_path.name),
            "source_path": str(file_path),
            "file_extension": file_path.suffix.lower()
        }
        
        if file_size is not None:
            metadata["file_size"] = file_size
        
        if item_count is not None:
            metadata["item_count"] = item_count
        
        if detected_structure:
            metadata["detected_structure"] = detected_structure
        
        if detected_language:
            metadata["detected_language"] = detected_language
        
        # Add any additional fields
        metadata.update(additional_fields)
        
        return metadata

