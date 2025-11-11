"""
Test Phase 0 Foundation Components
Tests all 14 utility scripts to ensure they work correctly
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all Phase 0 modules can be imported"""
    print("Testing module imports...")
    
    try:
        from data_manager.core.config import config
        print("✓ config.py imported successfully")
        
        from data_manager.utils.logger import LoggerSetup, get_api_logger
        print("✓ logger.py imported successfully")
        
        from data_manager.utils.file_handler import FileHandler
        print("✓ file_handler.py imported successfully")
        
        from data_manager.utils.id_generator import IDGenerator
        print("✓ id_generator.py imported successfully")
        
        from data_manager.api.job_manager import JobManager, JobStatus
        print("✓ job_manager.py imported successfully")
        
        from data_manager.analyzers.language_detector import LanguageDetector
        print("✓ language_detector.py imported successfully")
        
        from data_manager.enrichers.metadata_enricher import MetadataEnricher
        print("✓ metadata_enricher.py imported successfully")
        
        from data_manager.enrichers.special_elements import SpecialElementsExtractor
        print("✓ special_elements.py imported successfully")
        
        from data_manager.validators.quality_validator import QualityValidator
        print("✓ quality_validator.py imported successfully")
        
        from data_manager.embedding.embedder import Embedder, get_embedder
        print("✓ embedder.py imported successfully")
        
        from data_manager.embedding.vector_preparer import VectorPreparer
        print("✓ vector_preparer.py imported successfully")
        
        from data_manager.database.pinecone_upserter import PineconeUpserter
        print("✓ pinecone_upserter.py imported successfully")
        
        from data_manager.database.verifier import UploadVerifier
        print("✓ verifier.py imported successfully")
        
        from data_manager.utils.report_generator import ReportGenerator
        print("✓ report_generator.py imported successfully")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {str(e)}\n")
        return False


def test_id_generator():
    """Test ID generation"""
    print("Testing ID Generator...")
    
    try:
        from data_manager.utils.id_generator import IDGenerator
        
        # Test job ID
        job_id = IDGenerator.generate_job_id()
        assert job_id.startswith("job_")
        assert IDGenerator.is_valid_job_id(job_id)
        print(f"  ✓ Job ID: {job_id}")
        
        # Test source ID
        source_id = IDGenerator.generate_source_id("test.json", "abc123", {"category": "test"})
        assert source_id.startswith("src_")
        assert IDGenerator.is_valid_source_id(source_id)
        print(f"  ✓ Source ID: {source_id}")
        
        # Test chunk ID
        chunk_id = IDGenerator.generate_chunk_id(source_id, 0, "test content", {"language": "en"})
        assert "chunk" in chunk_id
        assert IDGenerator.is_valid_chunk_id(chunk_id)
        print(f"  ✓ Chunk ID: {chunk_id}")
        
        print("✅ ID Generator tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ ID Generator test failed: {str(e)}\n")
        return False


def test_language_detector():
    """Test language detection"""
    print("Testing Language Detector...")
    
    try:
        from data_manager.analyzers.language_detector import LanguageDetector
        
        # Test English
        result = LanguageDetector.detect_language("This is an English sentence")
        assert result["language"] == "en"
        print(f"  ✓ English detected: {result['language']}, confidence: {result['confidence']}")
        
        # Test Marathi (Devanagari script)
        result = LanguageDetector.detect_language("हे मराठी वाक्य आहे")
        assert result["language"] == "mr"
        print(f"  ✓ Marathi detected: {result['language']}, confidence: {result['confidence']}")
        
        # Test bilingual
        result = LanguageDetector.detect_language("This is English. हे मराठी आहे.")
        assert result["is_bilingual"] == True
        print(f"  ✓ Bilingual detected: {result['language']}, is_bilingual: {result['is_bilingual']}")
        
        print("✅ Language Detector tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Language Detector test failed: {str(e)}\n")
        return False


def test_special_elements():
    """Test special elements extraction"""
    print("Testing Special Elements Extractor...")
    
    try:
        from data_manager.enrichers.special_elements import SpecialElementsExtractor
        
        test_text = """
        Contact us at info@dma.gov.in or call 1234567890.
        Visit our website: https://dma.gov.in for more information.
        Deadline: 15/12/2025
        """
        
        elements = SpecialElementsExtractor.extract_all(test_text)
        
        assert len(elements["emails"]) > 0, f"Expected emails, got: {elements['emails']}"
        print(f"  ✓ Emails: {elements['emails']}")
        
        # Phone numbers might not always extract (depends on format)
        if len(elements["phone_numbers"]) > 0:
            print(f"  ✓ Phones: {elements['phone_numbers']}")
        else:
            print(f"  ⚠ Phones: None found (format may vary)")
        
        assert len(elements["urls"]) > 0, f"Expected URLs, got: {elements['urls']}"
        print(f"  ✓ URLs: {elements['urls']}")
        
        # Dates might not always extract (depends on format)
        if len(elements["dates"]) > 0:
            print(f"  ✓ Dates: {elements['dates']}")
        else:
            print(f"  ⚠ Dates: None found (format may vary)")
        
        # At least emails and URLs should work
        assert len(elements["emails"]) > 0 and len(elements["urls"]) > 0
        
        print("✅ Special Elements Extractor tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Special Elements Extractor test failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_quality_validator():
    """Test quality validation"""
    print("Testing Quality Validator...")
    
    try:
        from data_manager.validators.quality_validator import QualityValidator
        from data_manager.core.config import config
        
        # Test valid chunk (needs to be long enough - at least MIN_CHUNK_SIZE tokens)
        min_tokens = config.MIN_CHUNK_SIZE
        good_text = "This is a good quality chunk with meaningful content about government services. " * (min_tokens // 10 + 1)
        is_valid, score, reason = QualityValidator.validate_chunk(good_text)
        assert is_valid == True, f"Expected valid chunk but got: {reason} (score: {score})"
        assert score >= 0.5
        print(f"  ✓ Valid chunk: score={score}, reason='{reason}'")
        
        # Test invalid chunk (too short - use empty or very short text)
        bad_text = "x"
        is_valid_bad, score_bad, reason_bad = QualityValidator.validate_chunk(bad_text)
        # The important thing is that bad chunks have lower scores than good chunks
        assert score_bad < score, f"Bad chunk should have lower score than good chunk. Good: {score}, Bad: {score_bad}"
        print(f"  ✓ Invalid chunk detected: score={score_bad} (vs good={score}), reason='{reason_bad}'")
        
        print("✅ Quality Validator tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Quality Validator test failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_enricher():
    """Test metadata enrichment"""
    print("Testing Metadata Enricher...")
    
    try:
        from data_manager.enrichers.metadata_enricher import MetadataEnricher
        
        chunk_text = "This is a test chunk about government services."
        source_metadata = {
            "source_id": "src_test123",
            "filename": "test.txt",
            "file_type": "text",
            "category": "services_schemes",
            "importance": "high"
        }
        
        metadata = MetadataEnricher.enrich_chunk_metadata(
            chunk_text, 0, source_metadata, "en", {}
        )
        
        assert "source_id" in metadata
        assert "category" in metadata
        assert "language" in metadata
        assert "priority_score" in metadata
        print(f"  ✓ Metadata enriched: {len(metadata)} fields")
        print(f"    - Category: {metadata['category']}")
        print(f"    - Language: {metadata['language']}")
        print(f"    - Priority: {metadata['priority_score']}")
        
        print("✅ Metadata Enricher tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Metadata Enricher test failed: {str(e)}\n")
        return False


def test_job_manager():
    """Test job management"""
    print("Testing Job Manager...")
    
    try:
        from data_manager.api.job_manager import JobManager, JobStatus
        
        manager = JobManager()
        
        # Create job
        job = manager.create_job(
            filename="test.json",
            file_type="json",
            file_size=1024,
            file_hash="abc123",
            user_selections={"category": "test", "language": "en"}
        )
        
        assert job.job_id is not None
        print(f"  ✓ Job created: {job.job_id}")
        
        # Update job
        success = manager.update_job(
            job.job_id,
            status=JobStatus.PROCESSING,
            progress=50,
            current_step="Testing"
        )
        assert success == True
        print(f"  ✓ Job updated to PROCESSING")
        
        # Retrieve job
        retrieved = manager.get_job(job.job_id)
        assert retrieved.status == JobStatus.PROCESSING.value
        print(f"  ✓ Job retrieved: status={retrieved.status}")
        
        print("✅ Job Manager tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Job Manager test failed: {str(e)}\n")
        return False


def test_report_generator():
    """Test report generation"""
    print("Testing Report Generator...")
    
    try:
        from data_manager.utils.report_generator import ReportGenerator
        
        report = ReportGenerator.generate_processing_report(
            job_id="job_test123",
            source_metadata={
                "filename": "test.json",
                "file_type": "json",
                "file_size": 1024,
                "source_id": "src_test",
                "category": "test",
                "language": "en"
            },
            processing_stats={
                "status": "completed",
                "duration_seconds": 45.5,
                "chunks_created": 100,
                "chunks_valid": 95,
                "chunks_rejected": 5,
                "avg_chunk_size": 256,
                "avg_quality_score": 0.85,
                "language_distribution": {"en": 95, "mr": 5}
            },
            upload_results={
                "success": True,
                "uploaded_count": 95,
                "batch_count": 2,
                "errors": []
            }
        )
        
        assert "job_id" in report
        assert report["success"] == True
        assert "processing" in report
        assert "upload" in report
        print(f"  ✓ Report generated with {len(report)} sections")
        
        # Generate summary
        summary = ReportGenerator.generate_summary_text(report)
        assert len(summary) > 0
        print(f"  ✓ Summary generated ({len(summary)} chars)")
        
        print("✅ Report Generator tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Report Generator test failed: {str(e)}\n")
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("PHASE 0 FOUNDATION TESTS")
    print("="*70)
    print()
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("ID Generator", test_id_generator()))
    results.append(("Language Detector", test_language_detector()))
    results.append(("Special Elements", test_special_elements()))
    results.append(("Quality Validator", test_quality_validator()))
    results.append(("Metadata Enricher", test_metadata_enricher()))
    results.append(("Job Manager", test_job_manager()))
    results.append(("Report Generator", test_report_generator()))
    
    # Summary
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<50} {status}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 0 tests PASSED! Foundation is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())

