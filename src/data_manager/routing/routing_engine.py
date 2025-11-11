"""
Routing Engine
Routes extracted content to appropriate processor based on structure and user selections
"""
from typing import Dict, Any, Optional
from pathlib import Path

from ..processors.base_processor import BaseProcessor, ProcessingResult
from ..processors.tabular_processor import TabularProcessor
from ..processors.directory_processor import DirectoryProcessor
from ..processors.web_content_processor import WebContentProcessor
from ..processors.universal_processor import UniversalProcessor
from ..utils.logger import get_logger

logger = get_logger('routing_engine')


class RoutingEngine:
    """
    Routes content to the appropriate processor based on:
    1. User-provided content structure
    2. Detected structure from extraction
    3. Content characteristics
    """
    
    def __init__(self):
        self.logger = get_logger('routing_engine')
        
        # Initialize all available processors
        self._processors = {
            'tabular': TabularProcessor(),
            'directory': DirectoryProcessor(),
            'web_content': WebContentProcessor(),
            'universal': UniversalProcessor()  # Fallback
        }
        
        # Mapping of structure types to processors
        self._structure_to_processor = {
            # Tabular structures
            'array_of_objects': 'tabular',
            'single_object': 'tabular',
            'api_response': 'tabular',
            'standard_table': 'tabular',
            
            # Directory structures
            'directory_format': 'directory',
            'directory_list': 'directory',
            
            # Web content structures
            'web_scraping_output': 'web_content',
            'article': 'web_content',
            'web_content': 'web_content',
            
            # Fallback
            'unknown': 'universal',
            'mixed_content': 'universal'
        }
        
        self.logger.info(f"Initialized routing engine with {len(self._processors)} processors")
    
    def route(
        self,
        content: Any,
        structure: str,
        metadata: Dict[str, Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Route content to appropriate processor and execute processing.
        
        Args:
            content: Extracted content to process
            structure: Content structure type
            metadata: Processing metadata
            **kwargs: Additional parameters for processing
        
        Returns:
            ProcessingResult from the selected processor
        """
        self.logger.info(f"Routing content with structure: {structure}")
        
        # Select appropriate processor
        processor = self._select_processor(content, structure, metadata)
        
        if not processor:
            self.logger.error(f"No processor found for structure: {structure}")
            # Use universal processor as fallback
            processor = self._processors['universal']
        
        processor_name = processor.__class__.__name__
        self.logger.info(f"Selected processor: {processor_name}")
        
        # Execute processing
        try:
            result = processor.process(content, metadata, **kwargs)
            
            if result.success:
                self.logger.info(
                    f"Processing successful: {result.valid_chunks} chunks created "
                    f"by {processor_name}"
                )
            else:
                self.logger.error(
                    f"Processing failed in {processor_name}: "
                    f"{', '.join(result.errors)}"
                )
            
            # Add routing info to result
            result.processing_stats['processor_used'] = processor_name
            result.processing_stats['routed_structure'] = structure
            
            return result
            
        except Exception as e:
            error_msg = f"Error during processing with {processor_name}: {str(e)}"
            self.logger.error(error_msg)
            
            from ..processors.base_processor import ProcessingResult
            error_result = ProcessingResult(success=False)
            error_result.add_error(error_msg)
            return error_result
    
    def _select_processor(
        self,
        content: Any,
        structure: str,
        metadata: Dict[str, Any]
    ) -> Optional[BaseProcessor]:
        """
        Select the most appropriate processor for the content.
        
        Priority:
        1. User-specified processor (if provided in metadata)
        2. Structure-based routing
        3. Content analysis
        4. Universal fallback
        """
        # Check for user-specified processor
        user_processor = metadata.get('preferred_processor')
        if user_processor and user_processor in self._processors:
            self.logger.info(f"Using user-specified processor: {user_processor}")
            return self._processors[user_processor]
        
        # Check for category hints that suggest directory
        category = metadata.get('category', '')
        if category in ['government_officials', 'contact_information']:
            # Check if directory processor can handle it
            dir_processor = self._processors['directory']
            if dir_processor.can_process(content, structure):
                self.logger.info("Selected directory processor based on category")
                return dir_processor
        
        # Structure-based routing
        processor_key = self._structure_to_processor.get(structure)
        if processor_key:
            processor = self._processors.get(processor_key)
            if processor and processor.can_process(content, structure):
                self.logger.info(f"Selected {processor_key} processor based on structure")
                return processor
        
        # Try each processor's can_process method
        for proc_key, processor in self._processors.items():
            if proc_key == 'universal':
                continue  # Skip universal for now
            
            if processor.can_process(content, structure):
                self.logger.info(f"Selected {proc_key} processor from content analysis")
                return processor
        
        # Fallback to universal
        self.logger.info("Using universal processor as fallback")
        return self._processors['universal']
    
    def get_available_processors(self) -> list[str]:
        """Get list of available processor names"""
        return list(self._processors.keys())
    
    def get_processor_for_structure(self, structure: str) -> Optional[str]:
        """Get recommended processor name for a structure type"""
        return self._structure_to_processor.get(structure)
    
    def validate_routing(
        self,
        content: Any,
        structure: str,
        metadata: Dict[str, Any]
    ) -> tuple[bool, str, Optional[str]]:
        """
        Validate that content can be routed and processed.
        
        Args:
            content: Content to validate
            structure: Structure type
            metadata: Metadata
        
        Returns:
            Tuple of (is_valid, processor_name, error_message)
        """
        try:
            processor = self._select_processor(content, structure, metadata)
            
            if not processor:
                return False, "unknown", "No suitable processor found"
            
            processor_name = processor.__class__.__name__
            
            if not processor.can_process(content, structure):
                return False, processor_name, f"{processor_name} cannot process this content"
            
            return True, processor_name, None
            
        except Exception as e:
            return False, "unknown", f"Validation error: {str(e)}"


# Singleton instance
_routing_engine_instance = None

def get_routing_engine() -> RoutingEngine:
    """Get singleton instance of RoutingEngine"""
    global _routing_engine_instance
    if _routing_engine_instance is None:
        _routing_engine_instance = RoutingEngine()
    return _routing_engine_instance

