"""
PDF Extractor
Extracts content from PDF files with support for text, tables, scanned documents (OCR), and mixed content
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import PyPDF2
import pdfplumber
from io import BytesIO

from .base_extractor import BaseExtractor, ExtractionResult, ExtractorMetadata
from ..utils.logger import get_logger

logger = get_logger('extractor.pdf')


class PDFExtractor(BaseExtractor):
    """
    Extracts content from PDF files.
    
    Supports:
    - Pure text documents (articles, policies, guidelines)
    - Documents with tables (mixed text and tables)
    - Pure tabular documents (like Excel in PDF format)
    - FAQ documents (Q&A format)
    - Scanned documents (OCR with pytesseract)
    - Form/template documents (form fields and instructions)
    - Complex mixed documents (all of the above)
    
    Features:
    - Text extraction with position information
    - Table extraction with structure preservation
    - OCR for scanned/image-based PDFs
    - Layout and structure detection
    - Multi-page handling
    - Metadata extraction (author, title, creation date)
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "text_document",
            "document_with_tables",
            "mostly_tables",
            "faq_document",
            "scanned_document",
            "form_template",
            "complex_mix"
        ]
    
    def get_supported_extensions(self) -> List[str]:
        """PDF files only"""
        return ['.pdf']
    
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate PDF file.
        Checks:
        1. File exists and is readable
        2. Extension is .pdf
        3. File is a valid PDF (can be opened)
        4. PDF is not encrypted (or can be decrypted)
        """
        # Check file exists
        is_valid, error = self._validate_file_exists(file_path)
        if not is_valid:
            return False, error
        
        # Check extension
        is_valid, error = self._validate_extension(file_path)
        if not is_valid:
            return False, error
        
        # Check if valid PDF
        try:
            with open(file_path, 'rb') as f:
                # Try to read PDF header
                header = f.read(5)
                if header != b'%PDF-':
                    return False, "File is not a valid PDF (missing PDF header)"
                
                # Try to open with PyPDF2
                f.seek(0)
                reader = PyPDF2.PdfReader(f)
                
                # Check if encrypted
                if reader.is_encrypted:
                    # Try to decrypt with empty password
                    try:
                        reader.decrypt('')
                    except:
                        return False, "PDF is password-protected and cannot be read"
                
                # Check if PDF has pages
                num_pages = len(reader.pages)
                if num_pages == 0:
                    return False, "PDF has no pages"
            
            return True, None
            
        except PyPDF2.errors.PdfReadError as e:
            return False, f"Invalid or corrupted PDF: {str(e)}"
        except Exception as e:
            return False, f"Error validating PDF: {str(e)}"
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from PDF file.
        
        Args:
            file_path: Path to PDF file
            **kwargs: Optional parameters:
                - expected_structure: If provided, validate against this structure
                - extract_tables: Whether to extract tables (default: True)
                - extract_images: Whether to extract images (default: False)
                - ocr_enabled: Whether to use OCR for scanned PDFs (default: True)
                - ocr_language: Language for OCR (default: 'eng+mar' for English+Marathi)
                - max_pages: Maximum pages to extract (default: None = all pages)
        
        Returns:
            ExtractionResult with extracted content
        """
        self._log_extraction_start(file_path)
        
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            self._log_extraction_failure(file_path, error)
            return self._create_error_result("pdf", error)
        
        try:
            # Extract configuration from kwargs
            extract_tables = kwargs.get('extract_tables', True)
            extract_images = kwargs.get('extract_images', False)
            ocr_enabled = kwargs.get('ocr_enabled', True)
            ocr_language = kwargs.get('ocr_language', 'eng')
            max_pages = kwargs.get('max_pages', None)
            
            # Open PDF and extract basic info
            with open(file_path, 'rb') as f:
                # Get PDF info with PyPDF2
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Handle encrypted PDFs
                if pdf_reader.is_encrypted:
                    try:
                        pdf_reader.decrypt('')
                    except:
                        return self._create_error_result("pdf", "Failed to decrypt password-protected PDF")
                
                num_pages = len(pdf_reader.pages)
                pdf_metadata = pdf_reader.metadata or {}
                
                # Limit pages if specified
                if max_pages:
                    num_pages = min(num_pages, max_pages)
                
                self.logger.info(f"PDF has {num_pages} pages")
            
            # Extract content using pdfplumber (better for text and tables)
            extracted_content = {
                'pages': [],
                'all_text': '',
                'all_tables': [],
                'page_count': num_pages
            }
            
            with pdfplumber.open(file_path) as pdf:
                for page_num in range(num_pages):
                    page = pdf.pages[page_num]
                    
                    # Extract text
                    page_text = page.extract_text() or ''
                    
                    # Extract tables if requested
                    page_tables = []
                    if extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            page_tables = self._process_tables(tables, page_num + 1)
                    
                    # Store page content
                    page_content = {
                        'page_number': page_num + 1,
                        'text': page_text,
                        'tables': page_tables,
                        'has_tables': len(page_tables) > 0,
                        'text_length': len(page_text),
                        'char_count': len(page_text),
                        'word_count': len(page_text.split()) if page_text else 0
                    }
                    
                    extracted_content['pages'].append(page_content)
                    extracted_content['all_text'] += page_text + '\n'
                    extracted_content['all_tables'].extend(page_tables)
            
            # Check if PDF might be scanned (little to no text extracted)
            total_text_chars = len(extracted_content['all_text'].strip())
            is_scanned = total_text_chars < 100 and num_pages > 0
            
            if is_scanned and ocr_enabled:
                self.logger.info("PDF appears to be scanned. Attempting OCR...")
                ocr_result = self._perform_ocr(file_path, num_pages, ocr_language)
                
                if ocr_result['success']:
                    extracted_content = ocr_result['content']
                    extracted_content['ocr_performed'] = True
                else:
                    extracted_content['ocr_attempted'] = True
                    extracted_content['ocr_error'] = ocr_result.get('error', 'Unknown OCR error')
            else:
                extracted_content['ocr_performed'] = False
            
            # Detect structure
            detected_structure = self._detect_structure(extracted_content, kwargs.get('expected_structure'))
            
            # Parse content based on structure
            parsed_content = self._parse_content(extracted_content, detected_structure)
            
            # Create metadata
            metadata = ExtractorMetadata.create_metadata(
                file_path=file_path,
                file_size=file_path.stat().st_size,
                item_count=num_pages,
                detected_structure=detected_structure,
                page_count=num_pages,
                total_chars=len(extracted_content['all_text']),
                total_words=len(extracted_content['all_text'].split()),
                table_count=len(extracted_content['all_tables']),
                is_scanned=is_scanned,
                ocr_performed=extracted_content.get('ocr_performed', False),
                pdf_title=pdf_metadata.get('/Title', '') if pdf_metadata else '',
                pdf_author=pdf_metadata.get('/Author', '') if pdf_metadata else '',
                pdf_subject=pdf_metadata.get('/Subject', '') if pdf_metadata else '',
                pdf_creator=pdf_metadata.get('/Creator', '') if pdf_metadata else ''
            )
            
            # Create result
            result = ExtractionResult(
                content=parsed_content,
                file_type="pdf",
                extracted_structure=detected_structure,
                metadata=metadata
            )
            
            # Add warnings if needed
            if is_scanned and not ocr_enabled:
                result.warnings.append("PDF appears to be scanned but OCR is disabled")
            
            if total_text_chars < 50:
                result.warnings.append("Very little text extracted from PDF")
            
            self._log_extraction_success(file_path, result)
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during PDF extraction: {str(e)}"
            self.logger.exception(error_msg)
            self._log_extraction_failure(file_path, error_msg)
            return self._create_error_result("pdf", error_msg)
    
    def _process_tables(self, tables: List[List[List[str]]], page_num: int) -> List[Dict[str, Any]]:
        """
        Process extracted tables into structured format.
        
        Args:
            tables: List of tables from pdfplumber
            page_num: Page number where tables were found
        
        Returns:
            List of processed table dictionaries
        """
        processed_tables = []
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) == 0:
                continue
            
            # Clean table data (remove None values)
            cleaned_table = []
            for row in table:
                cleaned_row = [cell.strip() if cell else '' for cell in row]
                # Skip completely empty rows
                if any(cleaned_row):
                    cleaned_table.append(cleaned_row)
            
            if not cleaned_table:
                continue
            
            # Assume first row is header
            headers = cleaned_table[0] if cleaned_table else []
            rows = cleaned_table[1:] if len(cleaned_table) > 1 else []
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = {}
                for i, cell in enumerate(row):
                    header = headers[i] if i < len(headers) else f"Column_{i+1}"
                    row_dict[header] = cell
                table_data.append(row_dict)
            
            processed_table = {
                'page_number': page_num,
                'table_index': table_idx + 1,
                'headers': headers,
                'rows': rows,
                'data': table_data,
                'row_count': len(rows),
                'column_count': len(headers)
            }
            
            processed_tables.append(processed_table)
        
        return processed_tables
    
    def _perform_ocr(self, file_path: Path, num_pages: int, language: str) -> Dict[str, Any]:
        """
        Perform OCR on scanned PDF using pytesseract.
        
        Args:
            file_path: Path to PDF file
            num_pages: Number of pages to OCR
            language: OCR language code (e.g., 'eng', 'mar', 'eng+mar')
        
        Returns:
            Dictionary with OCR results
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            self.logger.info(f"Performing OCR with language: {language}")
            
            # Convert PDF to images
            try:
                images = convert_from_path(str(file_path), first_page=1, last_page=num_pages)
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Failed to convert PDF to images: {str(e)}. Install poppler-utils for OCR support."
                }
            
            # Perform OCR on each page
            ocr_content = {
                'pages': [],
                'all_text': '',
                'all_tables': [],
                'page_count': len(images)
            }
            
            for page_num, image in enumerate(images):
                try:
                    # Extract text using OCR
                    page_text = pytesseract.image_to_string(image, lang=language)
                    
                    page_content = {
                        'page_number': page_num + 1,
                        'text': page_text,
                        'tables': [],  # OCR doesn't extract tables
                        'has_tables': False,
                        'text_length': len(page_text),
                        'char_count': len(page_text),
                        'word_count': len(page_text.split()) if page_text else 0
                    }
                    
                    ocr_content['pages'].append(page_content)
                    ocr_content['all_text'] += page_text + '\n'
                    
                except Exception as e:
                    self.logger.warning(f"OCR failed for page {page_num + 1}: {str(e)}")
                    # Add empty page content
                    ocr_content['pages'].append({
                        'page_number': page_num + 1,
                        'text': '',
                        'tables': [],
                        'has_tables': False,
                        'text_length': 0,
                        'char_count': 0,
                        'word_count': 0,
                        'ocr_error': str(e)
                    })
            
            return {
                'success': True,
                'content': ocr_content
            }
            
        except ImportError as e:
            self.logger.error(f"OCR libraries not available: {str(e)}")
            return {
                'success': False,
                'error': f"OCR libraries not installed: {str(e)}. Install pytesseract and pdf2image."
            }
        except Exception as e:
            self.logger.error(f"OCR failed: {str(e)}")
            return {
                'success': False,
                'error': f"OCR failed: {str(e)}"
            }
    
    def _detect_structure(self, content: Dict[str, Any], expected_structure: Optional[str] = None) -> str:
        """
        Detect the structure type of PDF content.
        
        Args:
            content: Extracted content dictionary
            expected_structure: If provided, validate against this
        
        Returns:
            Detected structure type
        """
        if expected_structure:
            # User specified structure, trust it
            if expected_structure in self.supported_structures:
                return expected_structure
        
        # Auto-detect structure based on content analysis
        total_text_chars = len(content['all_text'].strip())
        table_count = len(content['all_tables'])
        page_count = content['page_count']
        
        # Calculate text vs table ratio
        pages_with_tables = sum(1 for page in content['pages'] if page['has_tables'])
        table_page_ratio = pages_with_tables / max(page_count, 1)
        
        # Check if scanned (OCR was performed)
        if content.get('ocr_performed', False):
            return "scanned_document"
        
        # Check for FAQ patterns
        faq_indicators = self._count_faq_patterns(content['all_text'])
        if faq_indicators > 5:  # At least 5 Q&A patterns found
            return "faq_document"
        
        # Check if mostly tables (>50% of pages have tables and tables are substantial)
        if table_count > 0 and table_page_ratio > 0.5:
            return "mostly_tables"
        
        # Check if document with tables (has both text and tables)
        if table_count > 0 and total_text_chars > 500:
            return "document_with_tables"
        
        # Check for form patterns
        form_indicators = self._count_form_patterns(content['all_text'])
        if form_indicators > 3:
            return "form_template"
        
        # Check for complex mix (multiple indicators)
        complexity_score = 0
        if table_count > 2:
            complexity_score += 1
        if faq_indicators > 0:
            complexity_score += 1
        if form_indicators > 0:
            complexity_score += 1
        if page_count > 10:
            complexity_score += 1
        
        if complexity_score >= 2:
            return "complex_mix"
        
        # Default to text document
        return "text_document"
    
    def _count_faq_patterns(self, text: str) -> int:
        """Count FAQ-like patterns in text"""
        patterns = [
            r'Q\s*[:\.]\s*.+',
            r'Question\s*[:\.]\s*.+',
            r'A\s*[:\.]\s*.+',
            r'Answer\s*[:\.]\s*.+',
            r'\d+\.\s+.+\?',
            r'प्रश्न\s*[:\.]\s*.+',  # Marathi for "Question"
            r'उत्तर\s*[:\.]\s*.+'    # Marathi for "Answer"
        ]
        
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            count += len(matches)
        
        return count
    
    def _count_form_patterns(self, text: str) -> int:
        """Count form-like patterns in text"""
        patterns = [
            r'Name\s*[:_]',
            r'Date\s*[:_]',
            r'Signature\s*[:_]',
            r'Address\s*[:_]',
            r'Application\s+Form',
            r'Form\s+No',
            r'Fill\s+in',
            r'नाव\s*[:_]',  # Marathi for "Name"
            r'दिनांक\s*[:_]',  # Marathi for "Date"
        ]
        
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            count += len(matches)
        
        return count
    
    def _parse_content(self, extracted_content: Dict[str, Any], structure: str) -> Dict[str, Any]:
        """
        Parse and organize extracted content based on structure.
        
        Args:
            extracted_content: Raw extracted content
            structure: Detected structure type
        
        Returns:
            Parsed content dictionary
        """
        parsed = {
            'raw_text': extracted_content['all_text'],
            'structure': structure,
            'page_count': extracted_content['page_count'],
            'pages': extracted_content['pages']
        }
        
        # Add structure-specific parsing
        if structure == 'faq_document':
            parsed['faq_pairs'] = self._extract_faq_pairs(extracted_content['all_text'])
            parsed['faq_count'] = len(parsed['faq_pairs'])
        
        elif structure in ['mostly_tables', 'document_with_tables']:
            parsed['tables'] = extracted_content['all_tables']
            parsed['table_count'] = len(extracted_content['all_tables'])
            
            # Extract text between tables
            if structure == 'document_with_tables':
                parsed['text_sections'] = self._extract_text_sections(extracted_content['pages'])
        
        elif structure == 'scanned_document':
            parsed['ocr_performed'] = True
            parsed['ocr_text'] = extracted_content['all_text']
        
        elif structure == 'form_template':
            parsed['form_fields'] = self._extract_form_fields(extracted_content['all_text'])
        
        # For all structures, extract paragraphs for processing
        parsed['paragraphs'] = self._extract_paragraphs(extracted_content['all_text'])
        
        return parsed
    
    def _extract_faq_pairs(self, text: str) -> List[Dict[str, str]]:
        """
        Extract Q&A pairs from FAQ-formatted PDF text.
        Similar to text_extractor FAQ extraction.
        """
        faq_pairs = []
        lines = text.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                # Empty line might end current answer
                if current_question and current_answer:
                    faq_pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answer).strip()
                    })
                    current_question = None
                    current_answer = []
                continue
            
            # Check if line is a question
            q_match = re.match(r'^(?:Q|Question|प्रश्न)\s*[:\.]\s*(.+)', line_stripped, re.IGNORECASE)
            if q_match:
                # Save previous FAQ if exists
                if current_question and current_answer:
                    faq_pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answer).strip()
                    })
                    current_answer = []
                
                current_question = q_match.group(1).strip()
                continue
            
            # Check if line is an answer
            a_match = re.match(r'^(?:A|Answer|उत्तर)\s*[:\.]\s*(.+)', line_stripped, re.IGNORECASE)
            if a_match:
                current_answer = [a_match.group(1).strip()]
                continue
            
            # Check if line is numbered question
            num_q_match = re.match(r'^\d+\.\s+(.+\?)', line_stripped)
            if num_q_match:
                # Save previous FAQ if exists
                if current_question and current_answer:
                    faq_pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answer).strip()
                    })
                    current_answer = []
                
                current_question = num_q_match.group(1).strip()
                continue
            
            # Continue building answer
            if current_question and not current_answer and not line_stripped.endswith('?'):
                current_answer.append(line_stripped)
            elif current_answer:
                current_answer.append(line_stripped)
        
        # Add final FAQ if exists
        if current_question and current_answer:
            faq_pairs.append({
                "question": current_question,
                "answer": " ".join(current_answer).strip()
            })
        
        return faq_pairs
    
    def _extract_text_sections(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract text sections between tables"""
        sections = []
        
        for page in pages:
            if page['text']:
                section = {
                    'page_number': page['page_number'],
                    'text': page['text'],
                    'char_count': page['char_count'],
                    'word_count': page['word_count']
                }
                sections.append(section)
        
        return sections
    
    def _extract_form_fields(self, text: str) -> List[Dict[str, str]]:
        """Extract form field patterns from text"""
        form_fields = []
        lines = text.split('\n')
        
        field_patterns = [
            r'^([A-Za-z\s]+?)\s*[:_][\s_]*$',  # Field name followed by colon/underscore
            r'^([A-Za-z\s]+?)\s*[:_]\s*(.*)$'   # Field name with potential value
        ]
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            for pattern in field_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    field_name = match.group(1).strip()
                    field_value = match.group(2).strip() if len(match.groups()) > 1 else ''
                    
                    form_fields.append({
                        'field_name': field_name,
                        'field_value': field_value
                    })
                    break
        
        return form_fields
    
    def _extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract paragraphs from PDF text.
        Paragraphs are separated by blank lines.
        """
        # Split by double newlines (blank lines)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter paragraphs
        cleaned = []
        for para in paragraphs:
            para_stripped = para.strip()
            if para_stripped and len(para_stripped) > 20:  # Minimum length
                # Remove excessive whitespace
                para_cleaned = re.sub(r'\s+', ' ', para_stripped)
                cleaned.append(para_cleaned)
        
        return cleaned
    
    def get_pdf_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get quick information about a PDF without full extraction.
        Useful for preview or validation.
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Dictionary with PDF information
        """
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                if reader.is_encrypted:
                    try:
                        reader.decrypt('')
                    except:
                        return {'error': 'PDF is password-protected', 'is_encrypted': True}
                
                metadata = reader.metadata or {}
                num_pages = len(reader.pages)
                
                # Get first page text sample
                first_page_text = ''
                if num_pages > 0:
                    first_page_text = reader.pages[0].extract_text() or ''
                
                return {
                    'page_count': num_pages,
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'is_encrypted': reader.is_encrypted,
                    'first_page_sample': first_page_text[:200],
                    'file_size_mb': file_path.stat().st_size / (1024 * 1024)
                }
        except Exception as e:
            return {
                'error': str(e),
                'is_valid': False
            }

