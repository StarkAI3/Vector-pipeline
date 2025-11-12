"""
Text Processor
Processes narrative text and markdown documents with semantic chunking
"""
import re
from typing import Dict, Any, List, Optional
from ..processors.base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.text')


class TextProcessor(BaseProcessor):
    """
    Processes narrative text and structured markdown documents.
    
    Features:
    - Semantic chunking with heading preservation
    - Paragraph-aware splitting
    - Markdown structure preservation
    - Handles both plain text and markdown files
    - Supports bilingual content
    """
    
    def __init__(self):
        super().__init__()
        self.name = "TextProcessor"
        
        # Chunking parameters
        self.target_chunk_size = 512  # Target tokens per chunk
        self.min_chunk_size = 20      # Minimum tokens per chunk (lowered for short text sections)
        self.max_chunk_size = 768     # Maximum tokens per chunk
        self.chunk_overlap = 50       # Overlap between chunks
    
    def can_process(self, content: Any, structure: str) -> bool:
        """
        Check if this processor can handle the content.
        
        Handles:
        - narrative_document
        - structured_markdown
        - mixed_content (as fallback)
        """
        if structure in ['narrative_document', 'structured_markdown', 'mixed_content']:
            return True
        
        # Check if content has expected text structure
        if isinstance(content, dict):
            return 'raw_text' in content or 'paragraphs' in content or 'sections' in content
        
        return False
    
    def process(
        self,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process text/markdown content into chunks.
        
        Args:
            content: Extracted content dictionary
            metadata: Processing metadata
            **kwargs: Additional parameters
        
        Returns:
            ProcessingResult with created chunks
        """
        self.logger.info(f"Processing text content with structure: {content.get('structure')}")
        
        result = ProcessingResult(success=True)
        result.processing_stats['processor'] = self.name
        result.processing_stats['structure'] = content.get('structure')
        
        try:
            structure = content.get('structure', 'narrative_document')
            is_markdown = content.get('is_markdown', False)
            
            # Route to appropriate processing method
            if structure == 'structured_markdown' and 'sections' in content:
                chunks = self._process_markdown_sections(content, metadata)
            elif 'paragraphs' in content:
                chunks = self._process_paragraphs(content, metadata)
            else:
                # Process raw text
                chunks = self._process_raw_text(content, metadata)
            
            # Validate and add chunks
            for chunk in chunks:
                if self._validate_chunk(chunk):
                    result.add_chunk(chunk)
                else:
                    result.add_warning(f"Invalid chunk filtered: {chunk.text[:50]}...")
            
            result.processing_stats['chunks_created'] = len(result.chunks)
            result.processing_stats['is_markdown'] = is_markdown
            
            self.logger.info(f"Text processing complete: {result.valid_chunks} chunks created")
            
            return result
            
        except Exception as e:
            error_msg = f"Error during text processing: {str(e)}"
            self.logger.error(error_msg)
            result.add_error(error_msg)
            result.success = False
            return result
    
    def _process_markdown_sections(
        self,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Process markdown content by sections (based on headings).
        Preserves document structure and hierarchy.
        """
        chunks = []
        sections = content.get('sections', [])
        
        for i, section in enumerate(sections):
            section_title = section.get('title', f'Section {i+1}')
            section_content = section.get('content', '')
            section_level = section.get('level', 1)
            
            if not section_content.strip():
                continue
            
            # Create context with heading
            section_context = f"# {section_title}\n\n{section_content}"
            
            # Check if section is small enough for single chunk
            token_count = self._estimate_tokens(section_context)
            
            if token_count <= self.max_chunk_size:
                # Single chunk for section
                chunk = self._create_chunk(
                    text=section_context,
                    chunk_type='section',
                    metadata=metadata,
                    extra_metadata={
                        'section_title': section_title,
                        'section_level': section_level,
                        'section_index': i,
                        'is_complete_section': True
                    }
                )
                chunks.append(chunk)
            else:
                # Split section into multiple chunks
                section_chunks = self._split_large_text(
                    text=section_content,
                    context_prefix=f"Section: {section_title}\n\n",
                    metadata=metadata,
                    extra_metadata={
                        'section_title': section_title,
                        'section_level': section_level,
                        'section_index': i,
                        'is_complete_section': False
                    }
                )
                chunks.extend(section_chunks)
        
        return chunks
    
    def _process_paragraphs(
        self,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Process content by paragraphs.
        Groups paragraphs into appropriately-sized chunks.
        """
        chunks = []
        paragraphs = content.get('paragraphs', [])
        
        if not paragraphs:
            return chunks
        
        current_chunk_text = []
        current_token_count = 0
        
        for i, paragraph in enumerate(paragraphs):
            paragraph_tokens = self._estimate_tokens(paragraph)
            
            # If single paragraph is too large, split it
            if paragraph_tokens > self.max_chunk_size:
                # Save current chunk if exists
                if current_chunk_text:
                    chunk = self._create_chunk(
                        text='\n\n'.join(current_chunk_text),
                        chunk_type='paragraph_group',
                        metadata=metadata,
                        extra_metadata={'paragraph_count': len(current_chunk_text)}
                    )
                    chunks.append(chunk)
                    current_chunk_text = []
                    current_token_count = 0
                
                # Split large paragraph
                para_chunks = self._split_large_text(
                    text=paragraph,
                    context_prefix="",
                    metadata=metadata,
                    extra_metadata={'source': 'large_paragraph'}
                )
                chunks.extend(para_chunks)
                continue
            
            # Check if adding this paragraph would exceed target size
            if current_token_count + paragraph_tokens > self.target_chunk_size and current_chunk_text:
                # Create chunk from accumulated paragraphs
                chunk = self._create_chunk(
                    text='\n\n'.join(current_chunk_text),
                    chunk_type='paragraph_group',
                    metadata=metadata,
                    extra_metadata={'paragraph_count': len(current_chunk_text)}
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap (include last paragraph)
                if len(current_chunk_text) > 0:
                    current_chunk_text = [current_chunk_text[-1], paragraph]
                    current_token_count = self._estimate_tokens(current_chunk_text[-1]) + paragraph_tokens
                else:
                    current_chunk_text = [paragraph]
                    current_token_count = paragraph_tokens
            else:
                # Add paragraph to current chunk
                current_chunk_text.append(paragraph)
                current_token_count += paragraph_tokens
        
        # Add final chunk
        if current_chunk_text:
            chunk = self._create_chunk(
                text='\n\n'.join(current_chunk_text),
                chunk_type='paragraph_group',
                metadata=metadata,
                extra_metadata={'paragraph_count': len(current_chunk_text)}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _process_raw_text(
        self,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Process raw text without predefined structure.
        Creates paragraph structure and chunks appropriately.
        """
        raw_text = content.get('raw_text', '')
        
        if not raw_text.strip():
            return []
        
        # Extract paragraphs from raw text
        paragraphs = self._extract_paragraphs_from_text(raw_text)
        
        # Process as paragraphs
        temp_content = {'paragraphs': paragraphs}
        return self._process_paragraphs(temp_content, metadata)
    
    def _split_large_text(
        self,
        text: str,
        context_prefix: str,
        metadata: Dict[str, Any],
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split large text into multiple chunks with overlap.
        Tries to split at sentence boundaries.
        """
        chunks = []
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return chunks
        
        current_chunk_sentences = []
        current_token_count = len(context_prefix.split()) if context_prefix else 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_token_count + sentence_tokens > self.target_chunk_size and current_chunk_sentences:
                # Create chunk
                chunk_text = context_prefix + ' '.join(current_chunk_sentences)
                chunk = self._create_chunk(
                    text=chunk_text,
                    chunk_type='text_split',
                    metadata=metadata,
                    extra_metadata=extra_metadata or {}
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk_sentences[-2:] if len(current_chunk_sentences) >= 2 else []
                current_chunk_sentences = overlap_sentences + [sentence]
                current_token_count = sum(self._estimate_tokens(s) for s in current_chunk_sentences)
            else:
                current_chunk_sentences.append(sentence)
                current_token_count += sentence_tokens
        
        # Add final chunk
        if current_chunk_sentences:
            chunk_text = context_prefix + ' '.join(current_chunk_sentences)
            chunk = self._create_chunk(
                text=chunk_text,
                chunk_type='text_split',
                metadata=metadata,
                extra_metadata=extra_metadata or {}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        chunk_type: str,
        metadata: Dict[str, Any],
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk with metadata"""
        chunk_metadata = {
            'chunk_type': chunk_type,
            'content_type': metadata.get('content_type', 'text'),
            'category': metadata.get('category', 'general_information'),
            'language': metadata.get('language', 'auto'),
            'source_file': metadata.get('source_file', 'unknown'),
            'importance': metadata.get('importance', 'normal')
        }
        
        if extra_metadata:
            chunk_metadata.update(extra_metadata)
        
        return Chunk(
            chunk_id="",  # Will be generated later
            text=text,
            metadata=chunk_metadata
        )
    
    def _validate_chunk(self, chunk: Chunk) -> bool:
        """Validate that chunk meets quality requirements"""
        if not chunk.text or not chunk.text.strip():
            return False
        
        token_count = self._estimate_tokens(chunk.text)
        
        if token_count < self.min_chunk_size:
            return False
        
        if token_count > self.max_chunk_size * 1.5:  # Allow some flexibility
            return False
        
        return True
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Simple approximation: ~0.75 tokens per word for English.
        """
        if not text:
            return 0
        
        words = text.split()
        return int(len(words) * 0.75)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        Handles common sentence endings.
        """
        # Simple sentence splitting
        # This can be improved with NLTK or spaCy for production
        sentence_endings = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_endings, text)
        
        # Clean and filter
        cleaned = []
        for sentence in sentences:
            sentence_stripped = sentence.strip()
            if sentence_stripped and len(sentence_stripped) > 10:
                cleaned.append(sentence_stripped)
        
        return cleaned
    
    def _extract_paragraphs_from_text(self, text: str) -> List[str]:
        """Extract paragraphs from raw text"""
        # Split by double newlines (blank lines)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter
        cleaned = []
        for para in paragraphs:
            para_stripped = para.strip()
            # Replace single newlines with spaces within paragraph
            para_normalized = re.sub(r'\s+', ' ', para_stripped)
            
            if para_normalized and len(para_normalized) > 20:
                cleaned.append(para_normalized)
        
        return cleaned
    
    def get_supported_structures(self) -> List[str]:
        """Get list of content structures this processor supports"""
        return [
            'narrative_document',
            'structured_markdown',
            'mixed_content'
        ]
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """Return processor statistics and configuration"""
        return {
            'name': self.name,
            'target_chunk_size': self.target_chunk_size,
            'min_chunk_size': self.min_chunk_size,
            'max_chunk_size': self.max_chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'supported_structures': self.get_supported_structures()
        }

