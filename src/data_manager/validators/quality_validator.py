"""
Quality Validator for DMA Bot Data Management System
Validates chunk quality before embedding and storage
"""
import re
from typing import Dict, List, Tuple

from ..core.config import config
from ..utils.logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.quality_validator")


class QualityValidator:
    """Validate chunk quality and content usefulness"""
    
    # Patterns for low-quality content
    NOISE_PATTERNS = [
        r'^[\s\-_=\*#]+$',  # Only special characters
        r'^page\s+\d+$',     # Just "Page 1"
        r'^\d+$',            # Just numbers
        r'^[^\w\s]+$',       # No alphanumeric characters
    ]
    
    # Compiled patterns
    NOISE_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in NOISE_PATTERNS]
    
    @classmethod
    def validate_chunk(cls, chunk_text: str, metadata: Dict = None) -> Tuple[bool, float, str]:
        """
        Validate chunk quality comprehensively
        
        Args:
            chunk_text: Chunk text to validate
            metadata: Optional metadata for context
            
        Returns:
            Tuple of (is_valid, quality_score, reason)
        """
        if not chunk_text or not chunk_text.strip():
            return False, 0.0, "Empty chunk"
        
        # Run all validation checks
        checks = [
            cls._check_length(chunk_text),
            cls._check_noise(chunk_text),
            cls._check_content_quality(chunk_text),
            cls._check_informativeness(chunk_text),
            cls._check_language_coherence(chunk_text)
        ]
        
        # Calculate overall quality score (average of all checks)
        scores = [score for _, score, _ in checks]
        overall_score = sum(scores) / len(scores)
        
        # Determine if valid (must pass threshold)
        is_valid = overall_score >= config.MIN_QUALITY_SCORE
        
        # Get reasons for failed checks
        failed_checks = [reason for valid, _, reason in checks if not valid]
        reason = "; ".join(failed_checks) if failed_checks else "Passed quality checks"
        
        if not is_valid:
            logger.debug(f"Chunk failed quality check (score: {overall_score:.2f}): {reason}")
        
        return is_valid, round(overall_score, 2), reason
    
    @classmethod
    def _check_length(cls, text: str) -> Tuple[bool, float, str]:
        """Check if chunk has appropriate length"""
        token_count = len(text.split())
        
        if token_count < config.MIN_CHUNK_SIZE:
            return False, 0.3, f"Too short ({token_count} tokens)"
        
        if token_count > config.MAX_CHUNK_SIZE:
            return False, 0.5, f"Too long ({token_count} tokens)"
        
        # Ideal length gets higher score
        if config.MIN_CHUNK_SIZE <= token_count <= config.MAX_CHUNK_SIZE:
            # Score based on how close to ideal (512 tokens)
            ideal = 512
            distance = abs(token_count - ideal) / ideal
            score = max(0.7, 1.0 - distance)
            return True, score, "Length OK"
        
        return True, 0.8, "Length acceptable"
    
    @classmethod
    def _check_noise(cls, text: str) -> Tuple[bool, float, str]:
        """Check for noisy/garbage content"""
        text = text.strip()
        
        # Check against noise patterns
        for pattern in cls.NOISE_REGEX:
            if pattern.match(text):
                return False, 0.0, "Matches noise pattern"
        
        # Check ratio of alphanumeric to total characters
        alnum_count = sum(c.isalnum() or c.isspace() for c in text)
        total_count = len(text)
        
        if total_count > 0:
            alnum_ratio = alnum_count / total_count
            if alnum_ratio < 0.5:
                return False, 0.3, "Too many special characters"
        
        # Check for excessive repetition
        words = text.lower().split()
        if len(words) > 5:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                return False, 0.4, "Excessive word repetition"
        
        return True, 1.0, "No noise detected"
    
    @classmethod
    def _check_content_quality(cls, text: str) -> Tuple[bool, float, str]:
        """Check overall content quality"""
        words = text.split()
        
        if not words:
            return False, 0.0, "No words"
        
        # Check average word length (too short = low quality)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        if avg_word_length < 2:
            return False, 0.3, "Words too short"
        
        # Check for minimum meaningful content
        # At least 3 words that are longer than 3 characters
        meaningful_words = [w for w in words if len(w) > 3]
        
        if len(meaningful_words) < 3:
            return False, 0.4, "Not enough meaningful content"
        
        # Quality score based on content richness
        score = min(1.0, len(meaningful_words) / max(len(words) * 0.3, 1))
        
        return True, max(0.7, score), "Content quality acceptable"
    
    @classmethod
    def _check_informativeness(cls, text: str) -> Tuple[bool, float, str]:
        """Check if chunk contains useful information"""
        text_lower = text.lower()
        
        # Check for informative indicators
        informative_indicators = [
            'how', 'what', 'when', 'where', 'why', 'who',
            'apply', 'contact', 'email', 'phone', 'address',
            'form', 'document', 'service', 'office', 'department',
            '@', 'http', '.com', '.gov', '.in',
            # Marathi indicators
            'कसे', 'काय', 'कोण', 'कुठे', 'का', 'कधी',
            'अर्ज', 'संपर्क', 'कार्यालय', 'विभाग'
        ]
        
        indicator_count = sum(1 for indicator in informative_indicators 
                            if indicator in text_lower)
        
        # Check for numbers (often indicates specific information)
        has_numbers = any(char.isdigit() for char in text)
        
        # Check for proper nouns (capitalized words, often important)
        words = text.split()
        capitalized_count = sum(1 for word in words 
                               if word and word[0].isupper() and len(word) > 1)
        
        # Calculate informativeness score
        score = 0.5  # Base score
        
        if indicator_count > 0:
            score += min(0.3, indicator_count * 0.1)
        
        if has_numbers:
            score += 0.1
        
        if capitalized_count > 2:
            score += 0.1
        
        score = min(1.0, score)
        
        is_valid = score >= 0.5
        reason = "Informative content" if is_valid else "Low informativeness"
        
        return is_valid, score, reason
    
    @classmethod
    def _check_language_coherence(cls, text: str) -> Tuple[bool, float, str]:
        """Check if text appears linguistically coherent"""
        words = text.split()
        
        if len(words) < 3:
            return True, 0.7, "Too short to assess coherence"
        
        # Check for common sentence structures
        has_sentence_endings = any(char in text for char in '.!?।')
        
        # Check word length distribution (too uniform = suspicious)
        if len(words) > 5:
            word_lengths = [len(word) for word in words]
            avg_length = sum(word_lengths) / len(word_lengths)
            variance = sum((l - avg_length) ** 2 for l in word_lengths) / len(word_lengths)
            
            # Good text has some variance in word lengths
            if variance < 1:
                return False, 0.5, "Suspicious uniformity"
        
        # Check for common stop words (indicates natural language)
        stop_words = {
            'the', 'is', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for',
            'आणि', 'आहे', 'ला', 'ने', 'या', 'मध्ये'
        }
        
        words_lower = [w.lower() for w in words]
        stop_word_count = sum(1 for w in words_lower if w in stop_words)
        stop_word_ratio = stop_word_count / len(words) if words else 0
        
        # Natural text typically has 20-40% stop words
        if stop_word_ratio > 0.1:
            score = 0.9
            reason = "Coherent language"
        else:
            score = 0.7
            reason = "Acceptable coherence"
        
        return True, score, reason
    
    @classmethod
    def batch_validate(cls, chunks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a batch of chunks
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            
        Returns:
            Tuple of (valid_chunks, invalid_chunks)
        """
        valid_chunks = []
        invalid_chunks = []
        
        for chunk in chunks:
            is_valid, score, reason = cls.validate_chunk(
                chunk.get('text', ''),
                chunk.get('metadata')
            )
            
            chunk['quality_score'] = score
            chunk['quality_reason'] = reason
            
            if is_valid:
                valid_chunks.append(chunk)
            else:
                invalid_chunks.append(chunk)
        
        logger.info(f"Validated {len(chunks)} chunks: "
                   f"{len(valid_chunks)} valid, {len(invalid_chunks)} rejected")
        
        return valid_chunks, invalid_chunks
    
    @classmethod
    def quick_validate(cls, text: str) -> bool:
        """
        Quick validation check (faster, less thorough)
        
        Args:
            text: Text to check
            
        Returns:
            True if likely valid
        """
        if not text or len(text.strip()) < 20:
            return False
        
        # Quick noise check
        for pattern in cls.NOISE_REGEX:
            if pattern.match(text.strip()):
                return False
        
        # Quick word count check
        word_count = len(text.split())
        if word_count < 5:
            return False
        
        return True


# Export
__all__ = ['QualityValidator']

