"""
Phase 1 Integration Tests
Tests JSON extraction, processing, and complete pipeline
"""
import pytest
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_manager.extractors.json_extractor import JSONExtractor
from data_manager.extractors.file_type_router import FileTypeRouter
from data_manager.processors.tabular_processor import TabularProcessor
from data_manager.processors.directory_processor import DirectoryProcessor
from data_manager.processors.web_content_processor import WebContentProcessor
from data_manager.routing.routing_engine import RoutingEngine


class TestJSONExtraction:
    """Test JSON extraction functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.extractor = JSONExtractor()
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
    
    def create_test_json(self, filename: str, data: dict):
        """Helper to create test JSON file"""
        file_path = self.test_data_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return file_path
    
    def test_extractor_initialization(self):
        """Test extractor initializes correctly"""
        assert self.extractor is not None
        assert self.extractor.get_supported_extensions() == ['.json']
    
    def test_extract_array_of_objects(self):
        """Test extraction of array of objects structure"""
        test_data = [
            {"name": "John Doe", "position": "Manager", "contact": "123-456"},
            {"name": "Jane Smith", "position": "Supervisor", "contact": "789-012"}
        ]
        
        file_path = self.create_test_json("test_array.json", test_data)
        
        result = self.extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "array_of_objects"
        assert len(result.content) == 2
        assert result.content[0]["name"] == "John Doe"
    
    def test_extract_nested_objects(self):
        """Test extraction of nested objects structure"""
        test_data = {
            "officials": {
                "department1": [
                    {"name": "Officer 1", "role": "Head"}
                ],
                "department2": [
                    {"name": "Officer 2", "role": "Deputy"}
                ]
            }
        }
        
        file_path = self.create_test_json("test_nested.json", test_data)
        
        result = self.extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "nested_objects"
        assert result.content is not None
    
    def test_extract_web_scraping_output(self):
        """Test extraction of web scraping format"""
        test_data = {
            "url": "https://example.com/page",
            "title": "Test Page",
            "content": "This is the page content",
            "links": ["https://example.com/link1"]
        }
        
        file_path = self.create_test_json("test_web.json", test_data)
        
        result = self.extractor.extract(file_path)
        
        assert result.success
        assert result.extracted_structure == "web_scraping_output"
        assert result.content[0]["url"] == "https://example.com/page"
    
    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        file_path = self.test_data_dir / "invalid.json"
        with open(file_path, 'w') as f:
            f.write("{invalid json content")
        
        result = self.extractor.extract(file_path)
        
        assert not result.success
        assert len(result.errors) > 0


class TestTabularProcessor:
    """Test tabular data processing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = TabularProcessor()
    
    def test_processor_initialization(self):
        """Test processor initializes correctly"""
        assert self.processor is not None
        assert "array_of_objects" in self.processor.get_supported_structures()
    
    def test_process_simple_table(self):
        """Test processing simple tabular data"""
        test_data = [
            {"service": "Birth Certificate", "department": "Municipal", "fee": "50"},
            {"service": "Death Certificate", "department": "Municipal", "fee": "50"}
        ]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "services_schemes"
        }
        
        result = self.processor.process(test_data, metadata)
        
        assert result.success
        assert result.valid_chunks > 0
        assert len(result.chunks) > 0
        
        # Check chunk content
        first_chunk = result.chunks[0]
        assert "Birth Certificate" in first_chunk.text
        assert first_chunk.language == "en"
    
    def test_process_with_variants(self):
        """Test processing with search variants"""
        test_data = [
            {"name": "John Doe", "position": "Manager", "phone": "123-456"}
        ]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "government_officials"
        }
        
        result = self.processor.process(
            test_data,
            metadata,
            create_variants=True
        )
        
        assert result.success
        # Should have primary chunk + variant
        assert result.valid_chunks >= 1


class TestDirectoryProcessor:
    """Test directory/contact list processing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = DirectoryProcessor()
    
    def test_process_directory(self):
        """Test processing directory entries"""
        test_data = [
            {
                "name": "John Doe",
                "position": "Municipal Commissioner",
                "department": "Administration",
                "phone": "022-1234567",
                "email": "john@example.com"
            }
        ]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "contact_information"
        }
        
        result = self.processor.process(test_data, metadata)
        
        assert result.success
        assert result.valid_chunks > 0
        
        # Should create multiple search variants
        assert len(result.chunks) >= 3  # comprehensive + variants


class TestWebContentProcessor:
    """Test web content processing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = WebContentProcessor()
    
    def test_process_web_content(self):
        """Test processing web scraping output"""
        test_data = [{
            "url": "https://example.com/services",
            "title": "Municipal Services",
            "content": "This is a test page about municipal services. " * 20,
            "links": []
        }]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "services_schemes"
        }
        
        result = self.processor.process(test_data, metadata)
        
        assert result.success
        assert result.valid_chunks > 0


class TestRoutingEngine:
    """Test content routing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = RoutingEngine()
    
    def test_route_tabular_data(self):
        """Test routing of tabular data"""
        content = [
            {"field1": "value1", "field2": "value2"}
        ]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "general_information"
        }
        
        result = self.engine.route(
            content=content,
            structure="array_of_objects",
            metadata=metadata
        )
        
        assert result.success
        assert "processor_used" in result.processing_stats
    
    def test_route_directory_data(self):
        """Test routing of directory data"""
        content = [
            {"name": "John", "position": "Manager", "phone": "123"}
        ]
        
        metadata = {
            "source_id": "test_source",
            "language": "en",
            "category": "contact_information"
        }
        
        result = self.engine.route(
            content=content,
            structure="array_of_objects",
            metadata=metadata
        )
        
        assert result.success
        # Should route to directory processor based on category
        assert "DirectoryProcessor" in result.processing_stats.get("processor_used", "")


class TestFileTypeRouter:
    """Test file type routing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.router = FileTypeRouter()
    
    def test_get_json_extractor(self):
        """Test getting JSON extractor"""
        extractor = self.router.get_extractor('json')
        assert extractor is not None
        assert isinstance(extractor, JSONExtractor)
    
    def test_supported_types(self):
        """Test getting supported types"""
        types = self.router.get_supported_types()
        assert 'json' in types
    
    def test_is_supported(self):
        """Test file support check"""
        test_file = Path("test.json")
        # Create temporary file for test
        test_file.touch()
        
        is_supported = self.router.is_supported(test_file)
        assert is_supported
        
        # Cleanup
        test_file.unlink()


def run_tests():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("Phase 1: JSON Support - Integration Tests")
    print("=" * 60)
    print()
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])


if __name__ == "__main__":
    run_tests()

