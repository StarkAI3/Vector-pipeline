"""
Processing Worker
Background async worker that processes jobs from the queue
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

from ..core.orchestrator import get_orchestrator
from ..api.job_manager import JobManager
from ..utils.file_handler import FileHandler
from ..utils.logger import get_logger

logger = get_logger('worker')


class ProcessingWorker:
    """
    Background worker that:
    1. Monitors for pending jobs
    2. Processes them through orchestrator
    3. Updates job status
    4. Handles errors and retries
    """
    
    def __init__(self):
        self.logger = get_logger('worker')
        self.orchestrator = get_orchestrator()
        self.job_manager = JobManager()
        self.file_handler = FileHandler()
        self.is_running = False
        self.current_job_id = None
    
    async def start(self):
        """Start the worker (runs indefinitely)"""
        self.is_running = True
        self.logger.info("Processing worker started")
        
        while self.is_running:
            try:
                # Check for pending/created jobs
                pending_jobs = self.job_manager.get_pending_jobs()
                
                # Also get 'created' status jobs
                from ..api.job_manager import JobStatus
                created_jobs = self.job_manager.get_all_jobs(status=JobStatus.CREATED)
                created_job_ids = [job.job_id for job in created_jobs]
                
                all_pending = list(set(pending_jobs + created_job_ids))
                
                if all_pending:
                    for job_id in all_pending:
                        if not self.is_running:
                            break
                        
                        await self.process_job(job_id)
                else:
                    # No jobs, wait before checking again
                    await asyncio.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Worker error: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False
        self.logger.info("Processing worker stopped")
    
    async def process_job(self, job_id: str):
        """
        Process a single job through the complete pipeline.
        
        Args:
            job_id: Job ID to process
        """
        self.current_job_id = job_id
        self.logger.info(f"Starting job: {job_id}")
        
        try:
            # Load job data
            job_data = self.job_manager.get_job(job_id)
            if not job_data:
                self.logger.error(f"Job not found: {job_id}")
                return
            
            # Check if already processing or completed
            if job_data.status in ['processing', 'completed', 'failed']:
                return
            
            # Update status to processing
            from ..api.job_manager import JobStatus
            self.job_manager.update_job(
                job_id,
                status=JobStatus.PROCESSING,
                progress=5,
                current_step='Starting processing'
            )
            
            # Get file path
            file_path = Path(job_data.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Prepare metadata for orchestrator
            job_metadata = {
                'job_id': job_id,
                'file_type': job_data.file_type,
                'content_structure': job_data.content_structure,
                'language': job_data.language,
                'category': job_data.category,
                'importance': job_data.importance,
                'chunk_size': job_data.chunk_size,
                'special_elements': job_data.special_elements,
                'file_hash': job_data.file_hash  # Include file hash for source ID generation
            }
            
            # Create progress callback
            def progress_callback(percentage: int, message: str):
                self.job_manager.update_job(
                    job_id,
                    progress=percentage,
                    current_step=message
                )
            
            # Process through orchestrator
            result = await self.orchestrator.process_file(
                file_path=file_path,
                job_metadata=job_metadata,
                progress_callback=progress_callback
            )
            
            # Update job with results
            if result['success']:
                self.logger.info(f"Job completed successfully: {job_id}")
                
                # Check if duplicate
                is_duplicate = result.get('statistics', {}).get('is_duplicate', False)
                existing_vectors = result.get('statistics', {}).get('existing_vectors', 0)
                
                # Save report
                report_path = self._save_report(job_id, result['report'])
                
                self.job_manager.update_job(
                    job_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    current_step='Processing complete',
                    chunks_created=result['statistics'].get('total_chunks', 0),
                    chunks_uploaded=result['statistics'].get('vectors_uploaded', 0),
                    source_id=result.get('source_id', ''),
                    is_duplicate=is_duplicate,
                    existing_vectors=existing_vectors
                )
                
                # Move file to processed directory
                self.file_handler.move_to_processed(file_path)
                
            else:
                self.logger.error(f"Job failed: {job_id} - {result.get('errors', [])}")
                
                # Check retry count
                from ..core.config import Config
                
                if job_data.retry_count < Config.JOB_RETRY_LIMIT:
                    # Retry - need to set status to pending
                    job_data.status = 'pending'
                    job_data.retry_count = job_data.retry_count + 1
                    job_data.error_message = '; '.join(result.get('errors', []))
                    self.job_manager._save_job(job_data)
                    self.logger.info(f"Job queued for retry ({job_data.retry_count}): {job_id}")
                else:
                    # Max retries exceeded
                    self.job_manager.mark_failed(
                        job_id,
                        '; '.join(result.get('errors', []))
                    )
                    
                    # Move to processed (failed) directory
                    self.file_handler.move_to_processed(file_path, job_id)
        
        except Exception as e:
            error_msg = f"Worker error processing job {job_id}: {str(e)}"
            self.logger.error(error_msg)
            
            # Update job as failed
            self.job_manager.update_job(
                job_id,
                status='failed',
                error_message=error_msg,
                processing_completed_at=datetime.now().isoformat()
            )
        
        finally:
            self.current_job_id = None
    
    def _save_report(self, job_id: str, report: Dict[str, Any]) -> Path:
        """Save processing report to file"""
        from ..core.config import Config
        
        reports_dir = Config.BASE_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_path = reports_dir / f"{job_id}_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    async def process_job_sync(self, job_id: str):
        """Synchronous wrapper for process_job (for testing)"""
        await self.process_job(job_id)


# Global worker instance
_worker_instance = None

def get_worker() -> ProcessingWorker:
    """Get singleton worker instance"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = ProcessingWorker()
    return _worker_instance


async def start_worker():
    """Start the background worker"""
    worker = get_worker()
    await worker.start()

