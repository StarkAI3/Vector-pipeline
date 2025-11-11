"""
Processors Module
Content processors for creating chunks from extracted content
"""
from .base_processor import BaseProcessor, ProcessingResult, Chunk
from .tabular_processor import TabularProcessor
from .directory_processor import DirectoryProcessor
from .web_content_processor import WebContentProcessor
from .universal_processor import UniversalProcessor

__all__ = [
    'BaseProcessor',
    'ProcessingResult',
    'Chunk',
    'TabularProcessor',
    'DirectoryProcessor',
    'WebContentProcessor',
    'UniversalProcessor'
]

