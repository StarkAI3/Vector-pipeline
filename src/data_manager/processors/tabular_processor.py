"""
Tabular Processor
Processes table-like data (array of objects from JSON/CSV/Excel)
"""
from typing import Dict, Any, List
import json

from .base_processor import BaseProcessor, ProcessingResult, Chunk
from ..utils.logger import get_logger

logger = get_logger('processor.tabular')


class TabularProcessor(BaseProcessor):
    """
    Processes tabular data where each row/object becomes a searchable chunk.
    Ideal for:
    - JSON array of objects
    - CSV/Excel rows
    - Data tables
    """
    
    def __init__(self):
        super().__init__()
        self.supported_structures = [
            "array_of_objects",
            "single_object",
            "api_response",
            # PDF structures (Phase 4)
            "mostly_tables",
            "standard_table"  # Also from Excel/CSV
        ]
    
    def get_supported_structures(self) -> List[str]:
        """Return supported structure types"""
        return self.supported_structures
    
    def can_process(self, content: Any, structure: str) -> bool:
        """Check if can process this content"""
        if structure in self.supported_structures:
            return True
        
        # Check for PDF table content (Phase 4)
        if isinstance(content, dict):
            # PDF content with tables
            if 'tables' in content or 'all_tables' in content:
                return True
            # Regular dict content
            return True
        
        # Also check if content is a list of dicts
        if isinstance(content, list) and len(content) > 0:
            return isinstance(content[0], dict)
        
        return False
    
    def process(
        self,
        content: Any,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process tabular content into chunks.
        
        Args:
            content: List of dictionaries or single dictionary
            metadata: Processing metadata (category, language, etc.)
            **kwargs: Optional parameters:
                - source_id: Source document ID
                - create_variants: Create search variants (default True)
                - chunk_size: Target chunk size
        
        Returns:
            ProcessingResult with chunks
        """
        result = ProcessingResult()
        
        # Handle PDF table content (Phase 4)
        if isinstance(content, dict) and 'tables' in content:
            # Extract tables from PDF content
            tables = content.get('tables', [])
            if not tables:
                tables = content.get('all_tables', [])
            
            # Convert PDF tables to list of dicts
            content_list = []
            for table in tables:
                if isinstance(table, dict) and 'data' in table:
                    # Table has 'data' field with list of row dicts
                    content_list.extend(table['data'])
                elif isinstance(table, dict) and 'rows' in table:
                    # Table has 'rows' field - convert to dicts
                    headers = table.get('headers', [])
                    rows = table.get('rows', [])
                    for row in rows:
                        row_dict = {}
                        for i, cell in enumerate(row):
                            header = headers[i] if i < len(headers) else f"Column_{i+1}"
                            row_dict[header] = cell
                        content_list.append(row_dict)
            
            content = content_list
            self._log_processing_start("tabular", len(content))
        else:
            self._log_processing_start("tabular", len(content) if isinstance(content, list) else 1)
        
        # Normalize to list
        if isinstance(content, dict):
            content = [content]
        
        if not isinstance(content, list):
            return self._create_error_result("Content must be list or dict")
        
        # Get parameters
        source_id = kwargs.get('source_id', metadata.get('source_id', 'unknown'))
        create_variants = kwargs.get('create_variants', True)
        user_language = metadata.get('language', 'en')
        category = metadata.get('category', 'general_information')
        
        # Process each item
        chunk_counter = 0
        for idx, item in enumerate(content):
            if not isinstance(item, dict):
                result.add_warning(f"Item {idx} is not a dictionary, skipping")
                continue
            
            try:
                # Create primary chunk
                primary_chunk = self._create_primary_chunk(
                    item=item,
                    source_id=source_id,
                    chunk_index=chunk_counter,
                    source_index=idx,
                    metadata=metadata,
                    language=user_language
                )
                
                if primary_chunk:
                    # Validate quality
                    is_valid, reason = self._validate_chunk(primary_chunk)
                    if not is_valid:
                        result.reject_chunk(f"Item {idx}: {reason}")
                        continue
                    
                    # Check quality score
                    quality_score, is_acceptable = self._validate_chunk_quality(
                        primary_chunk.text,
                        primary_chunk.language
                    )
                    primary_chunk.quality_score = quality_score
                    
                    if not is_acceptable:
                        result.reject_chunk(f"Item {idx}: Low quality score ({quality_score:.2f})")
                        continue
                    
                    # Enrich metadata
                    primary_chunk = self._enrich_with_metadata(
                        primary_chunk,
                        metadata,
                        category=category,
                        item_type="tabular_row"
                    )
                    
                    result.add_chunk(primary_chunk)
                    chunk_counter += 1
                    
                    # Create variants if requested
                    if create_variants:
                        variant_chunks = self._create_variant_chunks(
                            item=item,
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
                error_msg = f"Error processing item {idx}: {str(e)}"
                self.logger.error(error_msg)
                result.add_error(error_msg)
        
        # Add processing statistics
        result.processing_stats = {
            "total_items": len(content),
            "processing_method": "tabular",
            "variants_created": create_variants
        }
        
        self._log_processing_complete(result)
        return result
    
    def _create_primary_chunk(
        self,
        item: Dict[str, Any],
        source_id: str,
        chunk_index: int,
        source_index: int,
        metadata: Dict[str, Any],
        language: str
    ) -> Chunk:
        """
        Create primary chunk from tabular item.
        Converts dictionary to natural language text.
        """
        # Convert dict to readable text
        text_parts = []
        
        for key, value in item.items():
            # Skip internal keys
            if key.startswith('_'):
                continue
            
            # Format key (convert snake_case to Title Case)
            formatted_key = key.replace('_', ' ').title()
            
            # Format value
            if value is not None:
                if isinstance(value, (list, dict)):
                    formatted_value = json.dumps(value, ensure_ascii=False)
                else:
                    formatted_value = str(value)
                
                text_parts.append(f"{formatted_key}: {formatted_value}")
        
        # Join into natural text
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
            metadata={"raw_data": item},  # Store raw data in metadata
            language=language,
            source_index=source_index,
            chunk_index=chunk_index
        )
        
        return chunk
    
    def _create_variant_chunks(
        self,
        item: Dict[str, Any],
        source_id: str,
        base_chunk_index: int,
        source_index: int,
        metadata: Dict[str, Any],
        language: str
    ) -> List[Chunk]:
        """
        Create variant chunks for better searchability.
        For example: question-style, name-focused, etc.
        """
        variants = []
        
        # Check if item has name field (for directory-style data)
        name_fields = ['name', 'title', 'service_name', 'officer_name']
        name_value = None
        name_key = None
        
        for field in name_fields:
            if field in item:
                name_value = item[field]
                name_key = field
                break
        
        if name_value:
            # Create name-focused variant
            variant_text = f"Information about {name_value}:\n"
            for key, value in item.items():
                if key != name_key and not key.startswith('_'):
                    formatted_key = key.replace('_', ' ').title()
                    variant_text += f"{formatted_key}: {value}\n"
            
            chunk_id = self._create_chunk_id(
                source_id=source_id,
                chunk_index=base_chunk_index,
                text=variant_text,
                language=language
            )
            
            variant_chunk = self._create_chunk(
                text=variant_text.strip(),
                chunk_id=chunk_id + "_variant",
                metadata={"variant_type": "name_focused", "raw_data": item},
                language=language,
                source_index=source_index,
                chunk_index=base_chunk_index
            )
            
            variants.append(variant_chunk)
        
        return variants
    
    def process_with_schema(
        self,
        content: List[Dict[str, Any]],
        schema: Dict[str, str],
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process tabular data with a defined schema.
        Schema maps field names to their descriptions/types.
        
        Args:
            content: List of dictionaries
            schema: Dictionary mapping field names to descriptions
            metadata: Processing metadata
            **kwargs: Additional parameters
        
        Returns:
            ProcessingResult
        """
        # Add schema to metadata
        metadata['schema'] = schema
        
        # Process normally
        return self.process(content, metadata, **kwargs)

