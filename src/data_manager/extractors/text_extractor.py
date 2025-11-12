"""
Text and Markdown Extractor
Extracts content from plain text (.txt) and markdown (.md) files with structure detection
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

from .base_extractor import BaseExtractor, ExtractionResult, ExtractorMetadata
from ..utils.logger import get_logger

logger = get_logger('extractor.text')


class TextExtractor(BaseExtractor):
    """
    Extracts content from text and markdown files.
    Supports:
    - Plain narrative text documents
    - Structured markdown (with headings, lists, tables, code blocks)
    - FAQ format (Q: A: pattern)
    - Directory listings (Name: Position: Contact: pattern)
    - Mixed content
    
    Automatically detects structure and preserves formatting context.
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "narrative_document",
            "structured_markdown",
            "faq_format",
            "directory_format",
            "mixed_content"
        ]
        
        # Patterns for structure detection
        self.faq_patterns = [
            r'^Q\s*[:\.]\s*.+',  # Q: Question or Q. Question
            r'^Question\s*[:\.]\s*.+',  # Question: ...
            r'^A\s*[:\.]\s*.+',  # A: Answer or A. Answer
            r'^Answer\s*[:\.]\s*.+',  # Answer: ...
            r'^\d+\.\s+.+\?',  # 1. Question?
        ]
        
        self.directory_patterns = [
            r'^Name\s*[:=]',
            r'^Position\s*[:=]',
            r'^Contact\s*[:=]',
            r'^Phone\s*[:=]',
            r'^Email\s*[:=]',
            r'^Department\s*[:=]',
            r'^Office\s*[:=]'
        ]
        
        self.markdown_patterns = {
            'heading': r'^#{1,6}\s+.+',
            'list_bullet': r'^\s*[-*+]\s+.+',
            'list_numbered': r'^\s*\d+\.\s+.+',
            'code_block': r'^```',
            'table': r'^\|.+\|',
            'blockquote': r'^>\s+.+',
            'link': r'\[.+\]\(.+\)',
            'bold': r'\*\*.+\*\*|__.+__',
            'italic': r'\*.+\*|_.+_'
        }
    
    def get_supported_extensions(self) -> List[str]:
        """Text and Markdown files"""
        return ['.txt', '.md', '.markdown']
    
    def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate text/markdown file.
        Checks:
        1. File exists and is readable
        2. Extension is .txt, .md, or .markdown
        3. Content is valid text (not binary)
        """
        # Check file exists
        is_valid, error = self._validate_file_exists(file_path)
        if not is_valid:
            return False, error
        
        # Check extension
        is_valid, error = self._validate_extension(file_path)
        if not is_valid:
            return False, error
        
        # Check if valid text (not binary)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to read first 1KB
                sample = f.read(1024)
                
                # Check for null bytes (indicator of binary file)
                if '\x00' in sample:
                    return False, "File appears to be binary, not text"
                
            return True, None
            
        except UnicodeDecodeError:
            # Try with different encodings
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    f.read(1024)
                # File is readable but with different encoding
                return True, None
            except Exception as e:
                return False, f"Unable to decode file: {str(e)}"
                
        except Exception as e:
            return False, f"Error reading text file: {str(e)}"
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract content from text/markdown file.
        
        Args:
            file_path: Path to text/markdown file
            **kwargs: Optional parameters:
                - expected_structure: If provided, validate against this structure
                - preserve_formatting: Keep markdown syntax (default True for .md files)
                - encoding: Force specific encoding (default: auto-detect)
        
        Returns:
            ExtractionResult with extracted content
        """
        self._log_extraction_start(file_path)
        
        # Validate file
        is_valid, error = self.validate_file(file_path)
        if not is_valid:
            self._log_extraction_failure(file_path, error)
            return self._create_error_result("text", error)
        
        try:
            # Determine if markdown based on extension
            is_markdown = file_path.suffix.lower() in ['.md', '.markdown']
            preserve_formatting = kwargs.get('preserve_formatting', is_markdown)
            
            # Read file content with proper encoding
            content_text = self._read_file_with_encoding(file_path, kwargs.get('encoding'))
            
            if not content_text or not content_text.strip():
                return self._create_error_result("text", "File is empty or contains only whitespace")
            
            # Split into lines for structure analysis
            lines = content_text.split('\n')
            
            # Detect structure
            detected_structure = self._detect_structure(lines, is_markdown)
            
            # Parse content based on structure
            parsed_content = self._parse_content(
                content_text, 
                lines, 
                detected_structure,
                is_markdown,
                preserve_formatting
            )
            
            # Create metadata
            metadata = ExtractorMetadata.create_metadata(
                file_path=file_path,
                file_size=file_path.stat().st_size,
                item_count=len(lines),
                detected_structure=detected_structure,
                line_count=len(lines),
                char_count=len(content_text),
                word_count=len(content_text.split()),
                is_markdown=is_markdown
            )
            
            # Create result
            result = ExtractionResult(
                content=parsed_content,
                file_type="text" if not is_markdown else "markdown",
                extracted_structure=detected_structure,
                metadata=metadata
            )
            
            self._log_extraction_success(file_path, result)
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during text extraction: {str(e)}"
            self._log_extraction_failure(file_path, error_msg)
            return self._create_error_result("text", error_msg)
    
    def _read_file_with_encoding(self, file_path: Path, forced_encoding: Optional[str] = None) -> str:
        """
        Read file with proper encoding detection.
        
        Args:
            file_path: Path to file
            forced_encoding: If provided, use this encoding
        
        Returns:
            File content as string
        """
        if forced_encoding:
            with open(file_path, 'r', encoding=forced_encoding) as f:
                return f.read()
        
        # Try UTF-8 first (most common)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            pass
        
        # Try UTF-16
        try:
            with open(file_path, 'r', encoding='utf-16') as f:
                return f.read()
        except UnicodeDecodeError:
            pass
        
        # Fallback to Latin-1 (never fails)
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
            self.logger.warning(f"File read with latin-1 encoding fallback: {file_path.name}")
            return content
    
    def _detect_structure(self, lines: List[str], is_markdown: bool) -> str:
        """
        Detect the structure type of the text content.
        
        Args:
            lines: List of text lines
            is_markdown: Whether file is markdown
        
        Returns:
            Detected structure type
        """
        if not lines:
            return "empty"
        
        # Count different pattern occurrences
        faq_count = 0
        directory_count = 0
        markdown_feature_count = 0
        
        # Analyze lines
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                continue
            
            # Check for FAQ patterns
            for pattern in self.faq_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    faq_count += 1
                    break
            
            # Check for directory patterns
            for pattern in self.directory_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    directory_count += 1
                    break
            
            # Check for markdown features (if markdown file)
            if is_markdown:
                for feature, pattern in self.markdown_patterns.items():
                    if re.search(pattern, line_stripped):
                        markdown_feature_count += 1
                        break
        
        total_lines = len([l for l in lines if l.strip()])
        
        # Decision logic
        if faq_count > 0 and (faq_count / max(total_lines, 1)) > 0.1:
            # At least 10% of lines are FAQ patterns
            return "faq_format"
        
        if directory_count > 0 and (directory_count / max(total_lines, 1)) > 0.15:
            # At least 15% of lines are directory patterns
            return "directory_format"
        
        if is_markdown and markdown_feature_count > 3:
            # Has multiple markdown features
            return "structured_markdown"
        
        if is_markdown:
            return "structured_markdown"
        
        # Check if it's mixed content (has multiple structure types)
        structure_scores = {
            'faq': faq_count,
            'directory': directory_count,
            'markdown': markdown_feature_count if is_markdown else 0
        }
        
        non_zero_structures = sum(1 for score in structure_scores.values() if score > 0)
        
        if non_zero_structures >= 2:
            return "mixed_content"
        
        # Default to narrative document
        return "narrative_document"
    
    def _parse_content(
        self,
        content_text: str,
        lines: List[str],
        structure: str,
        is_markdown: bool,
        preserve_formatting: bool
    ) -> Dict[str, Any]:
        """
        Parse content based on detected structure.
        
        Args:
            content_text: Full text content
            lines: List of lines
            structure: Detected structure type
            is_markdown: Whether file is markdown
            preserve_formatting: Whether to preserve markdown syntax
        
        Returns:
            Parsed content dictionary
        """
        parsed = {
            "raw_text": content_text,
            "structure": structure,
            "is_markdown": is_markdown
        }
        
        if structure == "faq_format":
            parsed["faq_pairs"] = self._extract_faq_pairs(lines)
            parsed["faq_count"] = len(parsed["faq_pairs"])
        
        elif structure == "directory_format":
            parsed["directory_entries"] = self._extract_directory_entries(lines)
            parsed["entry_count"] = len(parsed["directory_entries"])
        
        elif structure == "structured_markdown":
            parsed["sections"] = self._extract_markdown_sections(lines)
            parsed["section_count"] = len(parsed["sections"])
            
            if not preserve_formatting:
                # Strip markdown syntax
                parsed["plain_text"] = self._strip_markdown_syntax(content_text)
        
        else:  # narrative_document or mixed_content
            # Extract paragraphs
            parsed["paragraphs"] = self._extract_paragraphs(content_text)
            parsed["paragraph_count"] = len(parsed["paragraphs"])
        
        return parsed
    
    def _extract_faq_pairs(self, lines: List[str]) -> List[Dict[str, str]]:
        """
        Extract Q&A pairs from FAQ format text.
        
        Supports patterns like:
        - Q: Question text
        - A: Answer text
        - Question: Text
        - Answer: Text
        - 1. Question?
        - Answer paragraph
        """
        faq_pairs = []
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
            q_match = re.match(r'^(?:Q|Question)\s*[:\.]\s*(.+)', line_stripped, re.IGNORECASE)
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
            a_match = re.match(r'^(?:A|Answer)\s*[:\.]\s*(.+)', line_stripped, re.IGNORECASE)
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
            
            # If we have a current question but no answer started yet, this might be continuation
            if current_question and not current_answer:
                # Check if line looks like start of answer
                if not line_stripped.endswith('?'):
                    current_answer.append(line_stripped)
            elif current_answer:
                # Continue building answer
                current_answer.append(line_stripped)
        
        # Add final FAQ if exists
        if current_question and current_answer:
            faq_pairs.append({
                "question": current_question,
                "answer": " ".join(current_answer).strip()
            })
        
        return faq_pairs
    
    def _extract_directory_entries(self, lines: List[str]) -> List[Dict[str, str]]:
        """
        Extract directory entries from directory format text.
        
        Supports patterns like:
        Name: John Doe
        Position: Manager
        Contact: 123-456-7890
        """
        entries = []
        current_entry = {}
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                # Empty line ends current entry
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                continue
            
            # Try to parse key: value format
            match = re.match(r'^([A-Za-z\s]+?)\s*[:=]\s*(.+)', line_stripped)
            if match:
                key = match.group(1).strip().lower().replace(' ', '_')
                value = match.group(2).strip()
                current_entry[key] = value
        
        # Add final entry if exists
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    def _extract_markdown_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Extract sections from markdown based on headings.
        
        Returns list of sections with heading and content.
        """
        sections = []
        current_section = None
        current_content = []
        
        for line in lines:
            # Check for heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
            
            if heading_match:
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'line': line
                }
                current_content = []
            else:
                # Add to current section content
                current_content.append(line)
        
        # Add final section
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        # If no sections found, create one section with all content
        if not sections:
            sections.append({
                'level': 0,
                'title': 'Document',
                'content': '\n'.join(lines).strip()
            })
        
        return sections
    
    def _extract_paragraphs(self, content_text: str) -> List[str]:
        """
        Extract paragraphs from plain text.
        Paragraphs are separated by blank lines.
        """
        # Split by double newlines (blank lines)
        paragraphs = re.split(r'\n\s*\n', content_text)
        
        # Clean and filter paragraphs
        cleaned = []
        for para in paragraphs:
            para_stripped = para.strip()
            if para_stripped and len(para_stripped) > 10:  # Minimum length
                cleaned.append(para_stripped)
        
        return cleaned
    
    def _strip_markdown_syntax(self, content: str) -> str:
        """
        Strip markdown syntax to get plain text.
        """
        # Remove headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove emphasis
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'__(.+?)__', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'_(.+?)_', r'\1', content)
        
        # Remove links but keep text
        content = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`(.+?)`', r'\1', content)
        
        # Remove list markers
        content = re.sub(r'^\s*[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', '', content, flags=re.MULTILINE)
        
        # Remove blockquotes
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def get_structure_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get quick structure information about a text file without full extraction.
        Useful for preview or validation.
        
        Args:
            file_path: Path to text file
        
        Returns:
            Dictionary with structure information
        """
        try:
            is_markdown = file_path.suffix.lower() in ['.md', '.markdown']
            content = self._read_file_with_encoding(file_path, None)
            lines = content.split('\n')
            
            structure = self._detect_structure(lines, is_markdown)
            
            return {
                'file_type': 'markdown' if is_markdown else 'text',
                'detected_structure': structure,
                'line_count': len(lines),
                'char_count': len(content),
                'word_count': len(content.split()),
                'is_empty': not content.strip()
            }
        except Exception as e:
            return {
                'error': str(e),
                'is_empty': True
            }

