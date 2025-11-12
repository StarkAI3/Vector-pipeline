"""
FAQ Table Processor
Processes FAQ data in table format (2-column or 4-column bilingual)
"""
from typing import Dict, Any, List
import json

from .base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.faq_table')


class FAQTableProcessor(BaseProcessor):
    """
    Processes FAQ data in table format.
    Ideal for:
    - 2-column FAQ (Question, Answer)
    - 4-column bilingual FAQ (Question_EN, Answer_EN, Question_MR, Answer_MR)
    - Creates multiple chunks per FAQ for better retrieval:
      * English-only chunk
      * Marathi-only chunk (if bilingual)
      * Combined bilingual chunk (if bilingual)
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "faq_table"
        ]
    
    def get_supported_structures(self) -> List[str]:
        """Return supported structure types"""
        return self.supported_structures
    
    def can_process(self, content: Any, structure: str) -> bool:
        """Check if can process this content"""
        if structure in self.supported_structures:
            return True
        
        # Check if content looks like FAQ table
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict):
                # Check for Q&A field patterns
                keys_lower = [k.lower() for k in first_item.keys()]
                has_question = any('question' in k or 'q' in k or 'प्रश्न' in k for k in keys_lower)
                has_answer = any('answer' in k or 'a' in k or 'उत्तर' in k for k in keys_lower)
                return has_question and has_answer
        
        return False
    
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process FAQ table content into chunks.
        
        Args:
            content: List of dictionaries (FAQ entries)
            metadata: Processing metadata (category, language, etc.)
            **kwargs: Optional parameters:
                - source_id: Source document ID
                - faq_column_mapping: Dict mapping column names to 'question_en', 'answer_en', etc.
                - create_variants: Create multiple chunks per FAQ (default True)
        
        Returns:
            ProcessingResult with chunks
        """
        self._log_processing_start("faq_table", len(content) if isinstance(content, list) else 1)
        
        result = ProcessingResult()
        
        # Normalize to list
        if isinstance(content, dict):
            content = [content]
        
        if not isinstance(content, list):
            return self._create_error_result("Content must be list or dict")
        
        # Get parameters
        source_id = kwargs.get('source_id', metadata.get('source_id', 'unknown'))
        column_mapping = kwargs.get('faq_column_mapping')
        create_variants = kwargs.get('create_variants', True)
        user_language = metadata.get('language', 'bilingual')
        category = metadata.get('category', 'faq_help')
        
        # Detect column structure
        if not column_mapping and len(content) > 0:
            column_mapping = self._detect_column_mapping(content[0])
        
        self.logger.info(f"FAQ column mapping: {column_mapping}")
        
        # Determine if bilingual
        is_bilingual = self._is_bilingual_structure(column_mapping)
        
        # Process each FAQ entry
        chunk_counter = 0
        for idx, faq_entry in enumerate(content):
            if not isinstance(faq_entry, dict):
                result.add_warning(f"FAQ entry {idx} is not a dictionary, skipping")
                continue
            
            try:
                # Extract Q&A from entry using column mapping
                qa_data = self._extract_qa_data(faq_entry, column_mapping)
                
                if not qa_data:
                    result.add_warning(f"FAQ entry {idx}: Could not extract Q&A data")
                    continue
                
                # Create chunks based on language structure
                if is_bilingual:
                    chunks = self._create_bilingual_chunks(
                        qa_data=qa_data,
                        source_id=source_id,
                        chunk_counter=chunk_counter,
                        source_index=idx,
                        metadata=metadata,
                        category=category
                    )
                else:
                    chunks = self._create_monolingual_chunks(
                        qa_data=qa_data,
                        source_id=source_id,
                        chunk_counter=chunk_counter,
                        source_index=idx,
                        metadata=metadata,
                        category=category,
                        language=user_language
                    )
                
                # Validate and add chunks
                for chunk in chunks:
                    # Validate quality
                    is_valid, reason = self._validate_chunk(chunk)
                    if not is_valid:
                        result.reject_chunk(f"FAQ {idx}: {reason}")
                        continue
                    
                    # Check quality score
                    quality_score, is_acceptable = self._validate_chunk_quality(
                        chunk.text,
                        chunk.language
                    )
                    chunk.quality_score = quality_score
                    
                    if not is_acceptable:
                        result.reject_chunk(f"FAQ {idx}: Low quality score ({quality_score:.2f})")
                        continue
                    
                    # Enrich metadata
                    chunk = self._enrich_with_metadata(
                        chunk,
                        metadata,
                        category=category,
                        item_type="faq_entry"
                    )
                    
                    result.add_chunk(chunk)
                    chunk_counter += 1
                
            except Exception as e:
                error_msg = f"Error processing FAQ {idx}: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Add processing statistics
        result.processing_stats = {
            "total_faqs": len(content),
            "processing_method": "faq_table",
            "is_bilingual": is_bilingual,
            "chunks_per_faq": "3" if is_bilingual else "1"
        }
        
        self._log_processing_complete(result)
        return result
    
    def _detect_column_mapping(self, sample_entry: Dict[str, Any]) -> Dict[str, str]:
        """
        Detect which columns contain question and answer data.
        
        Args:
            sample_entry: Sample FAQ entry (first row)
        
        Returns:
            Dictionary mapping 'question_en', 'answer_en', etc. to actual column names
        """
        mapping = {}
        keys = list(sample_entry.keys())
        keys_lower = [k.lower() for k in keys]
        
        # Try to find English Q&A columns
        for i, key_lower in enumerate(keys_lower):
            key_original = keys[i]
            
            # English Question
            if any(pattern in key_lower for pattern in ['question_en', 'q_en', 'question_english', 'q_eng']):
                mapping['question_en'] = key_original
            elif 'question' in key_lower and 'mr' not in key_lower and 'मराठी' not in key_lower:
                if 'question_en' not in mapping:  # Only if not found more specific match
                    mapping['question_en'] = key_original
            
            # English Answer
            if any(pattern in key_lower for pattern in ['answer_en', 'a_en', 'answer_english', 'a_eng']):
                mapping['answer_en'] = key_original
            elif 'answer' in key_lower and 'mr' not in key_lower and 'मराठी' not in key_lower:
                if 'answer_en' not in mapping:
                    mapping['answer_en'] = key_original
            
            # Marathi Question
            if any(pattern in key_lower for pattern in ['question_mr', 'q_mr', 'question_marathi', 'प्रश्न']):
                mapping['question_mr'] = key_original
            
            # Marathi Answer
            if any(pattern in key_lower for pattern in ['answer_mr', 'a_mr', 'answer_marathi', 'उत्तर']):
                mapping['answer_mr'] = key_original
        
        # If no specific language found, assume 2-column format
        if not mapping and len(keys) >= 2:
            mapping = {
                'question_en': keys[0],
                'answer_en': keys[1]
            }
        
        return mapping
    
    def _is_bilingual_structure(self, column_mapping: Dict[str, str]) -> bool:
        """Check if FAQ structure is bilingual"""
        has_en = 'question_en' in column_mapping and 'answer_en' in column_mapping
        has_mr = 'question_mr' in column_mapping and 'answer_mr' in column_mapping
        return has_en and has_mr
    
    def _extract_qa_data(
        self,
        faq_entry: Dict[str, Any],
        column_mapping: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Extract question and answer data using column mapping.
        
        Args:
            faq_entry: FAQ entry dictionary
            column_mapping: Column mapping
        
        Returns:
            Dictionary with 'question_en', 'answer_en', etc.
        """
        qa_data = {}
        
        for key, column_name in column_mapping.items():
            if column_name in faq_entry:
                value = faq_entry[column_name]
                # Convert to string and clean
                qa_data[key] = str(value).strip() if value else ""
        
        return qa_data
    
    def _create_bilingual_chunks(
        self,
        qa_data: Dict[str, str],
        source_id: str,
        chunk_counter: int,
        source_index: int,
        metadata: Dict[str, Any],
        category: str
    ) -> List[Chunk]:
        """
        Create 3 chunks for bilingual FAQ:
        1. English only
        2. Marathi only
        3. Combined bilingual
        
        Args:
            qa_data: Extracted Q&A data
            source_id: Source document ID
            chunk_counter: Current chunk counter
            source_index: Index in source data
            metadata: Processing metadata
            category: Content category
        
        Returns:
            List of 3 chunks
        """
        chunks = []
        
        question_en = qa_data.get('question_en', '')
        answer_en = qa_data.get('answer_en', '')
        question_mr = qa_data.get('question_mr', '')
        answer_mr = qa_data.get('answer_mr', '')
        
        # 1. English-only chunk
        if question_en and answer_en:
            text_en = f"Question: {question_en}\n\nAnswer: {answer_en}"
            
            chunk_id_en = self._create_chunk_id(
                source_id=source_id,
                chunk_index=chunk_counter,
                text=text_en,
                language='en'
            )
            
            chunk_en = self._create_chunk(
                text=text_en,
                chunk_id=chunk_id_en,
                metadata={
                    "faq_type": "bilingual",
                    "language_variant": "english_only",
                    "question": question_en,
                    "answer": answer_en
                },
                language='en',
                source_index=source_index,
                chunk_index=chunk_counter
            )
            
            chunks.append(chunk_en)
        
        # 2. Marathi-only chunk
        if question_mr and answer_mr:
            text_mr = f"प्रश्न: {question_mr}\n\nउत्तर: {answer_mr}"
            
            chunk_id_mr = self._create_chunk_id(
                source_id=source_id,
                chunk_index=chunk_counter + 1,
                text=text_mr,
                language='mr'
            )
            
            chunk_mr = self._create_chunk(
                text=text_mr,
                chunk_id=chunk_id_mr,
                metadata={
                    "faq_type": "bilingual",
                    "language_variant": "marathi_only",
                    "question": question_mr,
                    "answer": answer_mr
                },
                language='mr',
                source_index=source_index,
                chunk_index=chunk_counter + 1
            )
            
            chunks.append(chunk_mr)
        
        # 3. Combined bilingual chunk
        if (question_en or question_mr) and (answer_en or answer_mr):
            text_combined = ""
            
            if question_en:
                text_combined += f"Question / प्रश्न: {question_en}"
            if question_mr:
                if question_en:
                    text_combined += f" / {question_mr}"
                else:
                    text_combined += f"प्रश्न: {question_mr}"
            
            text_combined += "\n\n"
            
            if answer_en:
                text_combined += f"Answer / उत्तर: {answer_en}"
            if answer_mr:
                if answer_en:
                    text_combined += f"\n\n{answer_mr}"
                else:
                    text_combined += f"उत्तर: {answer_mr}"
            
            chunk_id_combined = self._create_chunk_id(
                source_id=source_id,
                chunk_index=chunk_counter + 2,
                text=text_combined,
                language='bilingual'
            )
            
            chunk_combined = self._create_chunk(
                text=text_combined,
                chunk_id=chunk_id_combined,
                metadata={
                    "faq_type": "bilingual",
                    "language_variant": "combined",
                    "question_en": question_en,
                    "answer_en": answer_en,
                    "question_mr": question_mr,
                    "answer_mr": answer_mr
                },
                language='bilingual',
                source_index=source_index,
                chunk_index=chunk_counter + 2
            )
            
            chunks.append(chunk_combined)
        
        return chunks
    
    def _create_monolingual_chunks(
        self,
        qa_data: Dict[str, str],
        source_id: str,
        chunk_counter: int,
        source_index: int,
        metadata: Dict[str, Any],
        category: str,
        language: str
    ) -> List[Chunk]:
        """
        Create single chunk for monolingual FAQ.
        
        Args:
            qa_data: Extracted Q&A data
            source_id: Source document ID
            chunk_counter: Current chunk counter
            source_index: Index in source data
            metadata: Processing metadata
            category: Content category
            language: Language code
        
        Returns:
            List with single chunk
        """
        question = qa_data.get('question_en', qa_data.get('question_mr', ''))
        answer = qa_data.get('answer_en', qa_data.get('answer_mr', ''))
        
        if not question or not answer:
            return []
        
        # Determine language-specific labels
        if language == 'mr':
            text = f"प्रश्न: {question}\n\nउत्तर: {answer}"
        else:
            text = f"Question: {question}\n\nAnswer: {answer}"
        
        chunk_id = self._create_chunk_id(
            source_id=source_id,
            chunk_index=chunk_counter,
            text=text,
            language=language
        )
        
        chunk = self._create_chunk(
            text=text,
            chunk_id=chunk_id,
            metadata={
                "faq_type": "monolingual",
                "language_variant": language,
                "question": question,
                "answer": answer
            },
            language=language,
            source_index=source_index,
            chunk_index=chunk_counter
        )
        
        return [chunk]

