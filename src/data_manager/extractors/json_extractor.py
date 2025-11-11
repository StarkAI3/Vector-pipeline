"""
JSON Extractor
Extracts content from JSON files with support for various structures
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema
from jsonschema import validate

from .base_extractor import BaseExtractor, ExtractionResult, ExtractorMetadata
from ..utils.logger import get_logger

logger = get_logger('extractor.json')


class JSONExtractor(BaseExtractor):
    """
    Extracts content from JSON files.
    Supports:
    - Array of objects (most common)
    - Nested objects
    - Web scraping output format
    - API response format
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "array_of_objects",
            "nested_objects",
            "web_scraping_output",
            "api_response"
        ]
    
    def get_supported_extensions(self) -> List[str]:
        """JSON files only"""
        return ['.json']
    
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate JSON file.
        Checks:
        1. File exists and is readable
        2. Extension is .json
        3. Content is valid JSON
        """
        # Check file exists
        is_valid, error = self._validate_file_exists(file_path)
        if not is_valid:
            return False, error
        
        # Check extension
        is_valid, error = self._validate_extension(file_path)
        if not is_valid:
            return False, error
        
        # Check if valid JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"
        except UnicodeDecodeError as e:
            return False, f"Unable to decode file (encoding issue): {str(e)}"
        except Exception as e:
            return False, f"Error reading JSON file: {str(e)}"
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from JSON file.
        
        Args:
            file_path: Path to JSON file
            **kwargs: Optional parameters:
                - expected_structure: If provided, validate against this structure
                - max_items: Maximum number of items to extract (for large files)
        
        Returns:
            ExtractionResult with extracted content
        """
        self._log_extraction_start(file_path)
        
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            self._log_extraction_failure(file_path, error)
            return self._create_error_result("json", error)
        
        try:
            # Read JSON content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Detect structure
            detected_structure = self._detect_structure(content)
            
            # Validate against expected structure if provided
            expected_structure = kwargs.get('expected_structure')
            if expected_structure and expected_structure != detected_structure:
                warning = (
                    f"Structure mismatch: Expected '{expected_structure}', "
                    f"detected '{detected_structure}'"
                )
                self.logger.warning(warning)
            
            # Normalize content based on structure
            normalized_content, item_count = self._normalize_content(
                content, 
                detected_structure,
                max_items=kwargs.get('max_items')
            )
            
            # Create metadata
            file_size = file_path.stat().st_size
            metadata = ExtractorMetadata.create_metadata(
                file_path=file_path,
                file_size=file_size,
                item_count=item_count,
                detected_structure=detected_structure
            )
            
            # Create result
            result = ExtractionResult(
                content=normalized_content,
                file_type="json",
                extracted_structure=detected_structure,
                metadata=metadata
            )
            
            self._log_extraction_success(file_path, result)
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during extraction: {str(e)}"
            self._log_extraction_failure(file_path, error_msg)
            return self._create_error_result("json", error_msg)
    
    def _detect_structure(self, content: Any) -> str:
        """
        Detect JSON structure type.
        
        Args:
            content: Parsed JSON content
        
        Returns:
            Structure type string
        """
        # Array of objects (most common)
        if isinstance(content, list):
            if len(content) > 0 and isinstance(content[0], dict):
                return "array_of_objects"
            else:
                return "array"
        
        # Dictionary/Object
        if isinstance(content, dict):
            # Check for web scraping output format
            if self._is_web_scraping_format(content):
                return "web_scraping_output"
            
            # Check for API response format
            if self._is_api_response_format(content):
                return "api_response"
            
            # Check for nested objects
            if self._is_nested_objects(content):
                return "nested_objects"
            
            # Single object
            return "single_object"
        
        return "unknown"
    
    def _is_web_scraping_format(self, content: Dict) -> bool:
        """Check if content matches web scraping output format"""
        # Typical web scraping has: url, title, content fields
        required_fields = {'url', 'content'}
        optional_fields = {'title', 'links', 'metadata'}
        
        has_required = required_fields.issubset(content.keys())
        has_optional = any(field in content for field in optional_fields)
        
        return has_required or (has_optional and 'url' in content)
    
    def _is_api_response_format(self, content: Dict) -> bool:
        """Check if content matches API response format"""
        # Typical API response has: status, data fields
        api_indicators = {'status', 'data', 'results', 'response'}
        return any(field in content for field in api_indicators)
    
    def _is_nested_objects(self, content: Dict) -> bool:
        """Check if content has nested object structure"""
        # Check if multiple keys contain objects or arrays
        nested_count = sum(
            1 for value in content.values() 
            if isinstance(value, (dict, list))
        )
        return nested_count >= 2
    
    def _normalize_content(
        self, 
        content: Any, 
        structure: str,
        max_items: Optional[int] = None
    ) -> tuple[Any, int]:
        """
        Normalize content to a standard format for processing.
        
        Args:
            content: Raw JSON content
            structure: Detected structure type
            max_items: Maximum items to return
        
        Returns:
            Tuple of (normalized_content, item_count)
        """
        if structure == "array_of_objects":
            items = content[:max_items] if max_items else content
            return items, len(content)
        
        elif structure == "web_scraping_output":
            # Wrap in array for consistent processing
            return [content], 1
        
        elif structure == "api_response":
            # Extract the data field
            extracted_data = self._extract_api_data(content)
            if isinstance(extracted_data, list):
                items = extracted_data[:max_items] if max_items else extracted_data
                return items, len(extracted_data)
            else:
                return [extracted_data], 1
        
        elif structure == "nested_objects":
            # Flatten nested objects
            flattened = self._flatten_nested_objects(content)
            items = flattened[:max_items] if max_items else flattened
            return items, len(flattened)
        
        elif structure == "single_object":
            return [content], 1
        
        else:
            # Unknown structure - try to make it processable
            if isinstance(content, list):
                items = content[:max_items] if max_items else content
                return items, len(content)
            else:
                return [content], 1
    
    def _extract_api_data(self, content: Dict) -> Any:
        """Extract data from API response format"""
        # Try common data field names
        for field in ['data', 'results', 'items', 'response', 'content']:
            if field in content:
                return content[field]
        
        # If no standard field found, return entire content
        return content
    
    def _flatten_nested_objects(self, content: Dict, parent_key: str = '') -> List[Dict]:
        """
        Flatten nested objects into a list of dictionaries.
        
        Args:
            content: Nested dictionary
            parent_key: Parent key for nested items
        
        Returns:
            List of flattened dictionaries
        """
        items = []
        
        for key, value in content.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Recursively flatten
                items.extend(self._flatten_nested_objects(value, new_key))
            elif isinstance(value, list):
                # If list of dicts, add each with parent key
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_with_key = {"_parent_key": new_key, "_index": i}
                        item_with_key.update(item)
                        items.append(item_with_key)
                    else:
                        items.append({
                            "_parent_key": new_key,
                            "_index": i,
                            "value": item
                        })
            else:
                # Leaf node - create entry
                items.append({
                    "_key": new_key,
                    "value": value
                })
        
        return items
    
    def extract_sample(self, file_path: Path, sample_size: int = 5) -> ExtractionResult:
        """
        Extract a sample of items for preview/validation.
        
        Args:
            file_path: Path to JSON file
            sample_size: Number of items to extract
        
        Returns:
            ExtractionResult with sample content
        """
        return self.extract(file_path, max_items=sample_size)
    
    def get_item_count(self, file_path: Path) -> int:
        """
        Get count of items in JSON file without full extraction.
        
        Args:
            file_path: Path to JSON file
        
        Returns:
            Number of items
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            if isinstance(content, list):
                return len(content)
            elif isinstance(content, dict):
                # Try to find data array
                for field in ['data', 'results', 'items']:
                    if field in content and isinstance(content[field], list):
                        return len(content[field])
                return 1  # Single object
            else:
                return 1
        except Exception as e:
            self.logger.error(f"Error counting items in {file_path}: {e}")
            return 0

