"""
Data Models for Deletion Operations
Provides structured result objects for deletion and discovery operations
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DeletionStatus(Enum):
    """Status of a deletion operation"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class ConfidenceLevel(Enum):
    """Confidence level for semantic search matches"""
    HIGH = "high"      # Score >= 0.95
    MEDIUM = "medium"  # Score >= 0.85
    LOW = "low"        # Score < 0.85


@dataclass
class DeletionResult:
    """Result of a single deletion operation"""
    success: bool
    message: str
    deleted_count: int = 0
    target_id: Optional[str] = None  # source_id or chunk_id
    target_type: str = "unknown"  # "chunk", "document", "filter"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: List[str] = field(default_factory=list)
    
    @property
    def status(self) -> DeletionStatus:
        """Get status enum from success flag"""
        if self.success:
            return DeletionStatus.SUCCESS
        elif self.deleted_count > 0:
            return DeletionStatus.PARTIAL
        else:
            return DeletionStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "deleted_count": self.deleted_count,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "timestamp": self.timestamp,
            "errors": self.errors
        }


@dataclass
class BatchDeletionResult:
    """Result of a batch deletion operation"""
    total_requested: int
    total_deleted: int
    total_failed: int
    individual_results: List[DeletionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Overall success if no failures"""
        return self.total_failed == 0 and self.total_deleted > 0
    
    @property
    def status(self) -> DeletionStatus:
        """Get overall status"""
        if self.total_deleted == self.total_requested:
            return DeletionStatus.SUCCESS
        elif self.total_deleted > 0:
            return DeletionStatus.PARTIAL
        else:
            return DeletionStatus.FAILED
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration if end_time is set"""
        if self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds()
        return 0.0
    
    def complete(self):
        """Mark the batch operation as complete"""
        self.end_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "status": self.status.value,
            "total_requested": self.total_requested,
            "total_deleted": self.total_deleted,
            "total_failed": self.total_failed,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "errors": self.errors,
            "individual_results": [r.to_dict() for r in self.individual_results]
        }


@dataclass
class DocumentInfo:
    """Information about a document in the database"""
    source_id: str
    filename: str
    chunk_count: int
    upload_date: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "chunk_count": self.chunk_count,
            "upload_date": self.upload_date,
            "category": self.category,
            "metadata": self.metadata,
            "chunks": self.chunks
        }


@dataclass
class ChunkInfo:
    """Information about a chunk"""
    chunk_id: str
    source_id: str
    text_preview: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity_score: Optional[float] = None  # For semantic search results
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level based on similarity score"""
        if self.similarity_score is None:
            return ConfidenceLevel.HIGH  # Exact match
        elif self.similarity_score >= 0.95:
            return ConfidenceLevel.HIGH
        elif self.similarity_score >= 0.85:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "text_preview": self.text_preview,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score,
            "confidence_level": self.confidence_level.value
        }


@dataclass
class DeletionPreview:
    """Preview of what will be deleted before executing"""
    total_chunks: int
    total_documents: int
    affected_documents: List[DocumentInfo] = field(default_factory=list)
    affected_chunks: List[ChunkInfo] = field(default_factory=list)
    estimated_size_kb: float = 0.0
    filter_criteria: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_chunks": self.total_chunks,
            "total_documents": self.total_documents,
            "estimated_size_kb": self.estimated_size_kb,
            "filter_criteria": self.filter_criteria,
            "warnings": self.warnings,
            "affected_documents": [d.to_dict() for d in self.affected_documents],
            "affected_chunks": [c.to_dict() for c in self.affected_chunks]
        }


@dataclass
class SearchResult:
    """Result from a search operation"""
    query: str
    query_type: str  # "semantic", "metadata", "filename", etc.
    total_matches: int
    chunks: List[ChunkInfo] = field(default_factory=list)
    documents: List[DocumentInfo] = field(default_factory=list)
    search_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "query_type": self.query_type,
            "total_matches": self.total_matches,
            "search_time_seconds": self.search_time_seconds,
            "chunks": [c.to_dict() for c in self.chunks],
            "documents": [d.to_dict() for d in self.documents]
        }


@dataclass
class PaginatedResult:
    """Paginated list of results"""
    items: List[Any]
    page: int
    page_size: int
    total_items: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total pages"""
        return (self.total_items + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "items": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items],
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous
        }


# Export all models
__all__ = [
    'DeletionStatus',
    'ConfidenceLevel',
    'DeletionResult',
    'BatchDeletionResult',
    'DocumentInfo',
    'ChunkInfo',
    'DeletionPreview',
    'SearchResult',
    'PaginatedResult'
]

