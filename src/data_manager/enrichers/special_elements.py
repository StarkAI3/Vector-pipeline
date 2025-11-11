"""
Special Elements Extractor for DMA Bot Data Management System
Extracts URLs, phone numbers, emails, and other special elements from text
"""
import re
from typing import Dict, List, Set
from urllib.parse import urlparse

from ..core.config import config
from ..utils.logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.special_elements")


class SpecialElementsExtractor:
    """Extract special elements from text content"""
    
    # Compiled regex patterns for efficiency
    URL_REGEX = re.compile(config.URL_PATTERN)
    EMAIL_REGEX = re.compile(config.EMAIL_PATTERN)
    PHONE_REGEX = re.compile(config.PHONE_PATTERN)
    
    # Date patterns (various formats)
    DATE_PATTERNS = [
        r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD/MM/YYYY or MM/DD/YYYY
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',    # YYYY/MM/DD
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',  # DD Month YYYY
    ]
    DATE_REGEX = re.compile('|'.join(DATE_PATTERNS), re.IGNORECASE)
    
    @classmethod
    def extract_all(cls, text: str) -> Dict[str, List[str]]:
        """
        Extract all special elements from text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with lists of extracted elements
        """
        if not text:
            return {
                "urls": [],
                "emails": [],
                "phone_numbers": [],
                "dates": []
            }
        
        elements = {
            "urls": cls.extract_urls(text),
            "emails": cls.extract_emails(text),
            "phone_numbers": cls.extract_phone_numbers(text),
            "dates": cls.extract_dates(text)
        }
        
        # Log summary
        total = sum(len(v) for v in elements.values())
        if total > 0:
            logger.debug(f"Extracted {total} special elements: "
                        f"{len(elements['urls'])} URLs, "
                        f"{len(elements['emails'])} emails, "
                        f"{len(elements['phone_numbers'])} phones, "
                        f"{len(elements['dates'])} dates")
        
        return elements
    
    @classmethod
    def extract_urls(cls, text: str) -> List[str]:
        """
        Extract URLs from text
        
        Args:
            text: Text to search
            
        Returns:
            List of unique URLs
        """
        if not text:
            return []
        
        urls = cls.URL_REGEX.findall(text)
        
        # Validate and clean URLs
        valid_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    valid_urls.append(url)
            except:
                continue
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(valid_urls))
    
    @classmethod
    def extract_emails(cls, text: str) -> List[str]:
        """
        Extract email addresses from text
        
        Args:
            text: Text to search
            
        Returns:
            List of unique emails
        """
        if not text:
            return []
        
        emails = cls.EMAIL_REGEX.findall(text)
        
        # Validate emails (basic check)
        valid_emails = []
        for email in emails:
            email = email.lower().strip()
            # Check for common invalid patterns
            if '@' in email and '.' in email.split('@')[1]:
                valid_emails.append(email)
        
        # Remove duplicates
        return list(dict.fromkeys(valid_emails))
    
    @classmethod
    def extract_phone_numbers(cls, text: str) -> List[str]:
        """
        Extract phone numbers from text
        
        Args:
            text: Text to search
            
        Returns:
            List of unique phone numbers
        """
        if not text:
            return []
        
        phones = cls.PHONE_REGEX.findall(text)
        
        # Clean and format phone numbers
        cleaned_phones = []
        for phone in phones:
            # If it's a tuple (from regex groups), join it
            if isinstance(phone, tuple):
                phone = ''.join(str(p) for p in phone if p)
            
            # Remove extra characters
            phone = re.sub(r'[^\d+]', '', str(phone))
            
            # Validate length (should be at least 10 digits)
            digits_only = re.sub(r'[^\d]', '', phone)
            if len(digits_only) >= 10:
                cleaned_phones.append(phone)
        
        # Remove duplicates
        return list(dict.fromkeys(cleaned_phones))
    
    @classmethod
    def extract_dates(cls, text: str) -> List[str]:
        """
        Extract dates from text
        
        Args:
            text: Text to search
            
        Returns:
            List of unique dates
        """
        if not text:
            return []
        
        dates = cls.DATE_REGEX.findall(text)
        
        # Remove duplicates
        return list(dict.fromkeys(dates))
    
    @classmethod
    def has_contact_info(cls, text: str) -> bool:
        """
        Quick check if text contains any contact information
        
        Args:
            text: Text to check
            
        Returns:
            True if contact info found
        """
        if not text:
            return False
        
        return (bool(cls.EMAIL_REGEX.search(text)) or 
                bool(cls.PHONE_REGEX.search(text)))
    
    @classmethod
    def extract_postal_addresses(cls, text: str) -> List[str]:
        """
        Attempt to extract postal addresses (basic pattern matching)
        
        Args:
            text: Text to search
            
        Returns:
            List of potential addresses
        """
        if not text:
            return []
        
        # Look for address-like patterns (very basic)
        # This is difficult without ML, so we look for common indicators
        address_indicators = [
            r'(?i)address[:\s]+([^\n]+)',
            r'(?i)office[:\s]+([^\n]+)',
            r'(?i)located at[:\s]+([^\n]+)',
            r'पत्ता[:\s]+([^\n]+)',  # Marathi for "address"
        ]
        
        addresses = []
        for pattern in address_indicators:
            matches = re.findall(pattern, text)
            addresses.extend(matches)
        
        # Clean and limit
        cleaned = [addr.strip() for addr in addresses if len(addr.strip()) > 10]
        
        return list(dict.fromkeys(cleaned))[:5]  # Limit to 5
    
    @classmethod
    def create_searchable_variants(cls, elements: Dict[str, List[str]]) -> List[str]:
        """
        Create searchable text variants from special elements
        Useful for enhancing chunk searchability
        
        Args:
            elements: Dict of extracted elements
            
        Returns:
            List of searchable strings
        """
        variants = []
        
        # Email variants
        for email in elements.get("emails", []):
            variants.append(f"Email: {email}")
            variants.append(f"Contact: {email}")
            # Add domain for organization search
            if '@' in email:
                domain = email.split('@')[1]
                variants.append(f"Organization: {domain}")
        
        # Phone variants
        for phone in elements.get("phone_numbers", []):
            variants.append(f"Phone: {phone}")
            variants.append(f"Contact: {phone}")
            variants.append(f"Tel: {phone}")
        
        # URL variants
        for url in elements.get("urls", []):
            variants.append(f"Website: {url}")
            # Extract domain for searching
            try:
                parsed = urlparse(url)
                if parsed.netloc:
                    variants.append(f"Website: {parsed.netloc}")
            except:
                pass
        
        return variants
    
    @classmethod
    def enhance_chunk_with_elements(cls, chunk_text: str, elements: Dict[str, List[str]]) -> str:
        """
        Enhance chunk text with extracted special elements for better searchability
        
        Args:
            chunk_text: Original chunk text
            elements: Extracted special elements
            
        Returns:
            Enhanced chunk text
        """
        if not any(elements.values()):
            return chunk_text
        
        # Add a special elements section at the end
        enhancement = []
        
        if elements.get("emails"):
            enhancement.append(f"\nContact Emails: {', '.join(elements['emails'])}")
        
        if elements.get("phone_numbers"):
            enhancement.append(f"\nContact Numbers: {', '.join(elements['phone_numbers'])}")
        
        if elements.get("urls"):
            enhancement.append(f"\nRelevant Links: {', '.join(elements['urls'][:3])}")
        
        if enhancement:
            return chunk_text + "\n" + "".join(enhancement)
        
        return chunk_text


# Export
__all__ = ['SpecialElementsExtractor']

