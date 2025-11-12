"""
Processing Orchestrator
Coordinates all steps of the content processing pipeline
"""
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from datetime import datetime

from ..extractors.file_type_router import get_file_type_router
from ..routing.routing_engine import get_routing_engine
from ..embedding.embedder import get_embedder
from ..embedding.vector_preparer import VectorPreparer
from ..database.vector_db_factory import get_vector_db_adapter
from ..database.verifier import UploadVerifier
from ..utils.report_generator import ReportGenerator
from ..utils.id_generator import IDGenerator
from ..utils.logger import get_logger

logger = get_logger('orchestrator')


class ProcessingOrchestrator:
    """
    Orchestrates the complete processing pipeline:
    1. Extract content from file
    2. Route to appropriate processor
    3. Create chunks
    4. Generate embeddings
    5. Prepare vectors
    6. Upload to vector database (modular - supports Pinecone, Qdrant, Weaviate, etc.)
    7. Verify upload
    8. Generate report
    """
    
    def __init__(self):
        self.logger = get_logger('orchestrator')
        
        # Initialize components (singletons)
        self.file_router = get_file_type_router()
        self.routing_engine = get_routing_engine()
        self.embedder = get_embedder()
        self.vector_preparer = VectorPreparer()
        self.vector_db = get_vector_db_adapter()  # Modular vector database adapter
        self.verifier = UploadVerifier()
        self.report_generator = ReportGenerator()
        
        self.logger.info("Orchestrator initialized with all components")
    
    async def process_file(
        self,
        file_path: Path,
        job_metadata: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process a single file through the complete pipeline.
        
        Args:
            file_path: Path to file to process
            job_metadata: Job metadata including:
                - file_type: Type of file
                - content_structure: Content structure type
                - language: Language(s)
                - category: Content category
                - importance: Importance level
                - chunk_size: Chunk size preference
                - special_elements: Special elements to extract
            progress_callback: Optional callback to report progress
        
        Returns:
            Processing result dictionary
        """
        start_time = datetime.now()
        self.logger.info(f"Starting orchestration for: {file_path.name}")
        
        result = {
            "success": False,
            "file_name": file_path.name,
            "stages": {},
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        try:
            # Generate source ID (need file_hash from job_metadata or calculate it)
            file_hash = job_metadata.get('file_hash')
            if not file_hash:
                # Calculate hash if not provided
                from ..utils.file_handler import FileHandler
                file_hash = FileHandler.get_file_hash(file_path)
            
            # Prepare user metadata for source ID generation
            user_metadata_for_id = {
                'category': job_metadata.get('category', ''),
                'content_type': job_metadata.get('content_structure', ''),
                'language': job_metadata.get('language', '')
            }
            
            source_id = IDGenerator.generate_source_id(
                filename=file_path.name,
                file_hash=file_hash,
                user_metadata=user_metadata_for_id
            )
            job_metadata['source_id'] = source_id
            job_metadata['filename'] = file_path.name  # Add filename for metadata enricher
            
            # Stage 1: Extract content
            self._update_progress(progress_callback, 10, "Extracting content from file")
            extraction_result = await self._extract_content(file_path, job_metadata)
            result['stages']['extraction'] = extraction_result
            
            if not extraction_result['success']:
                result['errors'].extend(extraction_result['errors'])
                return result
            
            # Stage 2: Process content into chunks
            self._update_progress(progress_callback, 30, "Processing content and creating chunks")
            processing_result = await self._process_content(
                extraction_result['content'],
                extraction_result['structure'],
                job_metadata
            )
            result['stages']['processing'] = processing_result
            
            if not processing_result['success']:
                result['errors'].extend(processing_result['errors'])
                return result
            
            chunks = processing_result['chunks']
            if not chunks:
                result['errors'].append("No valid chunks created")
                return result
            
            # Stage 3: Generate embeddings
            self._update_progress(progress_callback, 50, "Generating embeddings")
            embedding_result = await self._generate_embeddings(chunks)
            result['stages']['embedding'] = embedding_result
            
            if not embedding_result['success']:
                result['errors'].extend(embedding_result['errors'])
                return result
            
            # Stage 4: Prepare vectors
            self._update_progress(progress_callback, 70, "Preparing vectors for upload")
            vector_result = await self._prepare_vectors(
                chunks,
                embedding_result['embeddings'],
                job_metadata
            )
            result['stages']['vector_preparation'] = vector_result
            
            if not vector_result['success']:
                result['errors'].extend(vector_result['errors'])
                return result
            
            # Stage 5: Upload to Pinecone
            self._update_progress(progress_callback, 85, "Uploading to vector database")
            upload_result = await self._upload_vectors(vector_result['vectors'], source_id=source_id)
            result['stages']['upload'] = upload_result
            
            if not upload_result['success']:
                result['errors'].extend(upload_result['errors'])
                return result
            
            # Stage 6: Verify upload
            self._update_progress(progress_callback, 95, "Verifying upload")
            verification_result = await self._verify_upload(
                source_id,
                len(vector_result['vectors'])
            )
            result['stages']['verification'] = verification_result
            
            # Stage 7: Generate report
            self._update_progress(progress_callback, 100, "Generating report")
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Build report inputs
            source_metadata = {
                'filename': file_path.name,
                'file_type': job_metadata.get('file_type', ''),
                'file_size': file_path.stat().st_size,
                'source_id': source_id,
                'category': job_metadata.get('category', ''),
                'language': job_metadata.get('language', '')
            }
            processing_stats = {
                'status': 'completed',
                'duration_seconds': processing_time,
                'chunks_created': processing_result.get('total_chunks', len(chunks)),
                'chunks_valid': processing_result.get('valid_chunks', len(chunks)),
                'chunks_rejected': processing_result.get('rejected_chunks', 0),
            }
            upload_results = {
                'success': upload_result.get('success', False),
                'uploaded_count': upload_result.get('uploaded_count', 0),
                'errors': upload_result.get('errors', [])
            }
            verification_results = result['stages'].get('verification', {})
            
            report = self.report_generator.generate_processing_report(
                job_id=job_metadata.get('job_id', source_id),
                source_metadata=source_metadata,
                processing_stats=processing_stats,
                upload_results=upload_results,
                verification_results=verification_results
            )
            
            result['report'] = report
            result['success'] = True
            result['source_id'] = source_id
            result['processing_time'] = processing_time
            
            # Collect statistics
            result['statistics'] = {
                'total_chunks': len(chunks),
                'vectors_uploaded': upload_result.get('uploaded_count', 0),
                'processing_time_seconds': processing_time,
                'file_size_bytes': file_path.stat().st_size,
                'is_duplicate': upload_result.get('is_duplicate', False),
                'existing_vectors': upload_result.get('existing_vectors', 0)
            }
            
            self.logger.info(
                f"Orchestration successful: {file_path.name} - "
                f"{result['statistics']['vectors_uploaded']} vectors uploaded"
            )
            
        except Exception as e:
            error_msg = f"Orchestration error: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result['errors'].append(error_msg)
            result['success'] = False
        
        return result
    
    async def _extract_content(
        self,
        file_path: Path,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 1: Extract content from file"""
        try:
            file_type = metadata.get('file_type')
            extraction_result = self.file_router.extract(
                file_path,
                file_type=file_type
            )
            
            if not extraction_result.success:
                return {
                    'success': False,
                    'errors': extraction_result.errors,
                    'warnings': extraction_result.warnings
                }
            
            return {
                'success': True,
                'content': extraction_result.content,
                'structure': extraction_result.extracted_structure,
                'metadata': extraction_result.metadata,
                'warnings': extraction_result.warnings
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Extraction error: {str(e)}"]
            }
    
    async def _process_content(
        self,
        content: Any,
        structure: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 2: Process content into chunks"""
        try:
            processing_result = self.routing_engine.route(
                content=content,
                structure=structure,
                metadata=metadata,
                source_id=metadata.get('source_id')
            )
            
            if not processing_result.success:
                return {
                    'success': False,
                    'errors': processing_result.errors,
                    'warnings': processing_result.warnings
                }
            
            return {
                'success': True,
                'chunks': processing_result.chunks,
                'total_chunks': processing_result.total_chunks,
                'valid_chunks': processing_result.valid_chunks,
                'rejected_chunks': processing_result.rejected_chunks,
                'warnings': processing_result.warnings,
                'stats': processing_result.processing_stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Processing error: {str(e)}"]
            }
    
    async def _generate_embeddings(
        self,
        chunks: list
    ) -> Dict[str, Any]:
        """Stage 3: Generate embeddings for chunks"""
        try:
            texts = [chunk.text for chunk in chunks]
            
            self.logger.info(f"Generating embeddings for {len(texts)} chunks")
            embeddings = self.embedder.embed_batch(texts)
            
            if len(embeddings) != len(texts):
                return {
                    'success': False,
                    'errors': [f"Embedding count mismatch: {len(embeddings)} != {len(texts)}"]
                }
            
            return {
                'success': True,
                'embeddings': embeddings,
                'count': len(embeddings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Embedding error: {str(e)}"]
            }
    
    async def _prepare_vectors(
        self,
        chunks: list,
        embeddings: list,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 4: Prepare vectors for vector database"""
        try:
            # Get source_id from metadata if available
            source_id = metadata.get('source_id', 'unknown')
            
            # Build combined chunk dicts expected by VectorPreparer
            combined = []
            for idx, chunk in enumerate(chunks):
                embedding = embeddings[idx]
                
                # Get chunk_id, generate if empty or missing
                chunk_id = getattr(chunk, 'chunk_id', '')
                if not chunk_id or chunk_id == '':
                    # Generate chunk ID using IDGenerator
                    chunk_text = getattr(chunk, 'text', '')
                    chunk_metadata = getattr(chunk, 'metadata', {})
                    chunk_id = IDGenerator.generate_chunk_id(
                        source_id=source_id,
                        chunk_index=idx,
                        content_sample=chunk_text[:200],  # First 200 chars for uniqueness
                        metadata=chunk_metadata
                    )
                
                combined.append({
                    'id': chunk_id,
                    'embedding': embedding,
                    'text': getattr(chunk, 'text', ''),
                    'metadata': getattr(chunk, 'metadata', {})
                })
            
            # Prepare vectors in Pinecone format
            vectors = self.vector_preparer.prepare_batch(combined)
            
            # Validate vectors
            valid_vectors, validation_errors = self.vector_preparer.validate_batch(vectors)
            if validation_errors:
                return {
                    'success': False,
                    'errors': validation_errors
                }
            
            return {
                'success': True,
                'vectors': valid_vectors,
                'count': len(valid_vectors)
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Vector preparation error: {str(e)}"]
            }
    
    async def _upload_vectors(
        self,
        vectors: list,
        source_id: str = None
    ) -> Dict[str, Any]:
        """Stage 5: Upload vectors to vector database"""
        try:
            self.logger.info(f"Uploading {len(vectors)} vectors to vector database")
            
            # Check if this source already exists (duplicate detection)
            is_duplicate = False
            existing_count = 0
            if source_id:
                exists, existing_count = self.vector_db.check_source_exists(source_id)
                if exists:
                    is_duplicate = True
                    self.logger.info(f"Duplicate detected: Source {source_id} already has {existing_count} vectors")
            
            # upsert_vectors returns (success, count_uploaded, message)
            success, uploaded_count, message = self.vector_db.upsert_vectors(vectors)
            
            if not success:
                return {
                    'success': False,
                    'errors': [message],
                    'is_duplicate': is_duplicate,
                    'existing_vectors': existing_count
                }
            
            return {
                'success': True,
                'uploaded_count': uploaded_count,
                'failed_count': len(vectors) - uploaded_count,
                'is_duplicate': is_duplicate,
                'existing_vectors': existing_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Upload error: {str(e)}"],
                'is_duplicate': False,
                'existing_vectors': 0
            }
    
    async def _verify_upload(
        self,
        source_id: str,
        expected_count: int
    ) -> Dict[str, Any]:
        """Stage 6: Verify upload to vector database"""
        try:
            success, verification = self.verifier.verify_source_upload(
                source_id=source_id,
                expected_count=expected_count
            )
            
            return {
                'success': success,
                'verified_count': verification.get('found', 0),
                'warnings': verification.get('warnings', [])
            }
            
        except Exception as e:
            # Verification failure is not critical
            self.logger.warning(f"Verification error: {str(e)}")
            return {
                'success': False,
                'warnings': [f"Verification failed: {str(e)}"]
            }
    
    def _update_progress(
        self,
        callback: Optional[callable],
        percentage: int,
        message: str
    ):
        """Update progress through callback"""
        if callback:
            try:
                callback(percentage, message)
            except Exception as e:
                self.logger.warning(f"Progress callback error: {str(e)}")
        
        self.logger.info(f"Progress {percentage}%: {message}")


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> ProcessingOrchestrator:
    """Get singleton instance of ProcessingOrchestrator"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ProcessingOrchestrator()
    return _orchestrator_instance

