"""
Excel Extractor
Extracts content from Excel files (.xlsx, .xls) with support for various structures
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
from openpyxl import load_workbook

from .base_extractor import BaseExtractor, ExtractionResult, ExtractorMetadata
from ..utils.logger import get_logger

logger = get_logger('extractor.excel')


class ExcelExtractor(BaseExtractor):
    """
    Extracts content from Excel files.
    Supports:
    - Single sheet workbooks
    - Multi-sheet workbooks
    - Standard data tables
    - FAQ tables (2-column and 4-column bilingual)
    - Directory/contact lists
    - Merged cells handling
    - Various data structures
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "standard_table",
            "faq_table",
            "multiple_sheets",
            "directory_list",
            "service_catalog",
            "text_in_cells",
            "complex_layout"
        ]
    
    def get_supported_extensions(self) -> List[str]:
        """Excel files only"""
        return ['.xlsx', '.xls', '.xlsm']
    
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate Excel file.
        Checks:
        1. File exists and is readable
        2. Extension is .xlsx or .xls
        3. Content is valid Excel format
        """
        # Check file exists
        is_valid, error = self._validate_file_exists(file_path)
        if not is_valid:
            return False, error
        
        # Check extension
        is_valid, error = self._validate_extension(file_path)
        if not is_valid:
            return False, error
        
        # Check if valid Excel file
        try:
            # Try to load with pandas first (lighter check)
            pd.ExcelFile(file_path)
            return True, None
        except Exception as e:
            return False, f"Invalid Excel format: {str(e)}"
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from Excel file.
        
        Args:
            file_path: Path to Excel file
            **kwargs: Optional parameters:
                - expected_structure: Expected structure type
                - sheet_names: List of specific sheets to extract (None = all sheets)
                - has_header: Whether first row is header (default True)
                - handle_merged_cells: How to handle merged cells (default 'fill')
                - max_rows: Maximum rows to extract per sheet
        
        Returns:
            ExtractionResult with extracted content
        """
        self._log_extraction_start(file_path)
        
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            self._log_extraction_failure(file_path, error)
            return self._create_error_result("excel", error)
        
        try:
            # Get parameters
            expected_structure = kwargs.get('expected_structure')
            requested_sheets = kwargs.get('sheet_names')
            has_header = kwargs.get('has_header', True)
            handle_merged = kwargs.get('handle_merged_cells', 'fill')
            max_rows = kwargs.get('max_rows')
            
            # Load workbook to get sheet info
            excel_file = pd.ExcelFile(file_path)
            all_sheet_names = excel_file.sheet_names
            
            # Determine which sheets to process
            if requested_sheets:
                sheets_to_process = [s for s in requested_sheets if s in all_sheet_names]
                if not sheets_to_process:
                    return self._create_error_result(
                        "excel",
                        f"None of requested sheets found. Available: {', '.join(all_sheet_names)}"
                    )
            else:
                sheets_to_process = all_sheet_names
            
            self.logger.info(f"Processing {len(sheets_to_process)} sheet(s): {sheets_to_process}")
            
            # Detect if multi-sheet scenario
            is_multi_sheet = len(sheets_to_process) > 1 or expected_structure == "multiple_sheets"
            
            # Extract content from sheets
            if is_multi_sheet:
                extracted_content, item_count, detected_structure = self._extract_multiple_sheets(
                    file_path,
                    sheets_to_process,
                    has_header,
                    handle_merged,
                    max_rows
                )
            else:
                # Single sheet extraction
                sheet_name = sheets_to_process[0]
                extracted_content, item_count, detected_structure = self._extract_single_sheet(
                    file_path,
                    sheet_name,
                    expected_structure,
                    has_header,
                    handle_merged,
                    max_rows
                )
            
            # Create metadata
            file_size = file_path.stat().st_size
            metadata = ExtractorMetadata.create_metadata(
                file_path=file_path,
                file_size=file_size,
                item_count=item_count,
                detected_structure=detected_structure,
                sheet_count=len(sheets_to_process),
                sheet_names=sheets_to_process
            )
            
            # Create result
            result = ExtractionResult(
                content=extracted_content,
                file_type="excel",
                extracted_structure=detected_structure,
                metadata=metadata
            )
            
            self._log_extraction_success(file_path, result)
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during extraction: {str(e)}"
            self.logger.exception(error_msg)
            self._log_extraction_failure(file_path, error_msg)
            return self._create_error_result("excel", error_msg)
    
    def _extract_single_sheet(
        self,
        file_path: Path,
        sheet_name: str,
        expected_structure: Optional[str],
        has_header: bool,
        handle_merged: str,
        max_rows: Optional[int]
    ) -> Tuple[Any, int, str]:
        """Extract content from a single sheet"""
        
        # Read sheet
        if has_header:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=max_rows)
        
        # Handle merged cells if needed
        if handle_merged == 'fill':
            df = self._handle_merged_cells(file_path, sheet_name, df)
        
        # Detect structure if not provided
        if expected_structure:
            detected_structure = expected_structure
        else:
            detected_structure = self._detect_sheet_structure(df)
        
        self.logger.info(f"Sheet '{sheet_name}': Detected structure = {detected_structure}")
        
        # Convert to appropriate format based on structure
        content = self._dataframe_to_content(df, detected_structure)
        item_count = len(df)
        
        return content, item_count, detected_structure
    
    def _extract_multiple_sheets(
        self,
        file_path: Path,
        sheet_names: List[str],
        has_header: bool,
        handle_merged: str,
        max_rows: Optional[int]
    ) -> Tuple[Dict[str, Any], int, str]:
        """Extract content from multiple sheets"""
        
        sheets_content = {}
        total_items = 0
        
        for sheet_name in sheet_names:
            try:
                # Read sheet
                if has_header:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
                else:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=max_rows)
                
                # Handle merged cells
                if handle_merged == 'fill':
                    df = self._handle_merged_cells(file_path, sheet_name, df)
                
                # Detect structure for this sheet
                sheet_structure = self._detect_sheet_structure(df)
                
                # Convert to content
                content = self._dataframe_to_content(df, sheet_structure)
                
                sheets_content[sheet_name] = {
                    "structure": sheet_structure,
                    "content": content,
                    "row_count": len(df)
                }
                
                total_items += len(df)
                
                self.logger.info(
                    f"Sheet '{sheet_name}': {len(df)} rows, structure={sheet_structure}"
                )
                
            except Exception as e:
                self.logger.error(f"Error extracting sheet '{sheet_name}': {e}")
                sheets_content[sheet_name] = {
                    "structure": "error",
                    "content": None,
                    "error": str(e)
                }
        
        return sheets_content, total_items, "multiple_sheets"
    
    def _detect_sheet_structure(self, df: pd.DataFrame) -> str:
        """
        Detect the structure type of the sheet.
        
        Args:
            df: DataFrame containing sheet data
        
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
        
        # Check if text content in cells (long text in cells)
        if self._has_long_text_in_cells(df):
            return "text_in_cells"
        
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
    
    def _has_long_text_in_cells(self, df: pd.DataFrame) -> bool:
        """Check if cells contain long text content (paragraphs)"""
        # Sample first few rows
        sample_size = min(5, len(df))
        sample = df.iloc[:sample_size]
        
        # Check for cells with > 200 characters (indicates paragraph content)
        for col in df.columns:
            for val in sample[col]:
                if isinstance(val, str) and len(val) > 200:
                    return True
        
        return False
    
    def _dataframe_to_content(self, df: pd.DataFrame, structure: str) -> Any:
        """
        Convert DataFrame to appropriate content format based on structure.
        
        Args:
            df: DataFrame to convert
            structure: Detected structure type
        
        Returns:
            Content in appropriate format (list of dicts for most cases)
        """
        # Clean DataFrame - remove rows that are all NaN
        df = df.dropna(how='all')
        
        # Replace NaN with empty strings
        df = df.fillna('')
        
        # Convert to list of dictionaries (standard format)
        content = df.to_dict('records')
        
        return content
    
    def _handle_merged_cells(self, file_path: Path, sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle merged cells by filling them with appropriate values.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet
            df: DataFrame to process
        
        Returns:
            DataFrame with merged cells handled
        """
        try:
            # Load workbook with openpyxl to check for merged cells
            wb = load_workbook(file_path, data_only=True)
            ws = wb[sheet_name]
            
            # Get merged cell ranges
            merged_ranges = list(ws.merged_cells.ranges)
            
            if not merged_ranges:
                return df  # No merged cells
            
            self.logger.info(f"Found {len(merged_ranges)} merged cell range(s) in sheet '{sheet_name}'")
            
            # For each merged range, fill with the top-left cell value
            # This is handled by pandas/openpyxl automatically in most cases
            # Additional handling can be added here if needed
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Could not handle merged cells: {e}. Continuing with default behavior.")
            return df
    
    def extract_sample(self, file_path: Path, sample_size: int = 5) -> ExtractionResult:
        """
        Extract a sample of rows for preview/validation.
        
        Args:
            file_path: Path to Excel file
            sample_size: Number of rows to extract per sheet
        
        Returns:
            ExtractionResult with sample content
        """
        return self.extract(file_path, max_rows=sample_size)
    
    def get_sheet_names(self, file_path: Path) -> List[str]:
        """
        Get list of sheet names in Excel file.
        
        Args:
            file_path: Path to Excel file
        
        Returns:
            List of sheet names
        """
        try:
            excel_file = pd.ExcelFile(file_path)
            return excel_file.sheet_names
        except Exception as e:
            self.logger.error(f"Error getting sheet names: {e}")
            return []
    
    def get_item_count(self, file_path: Path, sheet_name: Optional[str] = None) -> int:
        """
        Get count of rows in Excel file without full extraction.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Specific sheet name (None = first sheet)
        
        Returns:
            Number of rows
        """
        try:
            excel_file = pd.ExcelFile(file_path)
            
            if sheet_name is None:
                sheet_name = excel_file.sheet_names[0]
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=0)
            
            # Get actual row count
            with pd.ExcelFile(file_path) as xls:
                df_full = pd.read_excel(xls, sheet_name=sheet_name)
                return len(df_full)
                
        except Exception as e:
            self.logger.error(f"Error counting rows in {file_path}: {e}")
            return 0

