"""
Integration Tests for Phase 4: PDF Support
Tests all components and features for PDF file processing
"""
import pytest
import sys
from pathlib import Path
import json

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_manager.extractors.pdf_extractor import PDFExtractor
from data_manager.extractors.file_type_router import get_file_type_router
from data_manager.routing.routing_engine import get_routing_engine
from data_manager.embedding.embedder import get_embedder
from data_manager.utils.id_generator import IDGenerator


# Test data directory
SAMPLE_DATA_DIR = Path(__file__).parent / 'sample_data'


class TestPDFExtraction:
    """Test PDF file extraction"""
    
    def test_text_document_extraction(self):
        """Test extraction of pure text PDF document"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path)
        
        assert result.success, f"Extraction failed: {result.errors}"
        assert result.file_type == 'pdf'
        assert result.extracted_structure in ['text_document', 'document_with_tables', 'complex_mix']
        assert result.content is not None
        assert 'raw_text' in result.content
        assert len(result.content['raw_text']) > 100
        assert 'page_count' in result.content
        assert result.content['page_count'] > 0
    
    def test_document_with_tables_extraction(self):
        """Test extraction of PDF with tables"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'document_with_tables.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path, expected_structure='document_with_tables')
        
        assert result.success
        assert result.file_type == 'pdf'
        assert result.extracted_structure in ['document_with_tables', 'mostly_tables', 'complex_mix']
        assert 'tables' in result.content or 'all_tables' in result.content
        assert 'raw_text' in result.content
        assert len(result.content['raw_text']) > 50
    
    def test_mostly_tables_extraction(self):
        """Test extraction of table-heavy PDF"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'mostly_tables.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path, expected_structure='mostly_tables')
        
        assert result.success
        assert result.extracted_structure in ['mostly_tables', 'document_with_tables']
        # Should have tables
        tables = result.content.get('tables', result.content.get('all_tables', []))
        assert len(tables) > 0
    
    def test_faq_document_extraction(self):
        """Test extraction of FAQ PDF document"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'faq_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path, expected_structure='faq_document')
        
        assert result.success
        assert result.extracted_structure in ['faq_document', 'text_document', 'complex_mix']
        # Should detect FAQ patterns
        if 'faq_pairs' in result.content:
            assert len(result.content['faq_pairs']) > 0
    
    def test_form_template_extraction(self):
        """Test extraction of form template PDF"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'form_template.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path, expected_structure='form_template')
        
        assert result.success
        assert result.file_type == 'pdf'
        assert 'raw_text' in result.content
        # Form should have field patterns
        text = result.content['raw_text'].lower()
        assert 'name' in text or 'application' in text or 'form' in text
    
    def test_complex_mix_extraction(self):
        """Test extraction of complex mixed PDF"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'complex_mix.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = extractor.extract(file_path, expected_structure='complex_mix')
        
        assert result.success
        assert result.file_type == 'pdf'
        assert 'raw_text' in result.content
        assert len(result.content['raw_text']) > 100
    
    def test_file_validation(self):
        """Test PDF file validation"""
        extractor = PDFExtractor()
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        is_valid, error = extractor.validate_file(file_path)
        
        assert is_valid
        assert error is None
    
    def test_invalid_file_validation(self):
        """Test validation of invalid file"""
        extractor = PDFExtractor()
        # Use a text file which should fail PDF validation
        file_path = SAMPLE_DATA_DIR / 'narrative_document.txt'
        
        if not file_path.exists():
            pytest.skip("Sample text file not found")
        
        is_valid, error = extractor.validate_file(file_path)
        
        assert not is_valid
        assert error is not None


class TestPDFRouting:
    """Test PDF file routing through file type router"""
    
    def test_pdf_file_type_detection(self):
        """Test PDF file type detection"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        extractor = router.get_extractor_for_file(file_path)
        
        assert extractor is not None
        assert extractor.__class__.__name__ == 'PDFExtractor'
    
    def test_pdf_extraction_via_router(self):
        """Test PDF extraction through router"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        result = router.extract(file_path, file_type='pdf')
        
        assert result.success
        assert result.file_type == 'pdf'
        assert result.content is not None
    
    def test_pdf_is_supported(self):
        """Test that PDF is recognized as supported"""
        router = get_file_type_router()
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        assert router.is_supported(file_path)


class TestPDFProcessing:
    """Test PDF content processing"""
    
    def test_text_document_processing(self):
        """Test processing of text PDF document"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Extract
        extraction_result = router.extract(file_path, file_type='pdf')
        assert extraction_result.success
        
        # Process
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'importance': 'normal'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        assert len(processing_result.chunks) > 0
    
    def test_faq_document_processing(self):
        """Test processing of FAQ PDF document"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        
        file_path = SAMPLE_DATA_DIR / 'faq_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Extract
        extraction_result = router.extract(
            file_path, 
            file_type='pdf',
            expected_structure='faq_document'
        )
        assert extraction_result.success
        
        # Process
        metadata = {
            'category': 'faq_help',
            'language': 'bilingual',
            'importance': 'normal'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0
    
    def test_table_document_processing(self):
        """Test processing of PDF with tables"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        
        file_path = SAMPLE_DATA_DIR / 'document_with_tables.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Extract
        extraction_result = router.extract(
            file_path,
            file_type='pdf',
            expected_structure='document_with_tables'
        )
        assert extraction_result.success
        
        # Process
        metadata = {
            'category': 'contact_information',
            'language': 'en',
            'importance': 'normal'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert processing_result.valid_chunks > 0


class TestPDFEmbedding:
    """Test PDF embedding generation"""
    
    def test_pdf_chunk_embedding(self):
        """Test embedding generation for PDF chunks"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        embedder = get_embedder()
        
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Extract and process
        extraction_result = router.extract(file_path, file_type='pdf')
        assert extraction_result.success
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'importance': 'normal'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        assert processing_result.success
        assert len(processing_result.chunks) > 0
        
        # Generate embeddings
        chunk = processing_result.chunks[0]
        embedding = embedder.embed_text(chunk.text)
        
        assert embedding is not None
        assert len(embedding) == 768  # multilingual-e5-base dimension


class TestPDFDeduplication:
    """Test de-duplication with PDF files"""
    
    def test_pdf_deduplication_same_content(self):
        """Test that uploading same PDF twice creates duplicate detection"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        id_generator = IDGenerator()
        
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Extract and process first time
        extraction_result = router.extract(file_path, file_type='pdf')
        assert extraction_result.success
        
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'importance': 'normal',
            'source_file': 'text_document.pdf'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        assert processing_result.success
        
        # Generate IDs for chunks
        chunk = processing_result.chunks[0]
        chunk_id_1 = id_generator.generate_chunk_id(
            chunk.text,
            metadata,
            chunk_index=0
        )
        
        # Process same content again
        processing_result_2 = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        assert processing_result_2.success
        
        chunk_2 = processing_result_2.chunks[0]
        chunk_id_2 = id_generator.generate_chunk_id(
            chunk_2.text,
            metadata,
            chunk_index=0
        )
        
        # IDs should be the same (de-duplication)
        assert chunk_id_1 == chunk_id_2
    
    def test_pdf_deduplication_different_content(self):
        """Test that different PDFs create different IDs"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        id_generator = IDGenerator()
        
        file_path_1 = SAMPLE_DATA_DIR / 'text_document.pdf'
        file_path_2 = SAMPLE_DATA_DIR / 'faq_document.pdf'
        
        if not file_path_1.exists() or not file_path_2.exists():
            pytest.skip("Sample PDFs not found")
        
        # Extract first PDF
        extraction_result_1 = router.extract(file_path_1, file_type='pdf')
        assert extraction_result_1.success
        
        metadata_1 = {
            'category': 'general_information',
            'language': 'en',
            'source_file': 'text_document.pdf'
        }
        
        processing_result_1 = routing_engine.route(
            extraction_result_1.content,
            extraction_result_1.extracted_structure,
            metadata_1
        )
        assert processing_result_1.success
        
        # Extract second PDF
        extraction_result_2 = router.extract(file_path_2, file_type='pdf')
        assert extraction_result_2.success
        
        metadata_2 = {
            'category': 'faq_help',
            'language': 'bilingual',
            'source_file': 'faq_document.pdf'
        }
        
        processing_result_2 = routing_engine.route(
            extraction_result_2.content,
            extraction_result_2.extracted_structure,
            metadata_2
        )
        assert processing_result_2.success
        
        # Generate IDs
        chunk_1 = processing_result_1.chunks[0]
        chunk_id_1 = id_generator.generate_chunk_id(
            chunk_1.text,
            metadata_1,
            chunk_index=0
        )
        
        chunk_2 = processing_result_2.chunks[0]
        chunk_id_2 = id_generator.generate_chunk_id(
            chunk_2.text,
            metadata_2,
            chunk_index=0
        )
        
        # IDs should be different
        assert chunk_id_1 != chunk_id_2


class TestPDFEndToEnd:
    """End-to-end tests for PDF processing pipeline"""
    
    def test_complete_pdf_pipeline(self):
        """Test complete pipeline from PDF extraction to chunk creation"""
        router = get_file_type_router()
        routing_engine = get_routing_engine()
        embedder = get_embedder()
        id_generator = IDGenerator()
        
        file_path = SAMPLE_DATA_DIR / 'text_document.pdf'
        
        if not file_path.exists():
            pytest.skip(f"Sample PDF not found: {file_path}")
        
        # Step 1: Extract
        extraction_result = router.extract(file_path, file_type='pdf')
        assert extraction_result.success
        assert extraction_result.content is not None
        
        # Step 2: Process
        metadata = {
            'category': 'general_information',
            'language': 'en',
            'importance': 'normal',
            'source_file': 'text_document.pdf'
        }
        
        processing_result = routing_engine.route(
            extraction_result.content,
            extraction_result.extracted_structure,
            metadata
        )
        assert processing_result.success
        assert processing_result.valid_chunks > 0
        
        # Step 3: Generate embeddings and IDs
        for i, chunk in enumerate(processing_result.chunks[:3]):  # Test first 3 chunks
            # Generate embedding
            embedding = embedder.embed_text(chunk.text)
            assert embedding is not None
            assert len(embedding) == 768
            
            # Generate ID
            chunk_id = id_generator.generate_chunk_id(
                chunk.text,
                metadata,
                chunk_index=i
            )
            assert chunk_id is not None
            assert len(chunk_id) > 0


class TestPhase4Summary:
    """Summary test to verify Phase 4 completion"""
    
    def test_phase4_complete(self):
        """Verify all Phase 4 components are working"""
        # Test PDF extractor exists
        router = get_file_type_router()
        assert 'pdf' in router.get_supported_types()
        
        # Test PDF extractor works
        pdf_extractor = router.get_extractor('pdf')
        assert pdf_extractor is not None
        assert pdf_extractor.__class__.__name__ == 'PDFExtractor'
        
        # Test routing engine handles PDF structures
        routing_engine = get_routing_engine()
        pdf_structures = [
            'text_document',
            'document_with_tables',
            'mostly_tables',
            'faq_document',
            'scanned_document',
            'form_template',
            'complex_mix'
        ]
        
        for structure in pdf_structures:
            processor_name = routing_engine.get_processor_for_structure(structure)
            assert processor_name is not None, f"No processor for structure: {structure}"
        
        print("\n✅ Phase 4 PDF Support: All components verified!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

