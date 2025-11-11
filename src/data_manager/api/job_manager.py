"""
Job Manager for DMA Bot Data Management System
Manages processing job state and lifecycle
"""
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

from ..core.config import config
from ..utils.logger import get_job_logger
from ..utils.id_generator import IDGenerator

logger = get_job_logger()


class JobStatus(Enum):
    """Job status enumeration"""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobMetadata:
    """Metadata for a processing job"""
    job_id: str
    status: str
    created_at: str
    updated_at: str
    filename: str
    file_type: str
    file_size: int
    file_hash: str
    
    # User selections from questionnaire
    content_structure: str
    language: str
    category: str
    importance: str = "normal"
    special_elements: List[str] = field(default_factory=list)
    
    # Processing parameters
    chunk_size: str = "medium"
    file_path: str = ""  # Path to uploaded file
    
    # Progress tracking
    progress_percentage: int = 0
    current_step: str = ""
    
    # Results
    chunks_created: int = 0
    chunks_uploaded: int = 0
    source_id: str = ""
    is_duplicate: bool = False
    existing_vectors: int = 0
    
    # Error handling
    error_message: str = ""
    retry_count: int = 0
    
    # Timing
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dictionary for API responses"""
        return asdict(self)


class JobManager:
    """Manage processing jobs"""
    
    def __init__(self):
        self.jobs_dir = config.BASE_DIR / "jobs"
        self.jobs_dir.mkdir(exist_ok=True)
        logger.info("JobManager initialized")
    
    def create_job(
        self,
        filename: str,
        file_type: str,
        file_size: int,
        file_hash: str,
        user_selections: Dict[str, Any]
    ) -> JobMetadata:
        """
        Create a new processing job
        
        Args:
            filename: Original filename
            file_type: File type (pdf, excel, json, etc.)
            file_size: File size in bytes
            file_hash: SHA256 hash of file
            user_selections: User's questionnaire answers
            
        Returns:
            JobMetadata object
        """
        job_id = IDGenerator.generate_job_id()
        now = datetime.now().isoformat()
        
        job = JobMetadata(
            job_id=job_id,
            status=JobStatus.CREATED.value,
            created_at=now,
            updated_at=now,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            content_structure=user_selections.get("content_structure", ""),
            language=user_selections.get("language", "en"),
            category=user_selections.get("category", "general_information"),
            importance=user_selections.get("importance", "normal"),
            special_elements=user_selections.get("special_elements", []),
            chunk_size=user_selections.get("chunk_size", "medium")
        )
        
        self._save_job(job)
        logger.info(f"Job created: {job_id} for {filename}")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[JobMetadata]:
        """
        Retrieve job metadata
        
        Args:
            job_id: Job ID
            
        Returns:
            JobMetadata or None if not found
        """
        job_file = self.jobs_dir / f"{job_id}.json"
        
        if not job_file.exists():
            logger.warning(f"Job not found: {job_id}")
            return None
        
        try:
            with open(job_file, 'r') as f:
                data = json.load(f)
            
            # Convert back to JobMetadata
            job = JobMetadata(**data)
            return job
            
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {str(e)}")
            return None
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        chunks_created: Optional[int] = None,
        chunks_uploaded: Optional[int] = None,
        source_id: Optional[str] = None,
        error_message: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        existing_vectors: Optional[int] = None
    ) -> bool:
        """
        Update job status and progress
        
        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            current_step: Current processing step description
            chunks_created: Number of chunks created
            chunks_uploaded: Number of chunks uploaded
            source_id: Generated source ID
            error_message: Error message if failed
            is_duplicate: Whether this was a duplicate upload
            existing_vectors: Number of existing vectors (if duplicate)
            
        Returns:
            Success status
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        # Update fields
        if status:
            job.status = status.value
        if progress is not None:
            job.progress_percentage = progress
        if current_step:
            job.current_step = current_step
        if chunks_created is not None:
            job.chunks_created = chunks_created
        if chunks_uploaded is not None:
            job.chunks_uploaded = chunks_uploaded
        if source_id:
            job.source_id = source_id
        if error_message:
            job.error_message = error_message
        if is_duplicate is not None:
            job.is_duplicate = is_duplicate
        if existing_vectors is not None:
            job.existing_vectors = existing_vectors
        
        job.updated_at = datetime.now().isoformat()
        
        # Update timing
        if status == JobStatus.PROCESSING and not job.processing_started_at:
            job.processing_started_at = datetime.now().isoformat()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.processing_completed_at = datetime.now().isoformat()
        
        self._save_job(job)
        logger.info(f"Job updated: {job_id} - {status.value if status else 'progress update'}")
        
        return True
    
    def mark_failed(self, job_id: str, error_message: str, increment_retry: bool = False) -> bool:
        """
        Mark job as failed
        
        Args:
            job_id: Job ID
            error_message: Error description
            increment_retry: Whether to increment retry count
            
        Returns:
            Success status
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        job.status = JobStatus.FAILED.value
        job.error_message = error_message
        job.updated_at = datetime.now().isoformat()
        job.processing_completed_at = datetime.now().isoformat()
        
        if increment_retry:
            job.retry_count += 1
        
        self._save_job(job)
        logger.error(f"Job failed: {job_id} - {error_message}")
        
        return True
    
    def mark_completed(self, job_id: str) -> bool:
        """
        Mark job as completed
        
        Args:
            job_id: Job ID
            
        Returns:
            Success status
        """
        return self.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_step="Processing completed successfully"
        )
    
    def can_retry(self, job_id: str) -> bool:
        """
        Check if job can be retried
        
        Args:
            job_id: Job ID
            
        Returns:
            True if retry allowed
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        return job.retry_count < config.JOB_RETRY_LIMIT
    
    def get_all_jobs(self, status: Optional[JobStatus] = None) -> List[JobMetadata]:
        """
        Get all jobs, optionally filtered by status
        
        Args:
            status: Filter by status
            
        Returns:
            List of JobMetadata
        """
        jobs = []
        
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r') as f:
                    data = json.load(f)
                job = JobMetadata(**data)
                
                if status is None or job.status == status.value:
                    jobs.append(job)
                    
            except Exception as e:
                logger.error(f"Failed to load job from {job_file}: {str(e)}")
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs
    
    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of jobs (convenience method for API)
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        jobs = self.get_all_jobs()[:limit]
        return [job.to_dict() for job in jobs]
    
    def get_pending_jobs(self) -> List[str]:
        """
        Get list of pending job IDs for processing
        
        Returns:
            List of job IDs with status 'pending'
        """
        job_ids = []
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r') as f:
                    data = json.load(f)
                status = data.get('status')
                if status in ['pending', 'created']:
                    job_ids.append(data.get('job_id'))
            except Exception as e:
                logger.error(f"Error reading job file {job_file}: {str(e)}")
        return job_ids
    
    def get_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get jobs filtered by status
        
        Args:
            status: Status string (pending, processing, completed, failed)
            limit: Maximum number of jobs to return
        
        Returns:
            List of job dictionaries
        """
        # Map string status to JobStatus enum
        status_map = {
            'pending': JobStatus.CREATED,
            'processing': JobStatus.PROCESSING,
            'completed': JobStatus.COMPLETED,
            'failed': JobStatus.FAILED
        }
        
        job_status = status_map.get(status.lower())
        jobs = self.get_all_jobs(status=job_status)[:limit]
        return [job.to_dict() for job in jobs]
    
    def cleanup_old_jobs(self, days: int = None) -> int:
        """
        Delete job records older than specified days
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of jobs deleted
        """
        days = days or config.JOB_CLEANUP_AFTER_DAYS
        cutoff = datetime.now().timestamp() - (days * 86400)
        deleted_count = 0
        
        for job_file in self.jobs_dir.glob("*.json"):
            if job_file.stat().st_mtime < cutoff:
                job_file.unlink()
                deleted_count += 1
                logger.info(f"Deleted old job file: {job_file.name}")
        
        return deleted_count
    
    def _save_job(self, job: JobMetadata) -> bool:
        """
        Save job to disk
        
        Args:
            job: JobMetadata object
            
        Returns:
            Success status
        """
        job_file = self.jobs_dir / f"{job.job_id}.json"
        
        try:
            with open(job_file, 'w') as f:
                json.dump(asdict(job), f, indent=2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save job {job.job_id}: {str(e)}")
            return False


# Export
__all__ = ['JobManager', 'JobStatus', 'JobMetadata']

