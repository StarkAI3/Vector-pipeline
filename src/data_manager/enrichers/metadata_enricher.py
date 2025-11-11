"""
Metadata Enricher for DMA Bot Data Management System
Adds comprehensive metadata to chunks based on user selections and content analysis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.config import config
from ..utils.logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.metadata_enricher")


class MetadataEnricher:
    """Enrich chunks with metadata for better retrieval"""
    
    @classmethod
    def enrich_chunk_metadata(
        cls,
        chunk_text: str,
        chunk_index: int,
        source_metadata: Dict[str, Any],
        language: str,
        special_elements: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Create comprehensive metadata for a chunk
        
        Args:
            chunk_text: The chunk text
            chunk_index: Index of chunk in document
            source_metadata: Metadata from source document
            language: Detected language of chunk
            special_elements: Extracted special elements (URLs, emails, etc.)
            
        Returns:
            Dict of metadata
        """
        metadata = {
            # Source information
            "source_id": source_metadata.get("source_id", ""),
            "source_filename": source_metadata.get("filename", ""),
            "source_type": source_metadata.get("file_type", ""),
            
            # Content classification
            "category": source_metadata.get("category", "general_information"),
            "content_structure": source_metadata.get("content_structure", ""),
            "content_type": cls._determine_content_type(
                source_metadata.get("content_structure", "")
            ),
            
            # Language information
            "language": language,
            "is_bilingual": language == "bilingual",
            
            # Chunk information
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_text),
            "word_count": len(chunk_text.split()),
            
            # Importance and priority
            "importance": source_metadata.get("importance", "normal"),
            "priority_score": cls._calculate_priority_score(
                source_metadata.get("importance", "normal"),
                chunk_text
            ),
            
            # Timestamps
            "uploaded_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            
            # Special elements
            "has_urls": False,
            "has_emails": False,
            "has_phone_numbers": False,
            "has_dates": False,
        }
        
        # Add special elements if present
        if special_elements:
            metadata["has_urls"] = len(special_elements.get("urls", [])) > 0
            metadata["has_emails"] = len(special_elements.get("emails", [])) > 0
            metadata["has_phone_numbers"] = len(special_elements.get("phone_numbers", [])) > 0
            
            # Store special elements for reference
            if metadata["has_urls"]:
                metadata["urls"] = special_elements["urls"][:5]  # Limit to 5
            if metadata["has_emails"]:
                metadata["emails"] = special_elements["emails"][:3]  # Limit to 3
            if metadata["has_phone_numbers"]:
                metadata["phone_numbers"] = special_elements["phone_numbers"][:3]
        
        # Content characteristics
        metadata.update(cls._analyze_content_characteristics(chunk_text))
        
        logger.debug(f"Enriched metadata for chunk {chunk_index}")
        
        return metadata
    
    @classmethod
    def enrich_source_metadata(
        cls,
        filename: str,
        file_type: str,
        file_hash: str,
        user_selections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create metadata for the source document
        
        Args:
            filename: Original filename
            file_type: File type
            file_hash: File content hash
            user_selections: User's questionnaire responses
            
        Returns:
            Dict of source metadata
        """
        metadata = {
            "filename": filename,
            "file_type": file_type,
            "file_hash": file_hash,
            "category": user_selections.get("category", "general_information"),
            "content_structure": user_selections.get("content_structure", ""),
            "language": user_selections.get("language", "en"),
            "importance": user_selections.get("importance", "normal"),
            "special_elements": user_selections.get("special_elements", []),
            "chunk_size": user_selections.get("chunk_size", "medium"),
            "uploaded_at": datetime.now().isoformat(),
        }
        
        return metadata
    
    @classmethod
    def _determine_content_type(cls, content_structure: str) -> str:
        """
        Map content structure to content type for filtering
        
        Args:
            content_structure: User-selected structure
            
        Returns:
            Content type string
        """
        # Map structures to high-level types
        type_mapping = {
            # FAQ types
            "faq_document": "faq",
            "faq_table": "faq",
            "faq_format": "faq",
            "faq_page": "faq",
            
            # Directory types
            "directory_list": "directory",
            "directory_listing": "directory",
            "directory_format": "directory",
            
            # Table types
            "standard_table": "table",
            "mostly_tables": "table",
            "table_page": "table",
            
            # Document types
            "text_document": "document",
            "narrative_document": "document",
            "article": "document",
            
            # Service types
            "service_catalog": "service",
            "service_page": "service",
        }
        
        return type_mapping.get(content_structure, "general")
    
    @classmethod
    def _calculate_priority_score(cls, importance: str, chunk_text: str) -> float:
        """
        Calculate priority score for ranking
        
        Args:
            importance: User-set importance level
            chunk_text: Chunk text
            
        Returns:
            Priority score (0.0 to 1.0)
        """
        # Base score from importance
        importance_scores = {
            "critical": 1.0,
            "high": 0.8,
            "normal": 0.5,
            "low": 0.3
        }
        
        base_score = importance_scores.get(importance, 0.5)
        
        # Boost for certain keywords (government-specific)
        boost_keywords = [
            "application", "apply", "form", "deadline", "contact",
            "email", "phone", "address", "officer", "department",
            "अर्ज", "संपर्क", "फॉर्म", "कार्यालय"
        ]
        
        text_lower = chunk_text.lower()
        keyword_boost = sum(0.05 for keyword in boost_keywords if keyword in text_lower)
        
        # Combine and cap at 1.0
        final_score = min(1.0, base_score + keyword_boost)
        
        return round(final_score, 2)
    
    @classmethod
    def _analyze_content_characteristics(cls, text: str) -> Dict[str, Any]:
        """
        Analyze text characteristics for metadata
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict of characteristics
        """
        characteristics = {
            "has_numbers": any(char.isdigit() for char in text),
            "has_uppercase": any(char.isupper() for char in text),
            "has_special_chars": any(not char.isalnum() and not char.isspace() for char in text),
            "avg_word_length": 0,
            "sentence_count": 0,
        }
        
        # Word analysis
        words = text.split()
        if words:
            characteristics["avg_word_length"] = sum(len(word) for word in words) / len(words)
        
        # Sentence count (rough estimate)
        sentence_endings = ['.', '!', '?', '।']  # Including Devanagari sentence ending
        characteristics["sentence_count"] = sum(text.count(ending) for ending in sentence_endings)
        
        return characteristics
    
    @classmethod
    def add_processing_metadata(
        cls,
        metadata: Dict[str, Any],
        processing_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add processing-related metadata
        
        Args:
            metadata: Existing metadata
            processing_info: Processing details
            
        Returns:
            Updated metadata
        """
        metadata["processing"] = {
            "job_id": processing_info.get("job_id", ""),
            "processed_at": datetime.now().isoformat(),
            "processor_type": processing_info.get("processor_type", ""),
            "embedding_model": config.EMBEDDING_MODEL_NAME,
            "chunk_method": processing_info.get("chunk_method", "semantic"),
        }
        
        return metadata
    
    @classmethod
    def prepare_metadata_for_pinecone(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for Pinecone (ensure all values are simple types)
        
        Args:
            metadata: Full metadata dict
            
        Returns:
            Pinecone-compatible metadata
        """
        # Pinecone supports: strings, numbers, booleans, lists of strings
        pinecone_metadata = {}
        
        for key, value in metadata.items():
            if value is None:
                continue
            
            # Convert lists to strings if they're not string lists
            if isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    pinecone_metadata[key] = value[:10]  # Limit list length
                else:
                    pinecone_metadata[key] = str(value)
            
            # Convert dicts to JSON strings
            elif isinstance(value, dict):
                # Flatten important dict fields
                if key == "processing":
                    pinecone_metadata["job_id"] = value.get("job_id", "")
                    pinecone_metadata["processor_type"] = value.get("processor_type", "")
            
            # Keep simple types
            elif isinstance(value, (str, int, float, bool)):
                pinecone_metadata[key] = value
            
            # Convert everything else to string
            else:
                pinecone_metadata[key] = str(value)
        
        return pinecone_metadata


# Export
__all__ = ['MetadataEnricher']

