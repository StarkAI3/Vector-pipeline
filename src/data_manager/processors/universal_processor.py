"""
Universal Processor
Fallback processor that can handle any content structure
"""
from typing import Dict, Any, List
import json

from .base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.universal')


class UniversalProcessor(BaseProcessor):
    """
    Universal fallback processor that handles any content structure.
    Uses conservative chunking approach to ensure content is processable.
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = ["*"]  # Supports everything
    
    def get_supported_structures(self) -> List[str]:
        """Return supported structure types (all)"""
        return self.supported_structures
    
    def can_process(self, content: Any, structure: str) -> bool:
        """Universal processor can handle anything"""
        return True
    
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process any content structure with conservative approach.
        
        Args:
            content: Any content (will be converted to processable format)
            metadata: Processing metadata
            **kwargs: Optional parameters:
                - source_id: Source document ID
                - chunk_size: Target chunk size
        
        Returns:
            ProcessingResult with chunks
        """
        self._log_processing_start("universal", 1)
        
        result = ProcessingResult()
        
        # Get parameters
        source_id = kwargs.get('source_id', metadata.get('source_id', 'unknown'))
        chunk_size = kwargs.get('chunk_size', metadata.get('chunk_size', 'medium'))
        user_language = metadata.get('language', 'en')
        category = metadata.get('category', 'general_information')
        
        from ..core.config import Config
        max_tokens = Config.get_chunk_size(chunk_size)
        
        try:
            # Convert content to processable text
            text_content = self._convert_to_text(content)
            
            if not text_content or len(text_content.strip()) < 10:
                return self._create_error_result("No meaningful content to process")
            
            # Create chunks
            chunks = self._create_chunks_from_text(
                text=text_content,
                source_id=source_id,
                metadata=metadata,
                language=user_language,
                max_tokens=max_tokens
            )
            
            # Validate and add chunks
            chunk_counter = 0
            for chunk in chunks:
                is_valid, reason = self._validate_chunk(chunk)
                if not is_valid:
                    result.reject_chunk(reason)
                    continue
                
                # Quality check
                quality_score, is_acceptable = self._validate_chunk_quality(
                    chunk.text,
                    chunk.language
                )
                chunk.quality_score = quality_score
                
                if not is_acceptable:
                    result.reject_chunk(f"Low quality score ({quality_score:.2f})")
                    continue
                
                # Enrich metadata
                chunk = self._enrich_with_metadata(
                    chunk,
                    metadata,
                    category=category,
                    item_type="universal"
                )
                
                result.add_chunk(chunk)
                chunk_counter += 1
            
            # Add processing statistics
            result.processing_stats = {
                "processing_method": "universal",
                "content_type": type(content).__name__,
                "chunk_size": chunk_size
            }
            
        except Exception as e:
            error_msg = f"Error in universal processing: {str(e)}"
            self.logger.error(error_msg)
            result.add_error(error_msg)
        
        self._log_processing_complete(result)
        return result
    
    def _convert_to_text(self, content: Any) -> str:
        """
        Convert any content type to text representation.
        """
        if isinstance(content, str):
            return content
        
        if isinstance(content, (list, dict)):
            # Try pretty JSON first
            try:
                return json.dumps(content, indent=2, ensure_ascii=False)
            except:
                return str(content)
        
        # For any other type
        return str(content)
    
    def _create_chunks_from_text(
        self,
        text: str,
        source_id: str,
        metadata: Dict[str, Any],
        language: str,
        max_tokens: int
    ) -> List[Chunk]:
        """
        Create chunks from text using simple splitting.
        """
        chunks = []
        
        # Estimate current size
        estimated_tokens = self._estimate_tokens(text)
        
        if estimated_tokens <= max_tokens:
            # Single chunk
            chunk_id = self._create_chunk_id(
                source_id=source_id,
                chunk_index=0,
                text=text,
                language=language
            )
            
            chunk = self._create_chunk(
                text=text,
                chunk_id=chunk_id,
                metadata={},
                language=language,
                chunk_index=0
            )
            
            chunks.append(chunk)
        else:
            # Split into multiple chunks
            text_chunks = self._split_text(text, max_tokens)
            
            for idx, text_chunk in enumerate(text_chunks):
                chunk_id = self._create_chunk_id(
                    source_id=source_id,
                    chunk_index=idx,
                    text=text_chunk,
                    language=language
                )
                
                chunk = self._create_chunk(
                    text=text_chunk,
                    chunk_id=chunk_id,
                    metadata={"part": idx + 1, "total_parts": len(text_chunks)},
                    language=language,
                    chunk_index=idx
                )
                
                chunks.append(chunk)
        
        return chunks
    
    def _split_text(self, text: str, max_tokens: int) -> List[str]:
        """
        Split text into chunks of approximately max_tokens.
        Uses paragraph and sentence boundaries when possible.
        """
        chunks = []
        
        # Try splitting by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_tokens = self._estimate_tokens(para)
            
            if para_tokens > max_tokens:
                # Paragraph itself is too long - split by sentences
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long paragraph
                sentences = self._split_paragraph_into_sentences(para)
                sentence_chunk = []
                sentence_tokens = 0
                
                for sentence in sentences:
                    sentence_token_count = self._estimate_tokens(sentence)
                    
                    if sentence_tokens + sentence_token_count > max_tokens and sentence_chunk:
                        chunks.append(' '.join(sentence_chunk))
                        sentence_chunk = [sentence]
                        sentence_tokens = sentence_token_count
                    else:
                        sentence_chunk.append(sentence)
                        sentence_tokens += sentence_token_count
                
                if sentence_chunk:
                    chunks.append(' '.join(sentence_chunk))
            
            elif current_tokens + para_tokens > max_tokens and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Add remaining content
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _split_paragraph_into_sentences(self, paragraph: str) -> List[str]:
        """Split paragraph into sentences"""
        import re
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        return [s.strip() for s in sentences if s.strip()]
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (~4 chars per token)"""
        return len(text) // 4

