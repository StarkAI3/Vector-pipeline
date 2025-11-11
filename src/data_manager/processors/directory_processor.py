"""
Directory Processor
Specialized processor for contact directories and official listings
"""
from typing import Dict, Any, List
import json

from .base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.directory')


class DirectoryProcessor(BaseProcessor):
    """
    Specialized processor for directory/contact list data.
    Creates multiple chunk variations for better searchability:
    - By name
    - By position/title
    - By department
    - By contact details
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "array_of_objects",  # When it's a directory
            "directory_format"
        ]
        
        # Common field mappings for directories
        self.name_fields = ['name', 'full_name', 'officer_name', 'person_name']
        self.position_fields = ['position', 'designation', 'title', 'role', 'post']
        self.department_fields = ['department', 'division', 'section', 'office']
        self.phone_fields = ['phone', 'mobile', 'contact', 'telephone', 'phone_number']
        self.email_fields = ['email', 'email_address', 'mail']
        self.address_fields = ['address', 'office_address', 'location']
    
    def get_supported_structures(self) -> List[str]:
        """Return supported structure types"""
        return self.supported_structures
    
    def can_process(self, content: Any, structure: str) -> bool:
        """
        Check if content looks like a directory.
        A directory typically has name + position/contact fields.
        """
        if structure in self.supported_structures:
            return True
        
        # Check if content has directory-like fields
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict):
                return self._is_directory_item(first_item)
        
        return False
    
    def _is_directory_item(self, item: Dict[str, Any]) -> bool:
        """Check if item has directory-like structure"""
        has_name = any(field in item for field in self.name_fields)
        has_position = any(field in item for field in self.position_fields)
        has_contact = any(
            field in item 
            for field in self.phone_fields + self.email_fields
        )
        
        return has_name and (has_position or has_contact)
    
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process directory content into searchable chunks.
        Creates multiple search variations per entry.
        
        Args:
            content: List of directory entries
            metadata: Processing metadata
            **kwargs: Optional parameters:
                - source_id: Source document ID
                - create_multiple_variants: Create all search variants (default True)
        
        Returns:
            ProcessingResult with chunks
        """
        self._log_processing_start("directory", len(content) if isinstance(content, list) else 1)
        
        result = ProcessingResult()
        
        # Normalize to list
        if isinstance(content, dict):
            content = [content]
        
        if not isinstance(content, list):
            return self._create_error_result("Content must be list or dict")
        
        # Get parameters
        source_id = kwargs.get('source_id', metadata.get('source_id', 'unknown'))
        create_variants = kwargs.get('create_multiple_variants', True)
        user_language = metadata.get('language', 'en')
        category = metadata.get('category', 'contact_information')
        
        # Process each directory entry
        chunk_counter = 0
        for idx, entry in enumerate(content):
            if not isinstance(entry, dict):
                result.add_warning(f"Entry {idx} is not a dictionary, skipping")
                continue
            
            try:
                # Parse directory entry
                parsed_entry = self._parse_directory_entry(entry)
                
                # Create comprehensive chunk
                comprehensive_chunk = self._create_comprehensive_chunk(
                    entry=parsed_entry,
                    source_id=source_id,
                    chunk_index=chunk_counter,
                    source_index=idx,
                    metadata=metadata,
                    language=user_language
                )
                
                if comprehensive_chunk:
                    # Validate
                    is_valid, reason = self._validate_chunk(comprehensive_chunk)
                    if not is_valid:
                        result.reject_chunk(f"Entry {idx}: {reason}")
                        continue
                    
                    # Quality check
                    quality_score, is_acceptable = self._validate_chunk_quality(
                        comprehensive_chunk.text,
                        comprehensive_chunk.language
                    )
                    comprehensive_chunk.quality_score = quality_score
                    
                    if not is_acceptable:
                        result.reject_chunk(f"Entry {idx}: Low quality ({quality_score:.2f})")
                        continue
                    
                    # Enrich metadata
                    comprehensive_chunk = self._enrich_with_metadata(
                        comprehensive_chunk,
                        metadata,
                        category=category,
                        item_type="directory_entry",
                        entry_name=parsed_entry.get('name')
                    )
                    
                    result.add_chunk(comprehensive_chunk)
                    chunk_counter += 1
                    
                    # Create search variants
                    if create_variants:
                        variant_chunks = self._create_search_variants(
                            entry=parsed_entry,
                            source_id=source_id,
                            base_chunk_index=chunk_counter,
                            source_index=idx,
                            metadata=metadata,
                            language=user_language
                        )
                        
                        for variant in variant_chunks:
                            result.add_chunk(variant)
                            chunk_counter += 1
                
            except Exception as e:
                error_msg = f"Error processing entry {idx}: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Add processing statistics
        result.processing_stats = {
            "total_entries": len(content),
            "processing_method": "directory",
            "variants_created": create_variants
        }
        
        self._log_processing_complete(result)
        return result
    
    def _parse_directory_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse directory entry and extract standard fields.
        """
        parsed = {
            "name": self._extract_field(entry, self.name_fields),
            "position": self._extract_field(entry, self.position_fields),
            "department": self._extract_field(entry, self.department_fields),
            "phone": self._extract_field(entry, self.phone_fields),
            "email": self._extract_field(entry, self.email_fields),
            "address": self._extract_field(entry, self.address_fields),
            "other_fields": {}
        }
        
        # Store remaining fields
        known_fields = set(
            self.name_fields + self.position_fields + 
            self.department_fields + self.phone_fields + 
            self.email_fields + self.address_fields
        )
        
        for key, value in entry.items():
            if key not in known_fields and not key.startswith('_'):
                parsed["other_fields"][key] = value
        
        # Store original
        parsed["_original"] = entry
        
        return parsed
    
    def _extract_field(self, entry: Dict[str, Any], field_options: List[str]) -> str:
        """Extract first matching field from entry"""
        for field in field_options:
            if field in entry and entry[field]:
                return str(entry[field])
        return ""
    
    def _create_comprehensive_chunk(
        self,
        entry: Dict[str, Any],
        source_id: str,
        chunk_index: int,
        source_index: int,
        metadata: Dict[str, Any],
        language: str
    ) -> Chunk:
        """
        Create comprehensive chunk with all directory information.
        """
        text_parts = []
        
        # Name and position (primary info)
        if entry['name']:
            text_parts.append(f"Name: {entry['name']}")
        
        if entry['position']:
            text_parts.append(f"Position: {entry['position']}")
        
        if entry['department']:
            text_parts.append(f"Department: {entry['department']}")
        
        # Contact information
        contact_parts = []
        if entry['phone']:
            contact_parts.append(f"Phone: {entry['phone']}")
        if entry['email']:
            contact_parts.append(f"Email: {entry['email']}")
        if entry['address']:
            contact_parts.append(f"Office: {entry['address']}")
        
        if contact_parts:
            text_parts.extend(contact_parts)
        
        # Other fields
        for key, value in entry['other_fields'].items():
            formatted_key = key.replace('_', ' ').title()
            text_parts.append(f"{formatted_key}: {value}")
        
        # Create chunk text
        chunk_text = "\n".join(text_parts)
        
        # Create chunk ID
        chunk_id = self._create_chunk_id(
            source_id=source_id,
            chunk_index=chunk_index,
            text=chunk_text,
            language=language
        )
        
        # Create chunk
        chunk = self._create_chunk(
            text=chunk_text,
            chunk_id=chunk_id,
            metadata={"directory_entry": entry},
            language=language,
            source_index=source_index,
            chunk_index=chunk_index
        )
        
        return chunk
    
    def _create_search_variants(
        self,
        entry: Dict[str, Any],
        source_id: str,
        base_chunk_index: int,
        source_index: int,
        metadata: Dict[str, Any],
        language: str
    ) -> List[Chunk]:
        """
        Create search variant chunks for different query types.
        """
        variants = []
        
        # Variant 1: Question-style (Who is X?)
        if entry['name']:
            variant_text = f"Who is {entry['name']}?\n"
            if entry['position']:
                variant_text += f"{entry['name']} is the {entry['position']}"
            if entry['department']:
                variant_text += f" in the {entry['department']}"
            variant_text += ".\n"
            
            if entry['phone']:
                variant_text += f"Contact: {entry['phone']}\n"
            if entry['email']:
                variant_text += f"Email: {entry['email']}"
            
            variants.append(self._create_variant_chunk(
                text=variant_text.strip(),
                variant_type="question_style",
                source_id=source_id,
                base_chunk_index=base_chunk_index,
                source_index=source_index,
                entry=entry,
                language=language
            ))
        
        # Variant 2: Position-focused (Who is the X?)
        if entry['position'] and entry['name']:
            variant_text = f"Who is the {entry['position']}?"
            if entry['department']:
                variant_text += f" in the {entry['department']}?"
            variant_text += f"\nThe {entry['position']} is {entry['name']}."
            
            variants.append(self._create_variant_chunk(
                text=variant_text,
                variant_type="position_focused",
                source_id=source_id,
                base_chunk_index=base_chunk_index + 1,
                source_index=source_index,
                entry=entry,
                language=language
            ))
        
        # Variant 3: Contact-focused (How to contact X?)
        if entry['name'] and (entry['phone'] or entry['email']):
            variant_text = f"How to contact {entry['name']}?\n"
            if entry['phone']:
                variant_text += f"Phone: {entry['phone']}\n"
            if entry['email']:
                variant_text += f"Email: {entry['email']}\n"
            if entry['address']:
                variant_text += f"Office: {entry['address']}"
            
            variants.append(self._create_variant_chunk(
                text=variant_text.strip(),
                variant_type="contact_focused",
                source_id=source_id,
                base_chunk_index=base_chunk_index + 2,
                source_index=source_index,
                entry=entry,
                language=language
            ))
        
        return [v for v in variants if v]  # Filter None values
    
    def _create_variant_chunk(
        self,
        text: str,
        variant_type: str,
        source_id: str,
        base_chunk_index: int,
        source_index: int,
        entry: Dict[str, Any],
        language: str
    ) -> Chunk:
        """Create a single variant chunk"""
        chunk_id = self._create_chunk_id(
            source_id=source_id,
            chunk_index=base_chunk_index,
            text=text,
            language=language
        )
        
        return self._create_chunk(
            text=text,
            chunk_id=chunk_id + f"_{variant_type}",
            metadata={"variant_type": variant_type, "directory_entry": entry},
            language=language,
            source_index=source_index,
            chunk_index=base_chunk_index
        )

