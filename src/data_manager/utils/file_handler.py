"""
File Handler for DMA Bot Data Management System
Manages file operations: save, delete, validate, temp storage
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import hashlib

from ..core.config import config
from .logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.file_handler")


class FileHandler:
    """Handle all file operations for the system"""
    
    @staticmethod
    def save_upload(file_data, filename: str, job_id: str = None) -> Path:
        """
        Save uploaded file to temporary storage
        
        Args:
            file_data: Binary file data
            filename: Original filename
            job_id: Optional job ID for tracking (creates subdirectory if provided)
            
        Returns:
            Path to saved file
        """
        try:
            # Create directory (job-specific if job_id provided, otherwise root upload dir)
            if job_id:
                upload_dir = config.UPLOAD_DIR / job_id
            else:
                upload_dir = config.UPLOAD_DIR
            
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_filename = FileHandler._sanitize_filename(filename)
            file_path = upload_dir / safe_filename
            
            # Save file (supports bytes or file-like objects)
            with open(file_path, 'wb') as f:
                if hasattr(file_data, 'read'):
                    # Stream in chunks
                    while True:
                        chunk = file_data.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                else:
                    # Assume bytes-like
                    f.write(file_data)
            
            logger.info(f"File saved: {file_path}" + (f" (Job: {job_id})" if job_id else ""))
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {str(e)}")
            raise Exception(f"Failed to save file: {str(e)}")
    
    @staticmethod
    def validate_file(file_path: Path, declared_type: str = None, max_size: int = None) -> Tuple[bool, str]:
        """
        Validate file exists, size, and type
        
        Args:
            file_path: Path to file
            declared_type: Declared file type from user
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Check file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "File is empty"
            
            max_file_size = max_size or config.MAX_FILE_SIZE
            if file_size > max_file_size:
                max_mb = max_file_size / (1024 * 1024)
                return False, f"File too large (max {max_mb}MB)"
            
            # Check file extension matches declared type (if provided)
            if declared_type:
                if not config.validate_file_extension(file_path.name, declared_type):
                    return False, f"File extension doesn't match declared type: {declared_type}"
            
            logger.info(f"File validated: {file_path.name} ({file_size} bytes)")
            return True, "File valid"
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def move_to_processed(file_path: Path, job_id: str) -> Tuple[bool, Optional[Path]]:
        """
        Move file from temp to processed directory
        
        Args:
            file_path: Current file path
            job_id: Job ID
            
        Returns:
            Tuple of (success, new_path)
        """
        try:
            processed_dir = config.PROCESSED_DIR / job_id
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            new_path = processed_dir / file_path.name
            shutil.move(str(file_path), str(new_path))
            
            logger.info(f"File moved to processed: {new_path}")
            return True, new_path
            
        except Exception as e:
            logger.error(f"Failed to move file: {str(e)}")
            return False, None
    
    @staticmethod
    def delete_file(file_path: Path) -> bool:
        """
        Delete a file safely
        
        Args:
            file_path: Path to file
            
        Returns:
            Success status
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def delete_job_files(job_id: str) -> bool:
        """
        Delete all files associated with a job
        
        Args:
            job_id: Job ID
            
        Returns:
            Success status
        """
        try:
            # Delete from temp
            temp_dir = config.UPLOAD_DIR / job_id
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Temp files deleted for job: {job_id}")
            
            # Delete from processed
            processed_dir = config.PROCESSED_DIR / job_id
            if processed_dir.exists():
                shutil.rmtree(processed_dir)
                logger.info(f"Processed files deleted for job: {job_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job files {job_id}: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_old_files(days: int = None) -> int:
        """
        Clean up files older than specified days
        
        Args:
            days: Number of days (default from config)
            
        Returns:
            Number of files deleted
        """
        days = days or config.JOB_CLEANUP_AFTER_DAYS
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        try:
            for directory in [config.UPLOAD_DIR, config.PROCESSED_DIR]:
                for job_dir in directory.iterdir():
                    if not job_dir.is_dir():
                        continue
                    
                    # Check directory modification time
                    mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
                    if mtime < cutoff_date:
                        shutil.rmtree(job_dir)
                        deleted_count += 1
                        logger.info(f"Cleaned up old directory: {job_dir}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return deleted_count
    
    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """
        Generate SHA256 hash of file for tracking
        
        Args:
            file_path: Path to file
            
        Returns:
            Hash string
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to hash file: {str(e)}")
            return ""
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Create safe filename by removing dangerous characters
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Split into name and extension first
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            # Sanitize only the name part (keep alphanumeric, hyphens, underscores)
            safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
            # Sanitize extension
            safe_ext = "".join(c for c in ext if c.isalnum())
            # Combine with single extension
            return f"{safe_name[:100]}.{safe_ext}" if safe_name else "uploaded_file"
        else:
            # No extension, just sanitize the name
            safe_name = "".join(c for c in filename if c.isalnum() or c in "-_")
            return safe_name[:100] or "uploaded_file"


# Export
__all__ = ['FileHandler']

