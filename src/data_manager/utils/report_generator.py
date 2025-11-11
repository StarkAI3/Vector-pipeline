"""
Report Generator for DMA Bot Data Management System
Creates detailed processing reports with statistics
"""
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from ..core.config import config
from .logger import LoggerSetup

logger = LoggerSetup.get_logger("data_manager.report_generator")


class ReportGenerator:
    """Generate processing reports for users"""
    
    @classmethod
    def generate_processing_report(
        cls,
        job_id: str,
        source_metadata: Dict[str, Any],
        processing_stats: Dict[str, Any],
        upload_results: Dict[str, Any],
        verification_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive processing report
        
        Args:
            job_id: Job ID
            source_metadata: Source file metadata
            processing_stats: Processing statistics
            upload_results: Upload results
            verification_results: Optional verification results
            
        Returns:
            Complete report dict
        """
        report = {
            # Report metadata
            "report_id": f"report_{job_id}",
            "job_id": job_id,
            "generated_at": datetime.now().isoformat(),
            "report_version": "1.0",
            
            # Source information
            "source": {
                "filename": source_metadata.get("filename", ""),
                "file_type": source_metadata.get("file_type", ""),
                "file_size_bytes": source_metadata.get("file_size", 0),
                "file_size_mb": round(source_metadata.get("file_size", 0) / (1024 * 1024), 2),
                "source_id": source_metadata.get("source_id", ""),
                "category": source_metadata.get("category", ""),
                "language": source_metadata.get("language", ""),
            },
            
            # Processing summary
            "processing": {
                "status": processing_stats.get("status", "completed"),
                "duration_seconds": processing_stats.get("duration_seconds", 0),
                "duration_formatted": cls._format_duration(processing_stats.get("duration_seconds", 0)),
                "chunks_created": processing_stats.get("chunks_created", 0),
                "chunks_valid": processing_stats.get("chunks_valid", 0),
                "chunks_rejected": processing_stats.get("chunks_rejected", 0),
                "rejection_rate": cls._calculate_percentage(
                    processing_stats.get("chunks_rejected", 0),
                    processing_stats.get("chunks_created", 0)
                ),
            },
            
            # Upload results
            "upload": {
                "success": upload_results.get("success", False),
                "vectors_uploaded": upload_results.get("uploaded_count", 0),
                "upload_batches": upload_results.get("batch_count", 0),
                "errors": upload_results.get("errors", []),
            },
            
            # Quality metrics
            "quality": {
                "avg_chunk_size": processing_stats.get("avg_chunk_size", 0),
                "avg_quality_score": processing_stats.get("avg_quality_score", 0),
                "language_distribution": processing_stats.get("language_distribution", {}),
            },
            
            # Overall status
            "overall_status": "success" if upload_results.get("success") else "failed",
            "success": upload_results.get("success", False),
        }
        
        # Add verification results if available
        if verification_results:
            report["verification"] = {
                "performed": True,
                "passed": verification_results.get("overall_success", False),
                "upload_verified": verification_results.get("upload_verification", {}).get("success", False),
                "retrieval_tested": verification_results.get("retrieval_test", {}).get("success", False),
            }
        else:
            report["verification"] = {
                "performed": False
            }
        
        logger.info(f"Generated report for job {job_id}")
        
        return report
    
    @classmethod
    def generate_summary_text(cls, report: Dict[str, Any]) -> str:
        """
        Generate human-readable summary text
        
        Args:
            report: Report dictionary
            
        Returns:
            Formatted summary text
        """
        success_icon = "✓" if report["success"] else "✗"
        
        summary = f"""
{success_icon} Processing Report - {report['job_id']}
{'='*60}

SOURCE INFORMATION:
  • File: {report['source']['filename']}
  • Type: {report['source']['file_type']}
  • Size: {report['source']['file_size_mb']} MB
  • Category: {report['source']['category']}
  • Language: {report['source']['language']}
  • Source ID: {report['source']['source_id']}

PROCESSING RESULTS:
  • Status: {report['processing']['status']}
  • Duration: {report['processing']['duration_formatted']}
  • Chunks Created: {report['processing']['chunks_created']}
  • Chunks Valid: {report['processing']['chunks_valid']}
  • Chunks Rejected: {report['processing']['chunks_rejected']} ({report['processing']['rejection_rate']}%)

UPLOAD RESULTS:
  • Vectors Uploaded: {report['upload']['vectors_uploaded']}
  • Upload Batches: {report['upload']['upload_batches']}
  • Success: {report['upload']['success']}
"""
        
        if report['upload']['errors']:
            summary += f"\n  • Errors: {len(report['upload']['errors'])} errors occurred\n"
        
        if report['verification']['performed']:
            summary += f"""
VERIFICATION:
  • Upload Verified: {report['verification']['upload_verified']}
  • Retrieval Tested: {report['verification']['retrieval_tested']}
"""
        
        summary += f"""
QUALITY METRICS:
  • Avg Chunk Size: {report['quality']['avg_chunk_size']} tokens
  • Avg Quality Score: {report['quality']['avg_quality_score']}
"""
        
        summary += f"\n{'='*60}\n"
        summary += f"Overall Status: {report['overall_status'].upper()}\n"
        summary += f"Report Generated: {report['generated_at']}\n"
        
        return summary
    
    @classmethod
    def save_report(cls, report: Dict[str, Any], output_dir: Path = None) -> Path:
        """
        Save report to file
        
        Args:
            report: Report dictionary
            output_dir: Output directory (default: config.LOGS_DIR)
            
        Returns:
            Path to saved report
        """
        output_dir = output_dir or config.LOGS_DIR / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"{report['report_id']}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Report saved to {report_file}")
            
            # Also save text summary
            summary_file = output_dir / f"{report['report_id']}_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(cls.generate_summary_text(report))
            
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
            return None
    
    @classmethod
    def generate_error_report(
        cls,
        job_id: str,
        error_message: str,
        source_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate report for failed processing
        
        Args:
            job_id: Job ID
            error_message: Error description
            source_metadata: Optional source metadata
            
        Returns:
            Error report dict
        """
        report = {
            "report_id": f"report_{job_id}_error",
            "job_id": job_id,
            "generated_at": datetime.now().isoformat(),
            "overall_status": "failed",
            "success": False,
            "error": {
                "message": error_message,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if source_metadata:
            report["source"] = {
                "filename": source_metadata.get("filename", ""),
                "file_type": source_metadata.get("file_type", ""),
            }
        
        logger.info(f"Generated error report for job {job_id}")
        
        return report
    
    @classmethod
    def generate_batch_report(cls, individual_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate report for batch processing
        
        Args:
            individual_reports: List of individual job reports
            
        Returns:
            Batch report dict
        """
        total_jobs = len(individual_reports)
        successful = sum(1 for r in individual_reports if r.get("success"))
        failed = total_jobs - successful
        
        total_vectors = sum(r.get("upload", {}).get("vectors_uploaded", 0) for r in individual_reports)
        
        batch_report = {
            "report_type": "batch",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_jobs": total_jobs,
                "successful": successful,
                "failed": failed,
                "success_rate": cls._calculate_percentage(successful, total_jobs),
                "total_vectors_uploaded": total_vectors
            },
            "individual_reports": [r.get("report_id") for r in individual_reports],
            "overall_success": failed == 0
        }
        
        return batch_report
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable form"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    @staticmethod
    def _calculate_percentage(part: int, total: int) -> float:
        """Calculate percentage"""
        if total == 0:
            return 0.0
        return round((part / total) * 100, 1)
    
    @classmethod
    def generate_statistics_summary(
        cls,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate statistics from chunks
        
        Args:
            chunks: List of processed chunks
            
        Returns:
            Statistics dict
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "avg_quality_score": 0,
                "language_distribution": {}
            }
        
        # Calculate statistics
        chunk_sizes = [len(c.get('text', '').split()) for c in chunks]
        quality_scores = [c.get('quality_score', 0) for c in chunks]
        languages = [c.get('metadata', {}).get('language', 'unknown') for c in chunks]
        
        # Language distribution
        lang_dist = {}
        for lang in languages:
            lang_dist[lang] = lang_dist.get(lang, 0) + 1
        
        stats = {
            "total_chunks": len(chunks),
            "avg_chunk_size": round(sum(chunk_sizes) / len(chunk_sizes), 1) if chunk_sizes else 0,
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0,
            "language_distribution": lang_dist
        }
        
        return stats


# Export
__all__ = ['ReportGenerator']

