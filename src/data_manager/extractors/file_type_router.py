"""
File Type Router
Routes files to the appropriate extractor based on file type
"""
from pathlib import Path
from typing import Dict, Optional, Type

from .base_extractor import BaseExtractor, ExtractionResult
from .json_extractor import JSONExtractor
from .excel_extractor import ExcelExtractor
from .csv_extractor import CSVExtractor
from ..utils.logger import get_logger
from ..core.config import Config

logger = get_logger('extractor.router')


class FileTypeRouter:
    """
    Routes files to appropriate extractors based on file type.
    Manages extractor instances and provides unified extraction interface.
    """
    
    def __init__(self):
        self.logger = get_logger('extractor.router')
        
        # Registry of extractors by file type
        self._extractors: Dict[str, BaseExtractor] = {}
        
        # Initialize available extractors
        self._initialize_extractors()
    
    def _initialize_extractors(self):
        """Initialize all available extractors"""
        # Phase 1: JSON support
        self._extractors['json'] = JSONExtractor()
        
        # Phase 2: Excel and CSV support
        self._extractors['excel'] = ExcelExtractor()
        self._extractors['csv'] = CSVExtractor()
        
        # Future phases will add:
        # Phase 3: self._extractors['text'] = TextExtractor()
        # Phase 4: self._extractors['pdf'] = PDFExtractor()
        # Phase 5: self._extractors['url'] = WebExtractor()
        
        self.logger.info(f"Initialized {len(self._extractors)} extractors: {list(self._extractors.keys())}")
    
    def get_extractor(self, file_type: str) -> Optional[BaseExtractor]:
        """
        Get extractor for a specific file type.
        
        Args:
            file_type: File type string (e.g., 'json', 'excel', 'pdf')
        
        Returns:
            Extractor instance or None if not found
        """
        extractor = self._extractors.get(file_type.lower())
        if not extractor:
            self.logger.warning(f"No extractor found for file type: {file_type}")
        return extractor
    
    def get_extractor_for_file(self, file_path: Path) -> Optional[BaseExtractor]:
        """
        Get extractor based on file extension.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Appropriate extractor or None if not supported
        """
        file_type = Config.get_file_type_from_extension(str(file_path))
        
        if file_type == "unknown":
            self.logger.error(f"Unknown file type for: {file_path}")
            return None
        
        return self.get_extractor(file_type)
    
    def extract(
        self, 
        file_path: Path, 
        file_type: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract content from file using appropriate extractor.
        
        Args:
            file_path: Path to the file
            file_type: Optional file type override (if not provided, detect from extension)
            **kwargs: Additional parameters passed to extractor
        
        Returns:
            ExtractionResult from the appropriate extractor
        """
        self.logger.info(f"Routing extraction for: {file_path.name}")
        
        # Determine file type
        if file_type:
            determined_type = file_type.lower()
        else:
            determined_type = Config.get_file_type_from_extension(str(file_path))
        
        self.logger.info(f"Determined file type: {determined_type}")
        
        # Get appropriate extractor
        extractor = self.get_extractor(determined_type)
        
        if not extractor:
            error_msg = f"No extractor available for file type: {determined_type}"
            self.logger.error(error_msg)
            return ExtractionResult(
                content=None,
                file_type=determined_type,
                extracted_structure="unknown",
                errors=[error_msg]
            )
        
        # Perform extraction
        try:
            result = extractor.extract(file_path, **kwargs)
            
            if result.success:
                self.logger.info(
                    f"Extraction successful: {file_path.name} "
                    f"({result.extracted_structure})"
                )
            else:
                self.logger.error(
                    f"Extraction failed: {file_path.name} - "
                    f"{', '.join(result.errors)}"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during extraction routing: {str(e)}"
            self.logger.error(error_msg)
            return ExtractionResult(
                content=None,
                file_type=determined_type,
                extracted_structure="unknown",
                errors=[error_msg]
            )
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if file type is supported.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if supported, False otherwise
        """
        file_type = Config.get_file_type_from_extension(str(file_path))
        return file_type in self._extractors
    
    def get_supported_types(self) -> list[str]:
        """
        Get list of supported file types.
        
        Returns:
            List of supported file type strings
        """
        return list(self._extractors.keys())
    
    def get_supported_extensions(self) -> Dict[str, list[str]]:
        """
        Get dictionary of supported extensions for each file type.
        
        Returns:
            Dictionary mapping file_type -> list of extensions
        """
        result = {}
        for file_type, extractor in self._extractors.items():
            result[file_type] = extractor.get_supported_extensions()
        return result
    
    def validate_file(self, file_path: Path, file_type: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate if file can be extracted.
        
        Args:
            file_path: Path to the file
            file_type: Optional file type override
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Determine file type
        if file_type:
            determined_type = file_type.lower()
        else:
            determined_type = Config.get_file_type_from_extension(str(file_path))
        
        # Check if supported
        if determined_type not in self._extractors:
            return False, f"Unsupported file type: {determined_type}"
        
        # Get extractor and validate
        extractor = self._extractors[determined_type]
        return extractor.validate_file(file_path)


# Create singleton instance
_router_instance = None

def get_file_type_router() -> FileTypeRouter:
    """Get singleton instance of FileTypeRouter"""
    global _router_instance
    if _router_instance is None:
        _router_instance = FileTypeRouter()
    return _router_instance

