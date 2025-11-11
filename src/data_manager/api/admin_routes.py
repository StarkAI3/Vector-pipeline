"""
Admin API Routes
FastAPI endpoints for file upload, job management, and status tracking
"""
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
from pathlib import Path
import json

from .job_manager import JobManager
from ..utils.file_handler import FileHandler
from ..utils.logger import get_logger
from ..core.config import Config
from ..database.vector_db_factory import get_vector_db_adapter
from ..database.vector_manager import VectorManager
from ..embedding.embedder import get_embedder

logger = get_logger('api.admin')

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Initialize managers
job_manager = JobManager()
file_handler = FileHandler()

# Initialize vector manager for deletion operations
_vector_manager = None

def get_vector_manager():
    """Get or create vector manager singleton"""
    global _vector_manager
    if _vector_manager is None:
        db_adapter = get_vector_db_adapter()
        _vector_manager = VectorManager(db_adapter)
    return _vector_manager


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    content_structure: str = Form(...),
    language: str = Form(...),
    category: str = Form(...),
    importance: str = Form("normal"),
    chunk_size: str = Form("medium"),
    special_elements: str = Form("[]")  # JSON string
):
    """
    Upload file and create processing job.
    
    Args:
        file: File to upload
        file_type: Type of file (json, excel, pdf, etc.)
        content_structure: Content structure type
        language: Language code
        category: Content category
        importance: Importance level
        chunk_size: Chunk size preference
        special_elements: JSON array of special elements to extract
    
    Returns:
        Job information including job_id for tracking
    """
    try:
        logger.info(f"Received upload request: {file.filename}")
        
        # Parse special elements
        try:
            special_elements_list = json.loads(special_elements)
        except:
            special_elements_list = []
        
        # Validate file type
        if not Config.validate_file_extension(file.filename, file_type):
            raise HTTPException(
                status_code=400,
                detail=f"File extension does not match declared type: {file_type}"
            )
        
        # Save uploaded file (supports SpooledTemporaryFile stream)
        saved_path = file_handler.save_upload(file.file, file.filename)
        
        # Validate file
        is_valid, error = file_handler.validate_file(
            saved_path,
            declared_type=file_type,
            max_size=Config.MAX_FILE_SIZE
        )
        
        if not is_valid:
            file_handler.delete_file(saved_path)
            raise HTTPException(status_code=400, detail=error)
        
        # Get file info
        file_size = saved_path.stat().st_size
        file_hash = FileHandler.get_file_hash(saved_path)
        
        # Prepare user selections for job creation
        user_selections = {
            "content_structure": content_structure,
            "language": language,
            "category": category,
            "importance": importance,
            "special_elements": special_elements_list,
            "chunk_size": chunk_size
        }
        
        # Create processing job
        job = job_manager.create_job(
            filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            user_selections=user_selections
        )
        
        # Save file path to job (need to update job with file_path)
        job.file_path = str(saved_path)
        job_manager._save_job(job)
        
        job_id = job.job_id
        
        logger.info(f"Job created: {job_id} for file: {file.filename}")
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "job_id": job_id,
            "filename": file.filename,
            "file_size": file_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status and progress.
    
    Args:
        job_id: Job ID to query
    
    Returns:
        Job status information
    """
    try:
        job_data = job_manager.get_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "job": job_data.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List jobs with optional filtering.
    
    Args:
        status: Optional status filter (pending, processing, completed, failed)
        limit: Maximum number of jobs to return
    
    Returns:
        List of jobs
    """
    try:
        if status:
            jobs = job_manager.get_jobs_by_status(status, limit=limit)
        else:
            jobs = job_manager.list_jobs(limit=limit)
        
        return {
            "success": True,
            "jobs": jobs,
            "count": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated data.
    
    Args:
        job_id: Job ID to delete
    
    Returns:
        Deletion confirmation
    """
    try:
        job_data = job_manager.get_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Delete associated file if exists
        file_path = job_data.get('file_path')
        if file_path:
            file_path = Path(file_path)
            if file_path.exists():
                file_handler.delete_file(file_path)
        
        # Delete job
        job_manager.delete_job(job_id)
        
        logger.info(f"Job deleted: {job_id}")
        
        return {
            "success": True,
            "message": "Job deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Retry a failed job.
    
    Args:
        job_id: Job ID to retry
    
    Returns:
        Retry confirmation
    """
    try:
        job_data = job_manager.get_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_data['status'] not in ['failed', 'cancelled']:
            raise HTTPException(
                status_code=400,
                detail="Can only retry failed or cancelled jobs"
            )
        
        # Reset job status
        job_manager.update_job(
            job_id,
            status='pending',
            error_message='',
            progress_percentage=0,
            current_step='Queued for retry'
        )
        
        logger.info(f"Job queued for retry: {job_id}")
        
        return {
            "success": True,
            "message": "Job queued for retry"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get system statistics.
    
    Returns:
        System statistics
    """
    try:
        # Get job counts by status
        pending = len(job_manager.get_jobs_by_status('pending'))
        processing = len(job_manager.get_jobs_by_status('processing'))
        completed = len(job_manager.get_jobs_by_status('completed'))
        failed = len(job_manager.get_jobs_by_status('failed'))
        
        # Get Pinecone stats
        from ..database.pinecone_upserter import get_pinecone_upserter
        upserter = get_pinecone_upserter()
        index_stats = upserter.get_index_stats()
        
        return {
            "success": True,
            "stats": {
                "jobs": {
                    "pending": pending,
                    "processing": processing,
                    "completed": completed,
                    "failed": failed,
                    "total": pending + processing + completed + failed
                },
                "vector_database": index_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "DMA Bot Data Manager"
    }


# ============================================================================
# DELETION ENDPOINTS
# ============================================================================

@router.get("/documents")
async def list_documents(limit: int = 100):
    """
    List all documents in the vector database.
    
    Returns:
        List of documents with metadata
    """
    try:
        manager = get_vector_manager()
        documents = manager.list_all_documents(limit=limit)
        
        return {
            "success": True,
            "documents": [doc.to_dict() for doc in documents],
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{source_id}")
async def get_document_details(source_id: str):
    """
    Get detailed information about a document.
    
    Args:
        source_id: Source ID of the document
        
    Returns:
        Document details with all chunks
    """
    try:
        manager = get_vector_manager()
        doc_info = manager.get_document_details(source_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "document": doc_info.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/semantic")
async def search_by_content(
    query: str = Form(...),
    top_k: int = Form(10)
):
    """
    Search chunks by semantic similarity.
    
    Args:
        query: Text query to search for
        top_k: Number of results to return
        
    Returns:
        Search results with confidence scores
    """
    try:
        manager = get_vector_manager()
        embedder = get_embedder()
        
        # Generate embedding
        embedding = embedder.embed_text(query).tolist()  # Convert numpy array to list
        
        # Search
        result = manager.search_chunks_by_content(
            text_query=query,
            query_embedding=embedding,
            top_k=top_k
        )
        
        return {
            "success": True,
            "result": result.to_dict()
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/filename")
async def search_by_filename(filename: str, exact: bool = True):
    """
    Search documents by filename.
    
    Args:
        filename: Filename to search for
        exact: Require exact match
        
    Returns:
        List of matching documents
    """
    try:
        manager = get_vector_manager()
        documents = manager.search_by_filename(filename, exact=exact)
        
        return {
            "success": True,
            "documents": [doc.to_dict() for doc in documents],
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error searching by filename: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/preview")
async def preview_deletion(
    source_ids: Optional[List[str]] = None,
    chunk_ids: Optional[List[str]] = None,
    filter_dict: Optional[dict] = None
):
    """
    Preview what will be deleted before executing.
    
    Args:
        source_ids: Optional list of source IDs
        chunk_ids: Optional list of chunk IDs
        filter_dict: Optional metadata filter
        
    Returns:
        Deletion preview with impact analysis
    """
    try:
        manager = get_vector_manager()
        preview = manager.get_deletion_preview(
            source_ids=source_ids,
            chunk_ids=chunk_ids,
            filter_dict=filter_dict
        )
        
        return {
            "success": True,
            "preview": preview.to_dict()
        }
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{source_id}")
async def delete_document(source_id: str, verify: bool = True):
    """
    Delete an entire document (all its chunks).
    
    Args:
        source_id: Source ID to delete
        verify: Verify deletion after execution
        
    Returns:
        Deletion result
    """
    try:
        manager = get_vector_manager()
        result = manager.delete_document(source_id, verify=verify)
        
        return {
            "success": result.success,
            "result": result.to_dict()
        }
    except Exception as e:
        logger.error(f"Error deleting document {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/documents")
async def delete_documents_batch(source_ids: List[str] = Body(...)):
    """
    Delete multiple documents in batch.
    
    Args:
        source_ids: List of source IDs to delete
        
    Returns:
        Batch deletion result
    """
    try:
        logger.info(f"Received document deletion request for {len(source_ids)} document(s): {source_ids[:3]}...")
        
        manager = get_vector_manager()
        result = manager.delete_documents(source_ids)
        
        logger.info(f"Deletion result - Success: {result.success}, Deleted: {result.total_deleted}, Failed: {result.total_failed}")
        
        if result.errors:
            logger.error(f"Deletion errors: {result.errors}")
        
        return {
            "success": result.success,
            "result": result.to_dict(),
            "message": f"Deleted {result.total_deleted} of {result.total_requested} document(s)"
        }
    except Exception as e:
        logger.error(f"Error in batch deletion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chunk/{chunk_id}")
async def delete_chunk(chunk_id: str, verify: bool = True):
    """
    Delete a single chunk.
    
    Args:
        chunk_id: Chunk ID to delete
        verify: Verify deletion after execution
        
    Returns:
        Deletion result
    """
    try:
        manager = get_vector_manager()
        result = manager.delete_chunk(chunk_id, verify=verify)
        
        return {
            "success": result.success,
            "result": result.to_dict()
        }
    except Exception as e:
        logger.error(f"Error deleting chunk {chunk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/chunks")
async def delete_chunks_batch(chunk_ids: List[str] = Body(...)):
    """
    Delete multiple chunks in batch.
    
    Args:
        chunk_ids: List of chunk IDs to delete
        
    Returns:
        Batch deletion result
    """
    try:
        logger.info(f"Received chunk deletion request for {len(chunk_ids)} chunk(s): {chunk_ids[:3]}...")
        
        manager = get_vector_manager()
        result = manager.delete_chunks(chunk_ids)
        
        logger.info(f"Deletion result - Success: {result.success}, Deleted: {result.total_deleted}, Failed: {result.total_failed}")
        
        if result.errors:
            logger.error(f"Deletion errors: {result.errors}")
        
        return {
            "success": result.success,
            "result": result.to_dict(),
            "message": f"Deleted {result.total_deleted} of {result.total_requested} chunk(s)"
        }
    except Exception as e:
        logger.error(f"Error in batch chunk deletion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/by-content")
async def delete_by_content(
    query: str,
    top_k: int = 10,
    auto_select_high_confidence: bool = False,
    confidence_threshold: float = 0.95,
    dry_run: bool = True
):
    """
    Find and delete chunks by semantic search.
    
    Args:
        query: Text query to search for
        top_k: Number of results
        auto_select_high_confidence: Auto-select high confidence results
        confidence_threshold: Minimum score for auto-selection
        dry_run: If True, only preview without deleting
        
    Returns:
        Search results and deletion preview/result
    """
    try:
        manager = get_vector_manager()
        embedder = get_embedder()
        embedding = embedder.embed_text(query).tolist()  # Convert numpy array to list
        
        result = manager.find_and_delete_by_content(
            text_query=query,
            query_embedding=embedding,
            top_k=top_k,
            auto_select_high_confidence=auto_select_high_confidence,
            confidence_threshold=confidence_threshold,
            dry_run=dry_run
        )
        
        return {
            "success": True,
            "dry_run": dry_run,
            "search_result": result['search_result'].to_dict() if 'search_result' in result else None,
            "selected_chunks": [c.to_dict() for c in result.get('selected_chunks', [])],
            "preview": result.get('preview').to_dict() if result.get('preview') else None,
            "deletion_result": result.get('deletion_result').to_dict() if result.get('deletion_result') else None
        }
    except Exception as e:
        logger.error(f"Error in content-based deletion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

