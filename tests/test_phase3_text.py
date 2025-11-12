"""
Integration Tests for Phase 3: Text/Markdown Support
Tests all components and features for text file processing
"""
import pytest
import sys
from pathlib import Path
import json

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_manager.extractors.text_extractor import TextExtractor
from data_manager.processors.text_processor import TextProcessor
from data_manager.processors.faq_document_processor import FAQDocumentProcessor
from data_manager.extractors.file_type_router import get_file_type_router
from data_manager.routing.routing_engine import get_routing_engine
from data_manager.embedding.embedder import get_embedder
from data_manager.utils.id_generator import IDGenerator


# Test data directory
SAMPLE_DATA_DIR = Path(__file__).parent / 'sample_data'


class TestTextExtraction:
    """Test text and markdown file extraction"""
    
    def test_narrative_text_extraction(self):
        """Test extraction of narrative text document"""
        extractor = TextExtractor()
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        
        result = extractor.extract(file_path)
        
        assert result.success, f"Extraction failed: {result.errors}"
        assert result.file_type in ['text', 'markdown']
        assert result.extracted_structure in ['narrative_document', 'mixed_content', 'structured_markdown']
        assert result.content is not None
        assert 'raw_text' in result.content
        assert len(result.content['raw_text']) > 100
    
    def test_markdown_extraction(self):
        """Test extraction of markdown document"""
        extractor = TextExtractor()
        file_path = SAMPLE_DATA_DIR / 'structured_markdown.md'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.file_type == 'markdown'
        assert result.extracted_structure == 'structured_markdown'
        assert 'sections' in result.content
        assert len(result.content['sections']) > 0
    
    def test_faq_text_extraction(self):
        """Test extraction of FAQ text document"""
        extractor = TextExtractor()
        file_path = SAMPLE_DATA_DIR / 'faq_document.txt'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == 'faq_format'
        assert 'faq_pairs' in result.content
        assert len(result.content['faq_pairs']) > 0
        
        # Check FAQ structure
        first_faq = result.content['faq_pairs'][0]
        assert 'question' in first_faq
        assert 'answer' in first_faq
        assert len(first_faq['question']) > 0
        assert len(first_faq['answer']) > 0
    
    def test_directory_text_extraction(self):
        """Test extraction of directory listing text"""
        extractor = TextExtractor()
        file_path = SAMPLE_DATA_DIR / 'directory_listing.txt'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == 'directory_format'
        assert 'directory_entries' in result.content
        assert len(result.content['directory_entries']) > 0
        
        # Check directory entry structure
        first_entry = result.content['directory_entries'][0]
        assert 'name' in first_entry
        assert 'position' in first_entry or 'email' in first_entry
    
    def test_file_validation(self):
        """Test file validation"""
        extractor = TextExtractor()
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        
        is_valid, error = extractor.validate_file(file_path)
        
        assert is_valid
        assert error is None
    
    def test_supported_extensions(self):
        """Test supported extensions"""
        extractor = TextExtractor()
        extensions = extractor.get_supported_extensions()
        
        assert '.txt' in extensions
        assert '.md' in extensions
        assert '.markdown' in extensions


class TestTextProcessing:
    """Test text processing with TextProcessor"""
    
    def test_narrative_processing(self):
        """Test processing of narrative text"""
        extractor = TextExtractor()
        processor = TextProcessor()
        
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        extraction_result = extractor.extract(file_path)
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'narrative_document.txt'
        }
        
        processing_result = processor.process(extraction_result.content, metadata)
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        assert len(processing_result.chunks) > 0
        
        # Check chunk structure
        first_chunk = processing_result.chunks[0]
        assert first_chunk.text is not None
        assert len(first_chunk.text) > 50
        assert 'category' in first_chunk.metadata
    
    def test_markdown_processing(self):
        """Test processing of structured markdown"""
        extractor = TextExtractor()
        processor = TextProcessor()
        
        file_path = SAMPLE_DATA_DIR / 'structured_markdown.md'
        extraction_result = extractor.extract(file_path)
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'structured_markdown.md'
        }
        
        processing_result = processor.process(extraction_result.content, metadata)
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        
        # Check if section metadata is preserved
        section_chunks = [c for c in processing_result.chunks if 'section_title' in c.metadata]
        assert len(section_chunks) > 0
    
    def test_chunk_size_constraints(self):
        """Test that chunks respect size constraints"""
        extractor = TextExtractor()
        processor = TextProcessor()
        
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        extraction_result = extractor.extract(file_path)
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'narrative_document.txt'
        }
        
        processing_result = processor.process(extraction_result.content, metadata)
        
        for chunk in processing_result.chunks:
            token_count = len(chunk.text.split()) * 0.75  # Rough estimate
            assert token_count >= processor.min_chunk_size
            assert token_count <= processor.max_chunk_size * 1.5  # Some flexibility


class TestFAQProcessing:
    """Test FAQ document processing"""
    
    def test_faq_document_processing(self):
        """Test processing of FAQ text document"""
        extractor = TextExtractor()
        processor = FAQDocumentProcessor()
        
        file_path = SAMPLE_DATA_DIR / 'faq_document.txt'
        extraction_result = extractor.extract(file_path)
        
        metadata = {
            'category': 'faq_help',
            'language': 'bilingual',
            'source_file': 'faq_document.txt'
        }
        
        processing_result = processor.process(extraction_result.content, metadata)
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        
        # Check FAQ chunk structure
        faq_chunks = [c for c in processing_result.chunks if c.metadata.get('chunk_type') == 'faq']
        assert len(faq_chunks) > 0
        
        # Check metadata
        first_chunk = processing_result.chunks[0]
        assert 'question' in first_chunk.metadata
        assert 'answer' in first_chunk.metadata
    
    def test_bilingual_faq_processing(self):
        """Test bilingual FAQ creates multiple chunks"""
        extractor = TextExtractor()
        processor = FAQDocumentProcessor()
        
        file_path = SAMPLE_DATA_DIR / 'faq_document.txt'
        extraction_result = extractor.extract(file_path)
        
        metadata = {
            'category': 'faq_help',
            'language': 'bilingual',
            'source_file': 'faq_document.txt'
        }
        
        processing_result = processor.process(extraction_result.content, metadata)
        
        # Bilingual FAQs should create multiple chunks per FAQ
        # (English, Marathi, Combined)
        faq_count = len(extraction_result.content['faq_pairs'])
        assert processing_result.valid_chunks >= faq_count  # At least one chunk per FAQ


class TestFileTypeRouting:
    """Test file type router with text files"""
    
    def test_text_file_routing(self):
        """Test routing of text files"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        
        extractor = router.get_extractor_for_file(file_path)
        
        assert extractor is not None
        assert isinstance(extractor, TextExtractor)
    
    def test_markdown_file_routing(self):
        """Test routing of markdown files"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'structured_markdown.md'
        
        extractor = router.get_extractor_for_file(file_path)
        
        assert extractor is not None
        assert isinstance(extractor, TextExtractor)
    
    def test_text_extraction_via_router(self):
        """Test full extraction through router"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        
        result = router.extract(file_path)
        
        assert result.success
        assert result.content is not None


class TestContentRouting:
    """Test routing engine with text content"""
    
    def test_narrative_routing(self):
        """Test routing of narrative content"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        extraction_result = router.extract(file_path)
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'narrative_document.txt'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        assert 'processor_used' in processing_result.processing_stats
    
    def test_faq_routing(self):
        """Test routing of FAQ content"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        
        file_path = SAMPLE_DATA_DIR / 'faq_document.txt'
        extraction_result = router.extract(file_path)
        
        metadata = {
            'category': 'faq_help',
            'language': 'bilingual',
            'source_file': 'faq_document.txt'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        # Should route to FAQDocumentProcessor
        assert 'FAQDocument' in processing_result.processing_stats.get('processor_used', '')


class TestEmbeddingGeneration:
    """Test embedding generation for text content"""
    
    def test_text_embedding(self):
        """Test embedding generation for text chunks"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        embedder = get_embedder()
        
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        extraction_result = router.extract(file_path)
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'narrative_document.txt'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        # Generate embedding for first chunk
        first_chunk = processing_result.chunks[0]
        embedding = embedder.embed_text(first_chunk.text)
        
        assert embedding is not None
        assert len(embedding) == 768  # multilingual-e5-base dimension
        # Check that embedding contains numeric values (numpy or native Python)
        import numpy as np
        assert all(isinstance(x, (int, float, np.integer, np.floating)) for x in embedding)


class TestDeduplication:
    """Test de-duplication for text content"""
    
    def test_stable_id_generation(self):
        """Test that same content generates same ID"""
        chunk_text = "This is a test chunk for deduplication"
        source_id = "src_test1234567890"
        metadata = {'language': 'en'}
        
        id1 = IDGenerator.generate_chunk_id(source_id, 0, chunk_text, metadata)
        id2 = IDGenerator.generate_chunk_id(source_id, 0, chunk_text, metadata)
        
        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) > 0
    
    def test_different_content_different_ids(self):
        """Test that different content generates different IDs"""
        source_id = "src_test1234567890"
        metadata = {'language': 'en'}
        
        id1 = IDGenerator.generate_chunk_id(source_id, 0, "Content one", metadata)
        id2 = IDGenerator.generate_chunk_id(source_id, 1, "Content two", metadata)
        
        assert id1 != id2


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline for text files"""
    
    def test_complete_text_pipeline(self):
        """Test complete pipeline: extract → route → process → embed"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        embedder = get_embedder()
        
        file_path = SAMPLE_DATA_DIR / 'structured_markdown.md'
        
        # Step 1: Extract
        extraction_result = router.extract(file_path)
        assert extraction_result.success
        
        # Step 2: Route and Process
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'structured_markdown.md'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        
        # Step 3: Generate embeddings
        sample_chunks = processing_result.chunks[:3]  # Test first 3 chunks
        
        for chunk in sample_chunks:
            embedding = embedder.embed_text(chunk.text)
            assert embedding is not None
            assert len(embedding) == 768
            
            # Generate chunk ID (for de-duplication)
            source_id = "src_test1234567890"
            chunk_id = IDGenerator.generate_chunk_id(source_id, 0, chunk.text, chunk.metadata)
            assert chunk_id is not None
        
        print(f"\n✓ Complete pipeline test passed:")
        print(f"  - Extracted: {extraction_result.extracted_structure}")
        print(f"  - Chunks created: {processing_result.valid_chunks}")
        print(f"  - Sample embeddings generated: {len(sample_chunks)}")


def test_phase3_summary():
    """Summary test to verify all Phase 3 components"""
    print("\n" + "="*60)
    print("Phase 3 Test Summary")
    print("="*60)
    
    # Test extractor availability
    router = get_file_type_router()
    supported_types = router.get_supported_types()
    print(f"\n✓ Supported file types: {supported_types}")
    assert 'text' in supported_types
    
    # Test processor availability
    routing_engine = get_routing_engine()
    processors = routing_engine.get_available_processors()
    print(f"✓ Available processors: {processors}")
    assert 'text' in processors
    assert 'faq_document' in processors
    
    # Test sample files
    sample_files = [
        'narrative_document.txt',
        'structured_markdown.md',
        'faq_document.txt',
        'directory_listing.txt'
    ]
    
    print(f"\n✓ Sample test files:")
    for file_name in sample_files:
        file_path = SAMPLE_DATA_DIR / file_name
        assert file_path.exists(), f"Missing test file: {file_name}"
        print(f"  - {file_name}")
    
    print("\n" + "="*60)
    print("Phase 3 Integration: PASSED")
    print("="*60)


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])

