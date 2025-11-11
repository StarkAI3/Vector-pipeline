"""
Web Content Processor
Processes scraped web content with semantic chunking
"""
from typing import Dict, Any, List
import re

from .base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.web_content')


class WebContentProcessor(BaseProcessor):
    """
    Processes web scraping output with intelligent chunking.
    Handles:
    - Article/blog content
    - Web pages with sections
    - Preserves URLs and links
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "web_scraping_output",
            "article",
            "web_content"
        ]
    
    def get_supported_structures(self) -> List[str]:
        """Return supported structure types"""
        return self.supported_structures
    
    def can_process(self, content: Any, structure: str) -> bool:
        """Check if content is web scraping output"""
        if structure in self.supported_structures:
            return True
        
        # Check for web scraping format
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict):
                return 'url' in first_item and 'content' in first_item
        
        if isinstance(content, dict):
            return 'url' in content and 'content' in content
        
        return False
    
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process web content into semantic chunks.
        
        Args:
            content: Web scraping output (dict or list of dicts)
            metadata: Processing metadata
            **kwargs: Optional parameters:
                - source_id: Source document ID
                - chunk_size: Target chunk size in tokens
                - preserve_sections: Keep section structure (default True)
        
        Returns:
            ProcessingResult with chunks
        """
        self._log_processing_start("web_content", len(content) if isinstance(content, list) else 1)
        
        result = ProcessingResult()
        
        # Normalize to list
        if isinstance(content, dict):
            content = [content]
        
        if not isinstance(content, list):
            return self._create_error_result("Content must be dict or list of dicts")
        
        # Get parameters
        source_id = kwargs.get('source_id', metadata.get('source_id', 'unknown'))
        chunk_size = kwargs.get('chunk_size', metadata.get('chunk_size', 'medium'))
        preserve_sections = kwargs.get('preserve_sections', True)
        user_language = metadata.get('language', 'en')
        category = metadata.get('category', 'general_information')
        
        from ..core.config import Config
        max_tokens = Config.get_chunk_size(chunk_size)
        
        # Process each web page
        chunk_counter = 0
        for idx, page in enumerate(content):
            if not isinstance(page, dict):
                result.add_warning(f"Page {idx} is not a dictionary, skipping")
                continue
            
            try:
                # Extract page data
                url = page.get('url', '')
                title = page.get('title', '')
                page_content = page.get('content', '')
                links = page.get('links', [])
                page_metadata = page.get('metadata', {})
                
                if not page_content:
                    result.add_warning(f"Page {idx} has no content, skipping")
                    continue
                
                # Create chunks from content
                page_chunks = self._create_content_chunks(
                    content=page_content,
                    url=url,
                    title=title,
                    links=links,
                    source_id=source_id,
                    base_chunk_index=chunk_counter,
                    source_index=idx,
                    metadata=metadata,
                    language=user_language,
                    max_tokens=max_tokens,
                    preserve_sections=preserve_sections
                )
                
                # Validate and add chunks
                for chunk in page_chunks:
                    is_valid, reason = self._validate_chunk(chunk)
                    if not is_valid:
                        result.reject_chunk(f"Page {idx} chunk: {reason}")
                        continue
                    
                    # Quality check
                    quality_score, is_acceptable = self._validate_chunk_quality(
                        chunk.text,
                        chunk.language
                    )
                    chunk.quality_score = quality_score
                    
                    if not is_acceptable:
                        result.reject_chunk(f"Page {idx} chunk: Low quality ({quality_score:.2f})")
                        continue
                    
                    # Enrich metadata
                    chunk = self._enrich_with_metadata(
                        chunk,
                        metadata,
                        category=category,
                        item_type="web_content",
                        source_url=url,
                        page_title=title
                    )
                    
                    result.add_chunk(chunk)
                    chunk_counter += 1
                
            except Exception as e:
                error_msg = f"Error processing page {idx}: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Add processing statistics
        result.processing_stats = {
            "total_pages": len(content),
            "processing_method": "web_content",
            "chunk_size": chunk_size
        }
        
        self._log_processing_complete(result)
        return result
    
    def _create_content_chunks(
        self,
        content: str,
        url: str,
        title: str,
        links: List[str],
        source_id: str,
        base_chunk_index: int,
        source_index: int,
        metadata: Dict[str, Any],
        language: str,
        max_tokens: int,
        preserve_sections: bool
    ) -> List[Chunk]:
        """
        Create chunks from web content using semantic splitting.
        """
        chunks = []
        
        # Clean content
        cleaned_content = self._clean_web_content(content)
        
        if preserve_sections:
            # Try to split by sections (headers, paragraphs)
            sections = self._split_into_sections(cleaned_content)
        else:
            sections = [cleaned_content]
        
        # Create chunks from sections
        current_chunk_index = base_chunk_index
        for section_idx, section in enumerate(sections):
            # Skip very short sections
            if len(section.strip()) < 50:
                continue
            
            # Split long sections
            if self._estimate_tokens(section) > max_tokens:
                subsections = self._split_long_section(section, max_tokens)
            else:
                subsections = [section]
            
            # Create chunks
            for subsection in subsections:
                # Add title context if this is first chunk
                chunk_text = subsection
                if current_chunk_index == base_chunk_index and title:
                    chunk_text = f"{title}\n\n{subsection}"
                
                # Create chunk ID
                chunk_id = self._create_chunk_id(
                    source_id=source_id,
                    chunk_index=current_chunk_index,
                    text=chunk_text,
                    language=language
                )
                
                # Create chunk
                chunk = self._create_chunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    metadata={
                        "source_url": url,
                        "page_title": title,
                        "section_index": section_idx
                    },
                    language=language,
                    source_index=source_index,
                    chunk_index=current_chunk_index
                )
                
                chunks.append(chunk)
                current_chunk_index += 1
        
        return chunks
    
    def _clean_web_content(self, content: str) -> str:
        """Clean web content from HTML artifacts and excessive whitespace"""
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove excessive spaces
        content = re.sub(r' {2,}', ' ', content)
        
        # Remove common HTML artifacts
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'&amp;', '&', content)
        content = re.sub(r'&lt;', '<', content)
        content = re.sub(r'&gt;', '>', content)
        
        return content.strip()
    
    def _split_into_sections(self, content: str) -> List[str]:
        """
        Split content into logical sections.
        Uses paragraph breaks and headers as section boundaries.
        """
        # Split by double newlines (paragraph breaks)
        paragraphs = content.split('\n\n')
        
        sections = []
        current_section = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if this looks like a header (short, possibly all caps or title case)
            is_header = (
                len(para) < 100 and
                (para.isupper() or para.istitle()) and
                not para.endswith('.')
            )
            
            if is_header and current_section:
                # Start new section
                sections.append('\n\n'.join(current_section))
                current_section = [para]
            else:
                current_section.append(para)
        
        # Add remaining section
        if current_section:
            sections.append('\n\n'.join(current_section))
        
        return sections
    
    def _split_long_section(self, section: str, max_tokens: int) -> List[str]:
        """Split long section into smaller chunks"""
        # Simple sentence-based splitting
        sentences = re.split(r'(?<=[.!?])\s+', section)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation.
        Assumes ~4 characters per token on average.
        """
        return len(text) // 4

