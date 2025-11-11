"""
Verifier for DMA Bot Data Management System
Verifies successful upload and tests retrieval
Works with any vector database adapter (modular)
"""
import random
from typing import List, Dict, Any, Tuple

from ..core.config import config
from ..utils.logger import get_database_logger
from .vector_db_factory import get_vector_db_adapter

logger = get_database_logger()


class UploadVerifier:
    """Verify vector uploads and test retrieval (modular - works with any vector DB)"""
    
    def __init__(self):
        """Initialize verifier with vector database adapter"""
        self.vector_db = get_vector_db_adapter()
    
    def verify_upload(
        self,
        uploaded_vector_ids: List[str],
        namespace: str = "",
        sample_size: int = 5
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that vectors were successfully uploaded
        
        Args:
            uploaded_vector_ids: List of vector IDs that were uploaded
            namespace: Namespace used for upload
            sample_size: Number of vectors to sample for verification
            
        Returns:
            Tuple of (success, verification_report)
        """
        if not uploaded_vector_ids:
            return False, {"error": "No vector IDs provided"}
        
        try:
            logger.info(f"Verifying upload of {len(uploaded_vector_ids)} vectors...")
            
            # Sample vectors to check
            sample_ids = random.sample(
                uploaded_vector_ids,
                min(sample_size, len(uploaded_vector_ids))
            )
            
            # Fetch sampled vectors
            fetched = self.vector_db.fetch_vectors(sample_ids, namespace)
            
            found_count = len(fetched)
            expected_count = len(sample_ids)
            
            success = found_count == expected_count
            
            report = {
                "total_uploaded": len(uploaded_vector_ids),
                "sample_size": len(sample_ids),
                "found": found_count,
                "missing": expected_count - found_count,
                "verification_rate": round(found_count / expected_count, 2) if expected_count > 0 else 0,
                "success": success
            }
            
            if success:
                logger.info(f"Verification successful: All {found_count} sampled vectors found")
            else:
                logger.warning(f"Verification incomplete: {found_count}/{expected_count} vectors found")
            
            return success, report
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False, {"error": str(e)}
    
    def test_retrieval(
        self,
        test_vectors: List[Dict[str, Any]],
        namespace: str = "",
        test_count: int = 3
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Test retrieval by querying with sample vectors
        
        Args:
            test_vectors: List of vectors with embeddings to test
            namespace: Namespace to query
            test_count: Number of test queries to run
            
        Returns:
            Tuple of (success, test_report)
        """
        if not test_vectors:
            return False, {"error": "No test vectors provided"}
        
        try:
            logger.info(f"Testing retrieval with {test_count} queries...")
            
            # Sample test vectors
            sample_vectors = random.sample(
                test_vectors,
                min(test_count, len(test_vectors))
            )
            
            successful_queries = 0
            query_results = []
            
            for i, test_vector in enumerate(sample_vectors, 1):
                query_embedding = test_vector.get('embedding', [])
                
                if not query_embedding:
                    logger.warning(f"Test {i}: No embedding found")
                    continue
                
                # Convert numpy array to list if needed
                if hasattr(query_embedding, 'tolist'):
                    query_embedding = query_embedding.tolist()
                
                # Query vector database
                results = self.vector_db.query_vectors(
                    query_vector=query_embedding,
                    top_k=5,
                    namespace=namespace,
                    include_metadata=True
                )
                
                if results:
                    # Check if the vector itself is in top results
                    test_id = test_vector.get('id', '')
                    found_in_results = any(r['id'] == test_id for r in results)
                    
                    query_results.append({
                        "test_id": test_id,
                        "results_count": len(results),
                        "found_self": found_in_results,
                        "top_score": results[0]['score'] if results else 0
                    })
                    
                    if found_in_results or results[0]['score'] > 0.9:
                        successful_queries += 1
                    
                    logger.debug(f"Test {i}: Got {len(results)} results, "
                               f"top score: {results[0]['score']:.3f}")
                else:
                    logger.warning(f"Test {i}: No results returned")
            
            success = successful_queries >= (test_count * 0.8)  # 80% success threshold
            
            report = {
                "tests_run": len(sample_vectors),
                "successful_queries": successful_queries,
                "success_rate": round(successful_queries / len(sample_vectors), 2) if sample_vectors else 0,
                "query_details": query_results,
                "success": success
            }
            
            if success:
                logger.info(f"Retrieval test passed: {successful_queries}/{len(sample_vectors)} successful")
            else:
                logger.warning(f"Retrieval test failed: {successful_queries}/{len(sample_vectors)} successful")
            
            return success, report
            
        except Exception as e:
            logger.error(f"Retrieval test failed: {str(e)}")
            return False, {"error": str(e)}
    
    def verify_source_upload(
        self,
        source_id: str,
        expected_count: int,
        namespace: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that all vectors from a source were uploaded
        
        Args:
            source_id: Source ID to verify
            expected_count: Expected number of vectors
            namespace: Namespace used
            
        Returns:
            Tuple of (success, verification_report)
        """
        try:
            logger.info(f"Verifying source {source_id} ({expected_count} vectors expected)...")
            
            # Query by source_id filter
            # We'll do a dummy query with source filter
            dummy_vector = [0.0] * config.EMBEDDING_DIMENSION
            
            results = self.vector_db.query_vectors(
                query_vector=dummy_vector,
                top_k=expected_count,
                filter_dict={"source_id": source_id},
                namespace=namespace
            )
            
            found_count = len(results)
            success = found_count == expected_count
            
            report = {
                "source_id": source_id,
                "expected": expected_count,
                "found": found_count,
                "success": success,
                "match_rate": round(found_count / expected_count, 2) if expected_count > 0 else 0
            }
            
            if success:
                logger.info(f"Source verification successful: {found_count}/{expected_count} vectors")
            else:
                logger.warning(f"Source verification incomplete: {found_count}/{expected_count} vectors")
            
            return success, report
            
        except Exception as e:
            logger.error(f"Source verification failed: {str(e)}")
            return False, {"error": str(e)}
    
    def comprehensive_verification(
        self,
        uploaded_vectors: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Run comprehensive verification including upload check and retrieval test
        
        Args:
            uploaded_vectors: List of vectors that were uploaded
            namespace: Namespace used
            
        Returns:
            Tuple of (success, comprehensive_report)
        """
        logger.info("Running comprehensive verification...")
        
        comprehensive_report = {
            "upload_verification": {},
            "retrieval_test": {},
            "overall_success": False
        }
        
        # Extract vector IDs
        vector_ids = [v.get('id') for v in uploaded_vectors if v.get('id')]
        
        # 1. Verify upload
        upload_success, upload_report = self.verify_upload(vector_ids, namespace)
        comprehensive_report["upload_verification"] = upload_report
        
        # 2. Test retrieval (only if upload verification passed)
        if upload_success:
            retrieval_success, retrieval_report = self.test_retrieval(
                uploaded_vectors,
                namespace
            )
            comprehensive_report["retrieval_test"] = retrieval_report
            
            comprehensive_report["overall_success"] = upload_success and retrieval_success
        else:
            comprehensive_report["retrieval_test"] = {"skipped": "Upload verification failed"}
            comprehensive_report["overall_success"] = False
        
        if comprehensive_report["overall_success"]:
            logger.info("✓ Comprehensive verification PASSED")
        else:
            logger.warning("✗ Comprehensive verification FAILED")
        
        return comprehensive_report["overall_success"], comprehensive_report
    
    def get_index_health(self) -> Dict[str, Any]:
        """
        Get overall index/collection health metrics
        
        Returns:
            Dict with health metrics
        """
        try:
            stats = self.vector_db.get_index_stats()
            
            health = {
                "status": "healthy" if "error" not in stats else "error",
                "total_vectors": stats.get("total_vectors", 0),
                "dimension": stats.get("dimension", 0),
                "index_fullness": stats.get("index_fullness", 0),
                "connection_ok": self.vector_db.test_connection()
            }
            
            return health
            
        except Exception as e:
            logger.error(f"Failed to get index health: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


# Singleton instance
_verifier_instance = None


def get_verifier() -> UploadVerifier:
    """
    Get singleton verifier instance
    
    Returns:
        UploadVerifier instance
    """
    global _verifier_instance
    
    if _verifier_instance is None:
        _verifier_instance = UploadVerifier()
    
    return _verifier_instance


# Export
__all__ = ['UploadVerifier', 'get_verifier']

