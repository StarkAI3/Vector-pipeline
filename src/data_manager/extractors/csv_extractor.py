"""
CSV Extractor
Extracts content from CSV files with support for various encodings and delimiters
"""
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import chardet

from .base_extractor import BaseExtractor, ExtractionResult, ExtractorMetadata
from ..utils.logger import get_logger

logger = get_logger('extractor.csv')


class CSVExtractor(BaseExtractor):
    """
    Extracts content from CSV files.
    Supports:
    - Various encodings (UTF-8, UTF-16, Latin-1, etc.)
    - Different delimiters (comma, tab, semicolon, pipe)
    - With or without headers
    - Standard data tables
    - FAQ tables
    - Directory/contact lists
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "standard_table",
            "faq_table",
            "directory_list",
            "service_catalog"
        ]
    
    def get_supported_extensions(self) -> List[str]:
        """CSV files only"""
        return ['.csv', '.tsv', '.txt']  # .txt because some CSV files use .txt extension
    
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate CSV file.
        Checks:
        1. File exists and is readable
        2. Extension is .csv, .tsv, or .txt
        3. Content is valid CSV format
        """
        # Check file exists
        is_valid, error = self._validate_file_exists(file_path)
        if not is_valid:
            return False, error
        
        # Check extension
        is_valid, error = self._validate_extension(file_path)
        if not is_valid:
            return False, error
        
        # Try to detect encoding and read CSV
        try:
            encoding = self._detect_encoding(file_path)
            delimiter = self._detect_delimiter(file_path, encoding)
            
            # Try to read first few rows
            pd.read_csv(file_path, encoding=encoding, delimiter=delimiter, nrows=5)
            return True, None
            
        except Exception as e:
            return False, f"Invalid CSV format: {str(e)}"
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from CSV file.
        
        Args:
            file_path: Path to CSV file
            **kwargs: Optional parameters:
                - expected_structure: Expected structure type
                - encoding: File encoding (auto-detected if not provided)
                - delimiter: Column delimiter (auto-detected if not provided)
                - has_header: Whether first row is header (default True)
                - max_rows: Maximum rows to extract
        
        Returns:
            ExtractionResult with extracted content
        """
        self._log_extraction_start(file_path)
        
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            self._log_extraction_failure(file_path, error)
            return self._create_error_result("csv", error)
        
        try:
            # Get parameters
            expected_structure = kwargs.get('expected_structure')
            encoding = kwargs.get('encoding') or self._detect_encoding(file_path)
            delimiter = kwargs.get('delimiter') or self._detect_delimiter(file_path, encoding)
            has_header = kwargs.get('has_header', True)
            max_rows = kwargs.get('max_rows')
            
            self.logger.info(f"Reading CSV with encoding={encoding}, delimiter='{delimiter}'")
            
            # Read CSV file
            if has_header:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    nrows=max_rows
                )
            else:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    header=None,
                    nrows=max_rows
                )
            
            # Detect structure if not provided
            if expected_structure:
                detected_structure = expected_structure
            else:
                detected_structure = self._detect_structure(df)
            
            self.logger.info(f"Detected structure: {detected_structure}")
            
            # Convert DataFrame to content
            content = self._dataframe_to_content(df, detected_structure)
            item_count = len(df)
            
            # Create metadata
            file_size = file_path.stat().st_size
            metadata = ExtractorMetadata.create_metadata(
                file_path=file_path,
                file_size=file_size,
                item_count=item_count,
                detected_structure=detected_structure,
                encoding=encoding,
                delimiter=delimiter,
                has_header=has_header
            )
            
            # Create result
            result = ExtractionResult(
                content=content,
                file_type="csv",
                extracted_structure=detected_structure,
                metadata=metadata
            )
            
            self._log_extraction_success(file_path, result)
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during extraction: {str(e)}"
            self.logger.exception(error_msg)
            self._log_extraction_failure(file_path, error_msg)
            return self._create_error_result("csv", error_msg)
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding using chardet.
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Detected encoding string
        """
        try:
            # Read first 100KB to detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read(100000)
            
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            
            self.logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
            
            # Default to UTF-8 if confidence is low
            if confidence < 0.7:
                self.logger.warning(f"Low encoding confidence, defaulting to UTF-8")
                return 'utf-8'
            
            return encoding or 'utf-8'
            
        except Exception as e:
            self.logger.warning(f"Error detecting encoding: {e}. Defaulting to UTF-8")
            return 'utf-8'
    
    def _detect_delimiter(self, file_path: Path, encoding: str) -> str:
        """
        Detect delimiter used in CSV file.
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding
        
        Returns:
            Detected delimiter character
        """
        try:
            # Read first few lines
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                sample_lines = [f.readline() for _ in range(5)]
                sample = ''.join(sample_lines)
            
            # Common delimiters to check
            common_delimiters = [',', '\t', ';', '|']
            
            # Count occurrences of each delimiter in first line (header)
            first_line = sample_lines[0] if sample_lines else ''
            delimiter_counts = {d: first_line.count(d) for d in common_delimiters}
            
            # Find delimiter with highest count
            detected_delimiter = max(delimiter_counts, key=delimiter_counts.get)
            
            # Verify the delimiter count is consistent across lines
            if delimiter_counts[detected_delimiter] > 0:
                self.logger.info(f"Detected delimiter: '{detected_delimiter}'")
                return detected_delimiter
            
            # Fallback to csv.Sniffer if simple counting fails
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample, delimiters=',\t;|').delimiter
                self.logger.info(f"Detected delimiter (via Sniffer): '{delimiter}'")
                return delimiter
            except:
                pass
            
            # Final fallback
            self.logger.warning("Could not detect delimiter. Defaulting to comma")
            return ','
            
        except Exception as e:
            self.logger.warning(f"Error detecting delimiter: {e}. Defaulting to comma")
            return ','
    
    def _detect_structure(self, df: pd.DataFrame) -> str:
        """
        Detect the structure type of the CSV.
        
        Args:
            df: DataFrame containing CSV data
        
        Returns:
            Structure type string
        """
        if df.empty:
            return "empty"
        
        # Get column count
        col_count = len(df.columns)
        
        # Check for FAQ table (2 or 4 columns with Q&A pattern)
        if self._is_faq_table(df):
            return "faq_table"
        
        # Check for directory/contact list
        if self._is_directory_structure(df):
            return "directory_list"
        
        # Check for service catalog
        if self._is_service_catalog(df):
            return "service_catalog"
        
        # Default: standard table
        return "standard_table"
    
    def _is_faq_table(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame is FAQ table structure"""
        col_count = len(df.columns)
        
        # FAQ tables typically have 2 or 4 columns
        if col_count not in [2, 4]:
            return False
        
        # Check column names for Q&A indicators
        columns_str = ' '.join([str(col).lower() for col in df.columns])
        
        faq_indicators = ['question', 'answer', 'q', 'a', 'faq', 'प्रश्न', 'उत्तर']
        matches = sum(1 for indicator in faq_indicators if indicator in columns_str)
        
        # If we find Q&A indicators in column names
        if matches >= 2:
            return True
        
        # Check first few rows for Q&A pattern in content
        if col_count == 2:
            first_col_sample = df.iloc[:3, 0].astype(str).str.lower()
            if any('?' in str(val) or 'how' in str(val) or 'what' in str(val) for val in first_col_sample):
                return True
        
        return False
    
    def _is_directory_structure(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame is directory/contact list structure"""
        columns_str = ' '.join([str(col).lower() for col in df.columns])
        
        # Look for common directory fields
        directory_indicators = ['name', 'contact', 'email', 'phone', 'position', 'office', 'department']
        matches = sum(1 for indicator in directory_indicators if indicator in columns_str)
        
        return matches >= 2
    
    def _is_service_catalog(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame is service catalog structure"""
        columns_str = ' '.join([str(col).lower() for col in df.columns])
        
        # Look for service-related fields
        service_indicators = ['service', 'scheme', 'description', 'link', 'url', 'department']
        matches = sum(1 for indicator in service_indicators if indicator in columns_str)
        
        return matches >= 2
    
    def _dataframe_to_content(self, df: pd.DataFrame, structure: str) -> List[Dict[str, Any]]:
        """
        Convert DataFrame to list of dictionaries.
        
        Args:
            df: DataFrame to convert
            structure: Detected structure type
        
        Returns:
            List of dictionaries
        """
        # Clean DataFrame - remove rows that are all NaN
        df = df.dropna(how='all')
        
        # Replace NaN with empty strings
        df = df.fillna('')
        
        # Convert to list of dictionaries
        content = df.to_dict('records')
        
        return content
    
    def extract_sample(self, file_path: Path, sample_size: int = 5) -> ExtractionResult:
        """
        Extract a sample of rows for preview/validation.
        
        Args:
            file_path: Path to CSV file
            sample_size: Number of rows to extract
        
        Returns:
            ExtractionResult with sample content
        """
        return self.extract(file_path, max_rows=sample_size)
    
    def get_item_count(self, file_path: Path) -> int:
        """
        Get count of rows in CSV file without full extraction.
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Number of rows
        """
        try:
            encoding = self._detect_encoding(file_path)
            delimiter = self._detect_delimiter(file_path, encoding)
            
            # Use pandas to count rows efficiently
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                usecols=[0]  # Only read first column for counting
            )
            return len(df)
            
        except Exception as e:
            self.logger.error(f"Error counting rows in {file_path}: {e}")
            return 0

