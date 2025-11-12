"""
FAQ Document Processor
Processes FAQ content in document format (text files with Q&A patterns)
"""
from typing import Dict, Any, List, Optional
from ..processors.base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.faq_document')


class FAQDocumentProcessor(BaseProcessor):
    """
    Processes FAQ content from text/markdown documents.
    
    Features:
    - Detects Q&A patterns
    - Creates separate chunks for questions and answers
    - Supports bilingual FAQ (English and Marathi)
    - Creates searchable variations
    - Handles different Q&A formats
    
    Chunk Creation Strategy:
    - For monolingual: 1 chunk per FAQ (question + answer combined)
    - For bilingual: 3 chunks per FAQ (English, Marathi, Combined)
    """
    
    def __init__(self):
        super().__init__()
        self.name = "FAQDocumentProcessor"
    
    def can_process(self, content: Any, structure: str) -> bool:
        """
        Check if this processor can handle the content.
        
        Handles:
        - faq_format structure
        - Content with faq_pairs
        """
        if structure == 'faq_format':
            return True
        
        if isinstance(content, dict) and 'faq_pairs' in content:
            return True
        
        return False
    
    def process(
        self,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process FAQ document content into chunks.
        
        Args:
            content: Extracted content with faq_pairs
            metadata: Processing metadata
            **kwargs: Additional parameters
        
        Returns:
            ProcessingResult with created chunks
        """
        self.logger.info("Processing FAQ document content")
        
        result = ProcessingResult(success=True)
        result.processing_stats['processor'] = self.name
        result.processing_stats['structure'] = 'faq_format'
        
        try:
            faq_pairs = content.get('faq_pairs', [])
            
            if not faq_pairs:
                result.add_error("No FAQ pairs found in content")
                result.success = False
                return result
            
            # Detect if bilingual
            is_bilingual = self._detect_bilingual(faq_pairs, metadata)
            result.processing_stats['is_bilingual'] = is_bilingual
            
            # Process each FAQ pair
            for i, faq in enumerate(faq_pairs):
                question = faq.get('question', '')
                answer = faq.get('answer', '')
                
                if not question or not answer:
                    result.add_warning(f"Skipping incomplete FAQ pair {i+1}")
                    continue
                
                # Create chunks based on language
                if is_bilingual:
                    faq_chunks = self._create_bilingual_faq_chunks(
                        question, answer, i, metadata
                    )
                else:
                    faq_chunks = self._create_monolingual_faq_chunks(
                        question, answer, i, metadata
                    )
                
                # Add chunks to result
                for chunk in faq_chunks:
                    result.add_chunk(chunk)
            
            result.processing_stats['faq_count'] = len(faq_pairs)
            result.processing_stats['chunks_created'] = len(result.chunks)
            
            self.logger.info(
                f"FAQ document processing complete: {len(faq_pairs)} FAQs -> "
                f"{result.valid_chunks} chunks"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error during FAQ document processing: {str(e)}"
            self.logger.error(error_msg)
            result.add_error(error_msg)
            result.success = False
            return result
    
    def _detect_bilingual(
        self,
        faq_pairs: List[Dict[str, str]],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Detect if FAQ content is bilingual.
        Checks metadata and content for language indicators.
        """
        # Check metadata
        language = metadata.get('language', '').lower()
        if language in ['bilingual', 'both', 'english+marathi', 'en+mr']:
            return True
        
        # Check content for Devanagari script (Marathi)
        devanagari_count = 0
        sample_size = min(5, len(faq_pairs))
        
        for faq in faq_pairs[:sample_size]:
            question = faq.get('question', '')
            answer = faq.get('answer', '')
            combined = question + ' ' + answer
            
            # Check for Devanagari Unicode range
            if any('\u0900' <= char <= '\u097F' for char in combined):
                devanagari_count += 1
        
        # If more than 30% have Devanagari, consider bilingual
        return devanagari_count / sample_size > 0.3 if sample_size > 0 else False
    
    def _create_monolingual_faq_chunks(
        self,
        question: str,
        answer: str,
        faq_index: int,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Create single chunk for monolingual FAQ.
        Combines question and answer for better context.
        """
        chunks = []
        
        # Combined chunk (question + answer)
        combined_text = f"Q: {question}\nA: {answer}"
        
        chunk_metadata = {
            'chunk_type': 'faq',
            'faq_index': faq_index,
            'content_type': 'faq',
            'category': metadata.get('category', 'faq_help'),
            'language': metadata.get('language', 'auto'),
            'source_file': metadata.get('source_file', 'unknown'),
            'importance': metadata.get('importance', 'normal'),
            'question': question,
            'answer': answer
        }
        
        chunk = Chunk(
            chunk_id="",  # Will be generated later
            text=combined_text,
            metadata=chunk_metadata
        )
        chunks.append(chunk)
        
        return chunks
    
    def _create_bilingual_faq_chunks(
        self,
        question: str,
        answer: str,
        faq_index: int,
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Create three chunks for bilingual FAQ:
        1. English only
        2. Marathi only  
        3. Combined bilingual
        
        This approach helps with:
        - Language-specific searches
        - Cross-lingual retrieval
        - Better coverage
        """
        chunks = []
        
        # Try to separate English and Marathi content
        en_question, mr_question = self._separate_languages(question)
        en_answer, mr_answer = self._separate_languages(answer)
        
        base_metadata = {
            'chunk_type': 'faq',
            'faq_index': faq_index,
            'content_type': 'faq',
            'category': metadata.get('category', 'faq_help'),
            'source_file': metadata.get('source_file', 'unknown'),
            'importance': metadata.get('importance', 'normal'),
            'is_bilingual': True
        }
        
        # 1. English-only chunk
        if en_question and en_answer:
            en_text = f"Q: {en_question}\nA: {en_answer}"
            en_metadata = base_metadata.copy()
            en_metadata.update({
                'language': 'english',
                'question': en_question,
                'answer': en_answer,
                'chunk_variant': 'english_only'
            })
            
            chunks.append(Chunk(
                chunk_id="",  # Will be generated later
                text=en_text,
                metadata=en_metadata
            ))
        
        # 2. Marathi-only chunk
        if mr_question and mr_answer:
            mr_text = f"Q: {mr_question}\nA: {mr_answer}"
            mr_metadata = base_metadata.copy()
            mr_metadata.update({
                'language': 'marathi',
                'question': mr_question,
                'answer': mr_answer,
                'chunk_variant': 'marathi_only'
            })
            
            chunks.append(Chunk(
                chunk_id="",  # Will be generated later
                text=mr_text,
                metadata=mr_metadata
            ))
        
        # 3. Combined bilingual chunk
        combined_text = f"Q: {question}\nA: {answer}"
        combined_metadata = base_metadata.copy()
        combined_metadata.update({
            'language': 'bilingual',
            'question': question,
            'answer': answer,
            'chunk_variant': 'bilingual_combined'
        })
        
        chunks.append(Chunk(
            chunk_id="",  # Will be generated later
            text=combined_text,
            metadata=combined_metadata
        ))
        
        # If we couldn't separate languages properly, just return combined
        if not chunks or len(chunks) < 2:
            # Fallback to single combined chunk
            return self._create_monolingual_faq_chunks(
                question, answer, faq_index, metadata
            )
        
        return chunks
    
    def _separate_languages(self, text: str) -> tuple[str, str]:
        """
        Attempt to separate English and Marathi text.
        
        Simple approach:
        - Identify Devanagari script as Marathi
        - Identify Latin script as English
        
        Returns:
            Tuple of (english_text, marathi_text)
        """
        if not text:
            return "", ""
        
        english_chars = []
        marathi_chars = []
        
        for char in text:
            if '\u0900' <= char <= '\u097F':
                # Devanagari (Marathi)
                marathi_chars.append(char)
            elif char.isalpha():
                # Latin alphabet (English)
                english_chars.append(char)
            else:
                # Punctuation, numbers, spaces - add to both
                english_chars.append(char)
                marathi_chars.append(char)
        
        english_text = ''.join(english_chars).strip()
        marathi_text = ''.join(marathi_chars).strip()
        
        # Clean up extra spaces
        english_text = ' '.join(english_text.split())
        marathi_text = ' '.join(marathi_text.split())
        
        return english_text, marathi_text
    
    def _has_devanagari(self, text: str) -> bool:
        """Check if text contains Devanagari script"""
        return any('\u0900' <= char <= '\u097F' for char in text)
    
    def _has_latin(self, text: str) -> bool:
        """Check if text contains Latin script"""
        return any('a' <= char.lower() <= 'z' for char in text)
    
    def get_supported_structures(self) -> List[str]:
        """Get list of content structures this processor supports"""
        return ['faq_format']
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """Return processor statistics and configuration"""
        return {
            'name': self.name,
            'chunk_strategy': 'bilingual_3_chunks',
            'supported_structures': self.get_supported_structures(),
            'supports_bilingual': True,
            'languages_supported': ['english', 'marathi', 'bilingual']
        }
    
    def validate_faq_pair(self, question: str, answer: str) -> tuple[bool, Optional[str]]:
        """
        Validate an FAQ pair.
        
        Args:
            question: Question text
            answer: Answer text
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not question or not question.strip():
            return False, "Question is empty"
        
        if not answer or not answer.strip():
            return False, "Answer is empty"
        
        if len(question.strip()) < 5:
            return False, "Question too short (minimum 5 characters)"
        
        if len(answer.strip()) < 10:
            return False, "Answer too short (minimum 10 characters)"
        
        return True, None

