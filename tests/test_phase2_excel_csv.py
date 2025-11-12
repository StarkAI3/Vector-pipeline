"""
Phase 2 Integration Tests - Excel/CSV Support
Tests all Phase 2 features including extraction, processing, and vector DB compatibility
"""
import pytest
import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_manager.extractors.excel_extractor import ExcelExtractor
from src.data_manager.extractors.csv_extractor import CSVExtractor
from src.data_manager.extractors.file_type_router import get_file_type_router
from src.data_manager.processors.tabular_processor import TabularProcessor
from src.data_manager.processors.faq_table_processor import FAQTableProcessor
from src.data_manager.processors.directory_processor import DirectoryProcessor
from src.data_manager.routing.routing_engine import get_routing_engine
from src.data_manager.embedding.embedder import get_embedder
from src.data_manager.database.vector_db_factory import VectorDBFactory
from src.data_manager.utils.id_generator import IDGenerator
import hashlib

# Test data directory
SAMPLE_DIR = Path(__file__).parent / "sample_data"


def generate_test_source_id(test_name: str) -> str:
    """Generate a source ID for testing"""
    file_hash = hashlib.sha256(test_name.encode()).hexdigest()
    return IDGenerator.generate_source_id(
        filename=f"{test_name}.test",
        file_hash=file_hash,
        user_metadata={'category': 'test', 'content_type': 'test'}
    )


def generate_test_chunk_id(source_id: str, chunk_index: int, text: str, language: str) -> str:
    """Generate a chunk ID for testing"""
    return IDGenerator.generate_chunk_id(
        source_id=source_id,
        chunk_index=chunk_index,
        text=text,
        language=language
    )


class TestExcelExtraction:
    """Test Excel file extraction"""
    
    def test_excel_extractor_initialization(self):
        """Test Excel extractor initializes correctly"""
        extractor = ExcelExtractor()
        assert extractor is not None
        assert '.xlsx' in extractor.get_supported_extensions()
        assert '.xls' in extractor.get_supported_extensions()
    
    def test_standard_table_extraction(self):
        """Test extraction of standard data table"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'standard_table_officials.xlsx'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.file_type == "excel"
        assert isinstance(result.content, list)
        assert len(result.content) == 5
        assert 'Name' in result.content[0]
        assert 'Position' in result.content[0]
    
    def test_faq_table_detection(self):
        """Test FAQ table structure detection"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'faq_table_2col_english.xlsx'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "faq_table"
        assert len(result.content) == 5
    
    def test_bilingual_faq_extraction(self):
        """Test bilingual FAQ extraction"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'faq_table_4col_bilingual.xlsx'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert len(result.content) == 3
        # Check for both English and Marathi columns
        first_entry = result.content[0]
        assert 'Question_EN' in first_entry or any('question' in str(k).lower() for k in first_entry.keys())
    
    def test_directory_extraction(self):
        """Test directory/contact list extraction"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'directory_contact_list.xlsx'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "directory_list"
        assert len(result.content) == 4
    
    def test_multi_sheet_workbook(self):
        """Test multi-sheet workbook extraction"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'multi_sheet_workbook.xlsx'
        
        # Get sheet names
        sheet_names = extractor.get_sheet_names(file_path)
        assert len(sheet_names) == 3
        assert 'Officials' in sheet_names
        assert 'Services' in sheet_names
        assert 'FAQ' in sheet_names
        
        # Extract all sheets
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "multiple_sheets"
        assert isinstance(result.content, dict)
        assert len(result.content) == 3


class TestCSVExtraction:
    """Test CSV file extraction"""
    
    def test_csv_extractor_initialization(self):
        """Test CSV extractor initializes correctly"""
        extractor = CSVExtractor()
        assert extractor is not None
        assert '.csv' in extractor.get_supported_extensions()
    
    def test_standard_csv_extraction(self):
        """Test extraction of standard CSV"""
        extractor = CSVExtractor()
        file_path = SAMPLE_DIR / 'standard_table_officials.csv'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.file_type == "csv"
        assert len(result.content) == 5
    
    def test_csv_encoding_detection(self):
        """Test CSV encoding detection"""
        extractor = CSVExtractor()
        file_path = SAMPLE_DIR / 'complex_data_with_special_chars.csv'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert len(result.content) == 3
    
    def test_faq_csv_extraction(self):
        """Test FAQ CSV extraction"""
        extractor = CSVExtractor()
        file_path = SAMPLE_DIR / 'faq_table_2col_english.csv'
        
        result = extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "faq_table"


class TestFAQProcessing:
    """Test FAQ table processing"""
    
    def test_faq_processor_initialization(self):
        """Test FAQ processor initializes correctly"""
        processor = FAQTableProcessor()
        assert processor is not None
        assert 'faq_table' in processor.get_supported_structures()
    
    def test_monolingual_faq_processing(self):
        """Test processing of English-only FAQ"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'faq_table_2col_english.xlsx'
        extraction_result = extractor.extract(file_path)
        
        processor = FAQTableProcessor()
        metadata = {
            'source_id': generate_test_source_id('faq_test'),
            'category': 'faq_help',
            'language': 'en'
        }
        
        result = processor.process(extraction_result.content, metadata)
        
        assert result.success
        assert result.valid_chunks > 0
        # Should create 1 chunk per FAQ
        assert result.valid_chunks == 5
    
    def test_bilingual_faq_processing(self):
        """Test processing of bilingual FAQ"""
        extractor = ExcelExtractor()
        file_path = SAMPLE_DIR / 'faq_table_4col_bilingual.xlsx'
        extraction_result = extractor.extract(file_path)
        
        processor = FAQTableProcessor()
        metadata = {
            'source_id': generate_test_source_id('faq_bilingual_test'),
            'category': 'faq_help',
            'language': 'bilingual'
        }
        
        result = processor.process(extraction_result.content, metadata)
        
        assert result.success
        assert result.valid_chunks > 0
        # Should create 3 chunks per FAQ (EN, MR, Combined)
        assert result.valid_chunks == 9  # 3 FAQs × 3 chunks each
        
        # Check chunk languages
        languages = [chunk.language for chunk in result.chunks]
        assert 'en' in languages
        assert 'mr' in languages
        assert 'bilingual' in languages


class TestFileTypeRouting:
    """Test file type routing"""
    
    def test_router_supports_excel(self):
        """Test router supports Excel files"""
        router = get_file_type_router()
        assert 'excel' in router.get_supported_types()
    
    def test_router_supports_csv(self):
        """Test router supports CSV files"""
        router = get_file_type_router()
        assert 'csv' in router.get_supported_types()
    
    def test_router_extracts_excel(self):
        """Test router can extract Excel files"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'standard_table_officials.xlsx'
        
        result = router.extract(file_path, file_type='excel')
        
        assert result.success
        assert result.file_type == "excel"
    
    def test_router_extracts_csv(self):
        """Test router can extract CSV files"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'standard_table_officials.csv'
        
        result = router.extract(file_path, file_type='csv')
        
        assert result.success
        assert result.file_type == "csv"


class TestContentRouting:
    """Test content routing to processors"""
    
    def test_routing_engine_handles_faq_table(self):
        """Test routing engine routes FAQ to FAQ processor"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'faq_table_2col_english.xlsx'
        extraction = router.extract(file_path)
        
        routing_engine = get_routing_engine()
        metadata = {
            'source_id': generate_test_source_id('routing_test'),
            'category': 'faq_help',
            'language': 'en'
        }
        
        result = routing_engine.route(
            extraction.content,
            extraction.extracted_structure,
            metadata
        )
        
        assert result.success
        assert result.processing_stats['processor_used'] == 'FAQTableProcessor'
    
    def test_routing_engine_handles_directory(self):
        """Test routing engine routes directory to directory processor"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'directory_contact_list.xlsx'
        extraction = router.extract(file_path)
        
        routing_engine = get_routing_engine()
        metadata = {
            'source_id': generate_test_source_id('directory_test'),
            'category': 'contact_information',
            'language': 'en'
        }
        
        result = routing_engine.route(
            extraction.content,
            extraction.extracted_structure,
            metadata
        )
        
        assert result.success
        assert result.processing_stats['processor_used'] == 'DirectoryProcessor'


class TestEmbeddingGeneration:
    """Test embedding generation for Excel/CSV content"""
    
    def test_embeddings_for_excel_content(self):
        """Test generating embeddings for Excel content"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'standard_table_officials.xlsx'
        extraction = router.extract(file_path)
        
        routing_engine = get_routing_engine()
        metadata = {
            'source_id': generate_test_source_id('embedding_test'),
            'category': 'government_officials',
            'language': 'en'
        }
        
        processing_result = routing_engine.route(
            extraction.content,
            extraction.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        assert len(processing_result.chunks) > 0
        
        # Generate embeddings for first chunk
        embedder = get_embedder()
        chunk = processing_result.chunks[0]
        embeddings = embedder.generate_embeddings([chunk.text])
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768  # multilingual-e5-base dimension


class TestVectorDBCompatibility:
    """Test vector DB compatibility with Excel/CSV data"""
    
    def test_vector_format_preparation(self):
        """Test preparing vectors for database upload"""
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'faq_table_2col_english.xlsx'
        extraction = router.extract(file_path)
        
        routing_engine = get_routing_engine()
        metadata = {
            'source_id': generate_test_source_id('vector_test'),
            'category': 'faq_help',
            'language': 'en'
        }
        
        processing_result = routing_engine.route(
            extraction.content,
            extraction.extracted_structure,
            metadata
        )
        
        assert processing_result.success
        
        # Generate embeddings
        embedder = get_embedder()
        texts = [chunk.text for chunk in processing_result.chunks]
        embeddings = embedder.generate_embeddings(texts)
        
        # Prepare vectors
        from src.data_manager.embedding.vector_preparer import VectorPreparer
        preparer = VectorPreparer()
        
        vectors = []
        for chunk, embedding in zip(processing_result.chunks, embeddings):
            vector = preparer.prepare_vector(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata,
                language=chunk.language
            )
            vectors.append(vector)
        
        assert len(vectors) > 0
        assert all('id' in v for v in vectors)
        assert all('values' in v for v in vectors)
        assert all('metadata' in v for v in vectors)


class TestDeduplication:
    """Test de-duplication works with Excel/CSV data"""
    
    def test_duplicate_detection(self):
        """Test that duplicate content is detected"""
        # Create two identical chunks
        text = "This is a test content for deduplication"
        source_id = generate_test_source_id('dedup_test')
        
        id1 = generate_test_chunk_id(source_id, 0, text, 'en')
        id2 = generate_test_chunk_id(source_id, 0, text, 'en')
        
        # IDs should be the same for identical content
        assert id1 == id2
        
        # Different content should have different IDs
        text2 = "This is different content"
        id3 = generate_test_chunk_id(source_id, 0, text2, 'en')
        assert id1 != id3


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline"""
    
    def test_complete_excel_pipeline(self):
        """Test complete pipeline: Extract → Process → Embed → Prepare"""
        # 1. Extract
        router = get_file_type_router()
        file_path = SAMPLE_DIR / 'service_catalog.xlsx'
        extraction = router.extract(file_path)
        assert extraction.success
        
        # 2. Process
        routing_engine = get_routing_engine()
        metadata = {
            'source_id': generate_test_source_id('e2e_test'),
            'category': 'services_schemes',
            'language': 'bilingual'
        }
        
        processing = routing_engine.route(
            extraction.content,
            extraction.extracted_structure,
            metadata
        )
        assert processing.success
        assert processing.valid_chunks > 0
        
        # 3. Embed
        embedder = get_embedder()
        texts = [chunk.text for chunk in processing.chunks]
        embeddings = embedder.generate_embeddings(texts)
        assert len(embeddings) == len(processing.chunks)
        
        # 4. Prepare for vector DB
        from src.data_manager.embedding.vector_preparer import VectorPreparer
        preparer = VectorPreparer()
        
        vectors = []
        for chunk, embedding in zip(processing.chunks, embeddings):
            vector = preparer.prepare_vector(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata,
                language=chunk.language
            )
            vectors.append(vector)
        
        assert len(vectors) == processing.valid_chunks
        
        # Verify vector format
        for vector in vectors:
            assert 'id' in vector
            assert 'values' in vector
            assert 'metadata' in vector
            assert len(vector['values']) == 768
            assert 'text' in vector['metadata']
            assert 'language' in vector['metadata']


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("Phase 2 Integration Tests - Excel/CSV Support")
    print("=" * 70)
    
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '-x'  # Stop on first failure
    ]
    
    return pytest.main(pytest_args)


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)

