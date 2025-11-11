"""
Language Detector for DMA Bot Data Management System
Detects English, Marathi, Hindi, and bilingual content
"""
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter

from ..core.config import config
from ..utils.logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.language_detector")


class LanguageDetector:
    """Detect language of text content"""
    
    # Unicode ranges for different scripts
    DEVANAGARI_RANGE = (0x0900, 0x097F)  # Marathi/Hindi
    
    # Common English words for validation
    ENGLISH_COMMON_WORDS = {
        'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'of', 'to', 
        'in', 'for', 'with', 'by', 'from', 'as', 'that', 'this', 'are', 'was'
    }
    
    # Common Marathi words (transliterated)
    MARATHI_COMMON_WORDS = {
        'आणि', 'किंवा', 'तर', 'या', 'ला', 'ने', 'च्या', 'मध्ये', 'साठी',
        'करण्यासाठी', 'आहे', 'होते', 'असे', 'काय', 'कोण', 'कसे', 'कुठे'
    }
    
    @classmethod
    def detect_language(cls, text: str, user_hint: Optional[str] = None) -> Dict[str, any]:
        """
        Detect language of text with confidence scores
        
        Args:
            text: Text to analyze
            user_hint: Optional user-provided language hint
            
        Returns:
            Dict with language, confidence, is_bilingual, and details
        """
        if not text or len(text.strip()) == 0:
            return {
                "language": "unknown",
                "confidence": 0.0,
                "is_bilingual": False,
                "languages_detected": [],
                "details": "Empty text"
            }
        
        # If user provided hint, trust it with lower threshold validation
        if user_hint and user_hint != "auto-detect":
            validation = cls._validate_user_hint(text, user_hint)
            if validation["valid"]:
                return {
                    "language": user_hint,
                    "confidence": validation["confidence"],
                    "is_bilingual": user_hint == "bilingual",
                    "languages_detected": cls._detect_scripts(text),
                    "details": "User-provided with validation"
                }
        
        # Automatic detection
        scripts = cls._detect_scripts(text)
        
        # Analyze script distribution
        has_english = "english" in scripts
        has_devanagari = "devanagari" in scripts
        
        # Bilingual detection
        if has_english and has_devanagari:
            en_ratio = scripts.get("english", 0)
            dv_ratio = scripts.get("devanagari", 0)
            
            # If both scripts have significant presence (>20%), it's bilingual
            if en_ratio > 0.2 and dv_ratio > 0.2:
                return {
                    "language": "bilingual",
                    "confidence": 0.9,
                    "is_bilingual": True,
                    "languages_detected": ["en", "mr"],
                    "details": f"English {en_ratio:.1%}, Devanagari {dv_ratio:.1%}"
                }
        
        # Single language detection
        if has_devanagari and scripts["devanagari"] > 0.5:
            return {
                "language": "mr",  # Marathi (could also be Hindi)
                "confidence": scripts["devanagari"],
                "is_bilingual": False,
                "languages_detected": ["mr"],
                "details": f"Devanagari script {scripts['devanagari']:.1%}"
            }
        
        if has_english:
            return {
                "language": "en",
                "confidence": scripts.get("english", 0.7),
                "is_bilingual": False,
                "languages_detected": ["en"],
                "details": f"English {scripts.get('english', 0.7):.1%}"
            }
        
        # Unknown
        return {
            "language": "unknown",
            "confidence": 0.3,
            "is_bilingual": False,
            "languages_detected": [],
            "details": "Could not determine language"
        }
    
    @classmethod
    def detect_chunk_language(cls, text: str, overall_language: str) -> str:
        """
        Detect language of a specific chunk within a document
        
        Args:
            text: Chunk text
            overall_language: Overall document language
            
        Returns:
            Language code (en, mr, or bilingual)
        """
        # For bilingual documents, check if this specific chunk is bilingual
        if overall_language == "bilingual":
            scripts = cls._detect_scripts(text)
            has_english = scripts.get("english", 0) > 0.1
            has_devanagari = scripts.get("devanagari", 0) > 0.1
            
            if has_english and has_devanagari:
                return "bilingual"
            elif has_devanagari:
                return "mr"
            elif has_english:
                return "en"
        
        # For single-language documents, inherit the document language
        return overall_language
    
    @classmethod
    def split_bilingual_content(cls, text: str) -> Tuple[str, str]:
        """
        Attempt to split bilingual text into English and Marathi parts
        
        Args:
            text: Bilingual text
            
        Returns:
            Tuple of (english_text, marathi_text)
        """
        lines = text.split('\n')
        english_lines = []
        marathi_lines = []
        
        for line in lines:
            scripts = cls._detect_scripts(line)
            
            if scripts.get("devanagari", 0) > scripts.get("english", 0):
                marathi_lines.append(line)
            else:
                english_lines.append(line)
        
        english_text = '\n'.join(english_lines).strip()
        marathi_text = '\n'.join(marathi_lines).strip()
        
        return english_text, marathi_text
    
    @classmethod
    def _detect_scripts(cls, text: str) -> Dict[str, float]:
        """
        Detect character scripts and their ratios
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with script names and their ratios
        """
        if not text:
            return {}
        
        total_chars = len(text)
        devanagari_count = 0
        latin_count = 0
        
        for char in text:
            code_point = ord(char)
            
            # Check Devanagari
            if cls.DEVANAGARI_RANGE[0] <= code_point <= cls.DEVANAGARI_RANGE[1]:
                devanagari_count += 1
            # Check Latin (English)
            elif (65 <= code_point <= 90) or (97 <= code_point <= 122):
                latin_count += 1
        
        scripts = {}
        
        if latin_count > 0:
            scripts["english"] = latin_count / total_chars
        
        if devanagari_count > 0:
            scripts["devanagari"] = devanagari_count / total_chars
        
        return scripts
    
    @classmethod
    def _validate_user_hint(cls, text: str, hint: str) -> Dict[str, any]:
        """
        Validate user's language hint against actual content
        
        Args:
            text: Text to check
            hint: User's language hint
            
        Returns:
            Dict with validation result
        """
        scripts = cls._detect_scripts(text)
        
        if hint == "en":
            en_ratio = scripts.get("english", 0)
            return {
                "valid": en_ratio > 0.3,
                "confidence": en_ratio
            }
        
        elif hint == "mr":
            dv_ratio = scripts.get("devanagari", 0)
            return {
                "valid": dv_ratio > 0.3,
                "confidence": dv_ratio
            }
        
        elif hint == "bilingual":
            has_both = (scripts.get("english", 0) > 0.1 and 
                       scripts.get("devanagari", 0) > 0.1)
            return {
                "valid": has_both,
                "confidence": 0.9 if has_both else 0.5
            }
        
        return {"valid": True, "confidence": 0.5}
    
    @classmethod
    def is_mostly_english(cls, text: str) -> bool:
        """Quick check if text is mostly English"""
        scripts = cls._detect_scripts(text)
        return scripts.get("english", 0) > 0.6
    
    @classmethod
    def is_mostly_marathi(cls, text: str) -> bool:
        """Quick check if text is mostly Marathi"""
        scripts = cls._detect_scripts(text)
        return scripts.get("devanagari", 0) > 0.6


# Export
__all__ = ['LanguageDetector']

