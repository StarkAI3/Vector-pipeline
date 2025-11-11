"""
Configuration Management for DMA Bot Data Management System
Centralizes all configuration settings for the application
"""
import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class for all system settings"""
    
    # ============================================================================
    # PROJECT PATHS
    # ============================================================================
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    UPLOAD_DIR = BASE_DIR / "uploads" / "temp"
    PROCESSED_DIR = BASE_DIR / "uploads" / "processed"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Create directories if they don't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # ============================================================================
    # VECTOR DATABASE CONFIGURATION (MODULAR)
    # ============================================================================
    # Supports multiple vector databases: pinecone, qdrant, weaviate, chroma, milvus
    VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "pinecone").lower()
    
    # Generic configuration (applies to all vector databases)
    VECTOR_DB_API_KEY = os.getenv("VECTOR_DB_API_KEY", "")
    VECTOR_DB_INDEX_NAME = os.getenv("VECTOR_DB_INDEX_NAME", "dma-bot-index")
    VECTOR_DB_DIMENSION = int(os.getenv("VECTOR_DB_DIMENSION", "768"))
    VECTOR_DB_METRIC = os.getenv("VECTOR_DB_METRIC", "cosine")  # cosine, euclidean, dot_product
    VECTOR_DB_BATCH_SIZE = int(os.getenv("VECTOR_DB_BATCH_SIZE", "100"))
    VECTOR_DB_NAMESPACE = os.getenv("VECTOR_DB_NAMESPACE", "")
    
    # Deployment type: "cloud" or "local"
    VECTOR_DB_DEPLOYMENT = os.getenv("VECTOR_DB_DEPLOYMENT", "cloud").lower()
    
    # Cloud-specific settings (for Pinecone, Qdrant Cloud, Weaviate Cloud, etc.)
    VECTOR_DB_CLOUD_PROVIDER = os.getenv("VECTOR_DB_CLOUD_PROVIDER", "aws")  # aws, gcp, azure
    VECTOR_DB_REGION = os.getenv("VECTOR_DB_REGION", "us-east-1")
    
    # Local-specific settings (for self-hosted Qdrant, Weaviate, Chroma, Milvus)
    VECTOR_DB_HOST = os.getenv("VECTOR_DB_HOST", "localhost")
    VECTOR_DB_PORT = int(os.getenv("VECTOR_DB_PORT", "6333"))  # Default Qdrant port
    VECTOR_DB_GRPC_PORT = int(os.getenv("VECTOR_DB_GRPC_PORT", "6334"))  # For Milvus/Qdrant
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db_data")  # For local storage
    
    # Authentication (for databases that support multiple auth methods)
    VECTOR_DB_USERNAME = os.getenv("VECTOR_DB_USERNAME", "")
    VECTOR_DB_PASSWORD = os.getenv("VECTOR_DB_PASSWORD", "")
    VECTOR_DB_TOKEN = os.getenv("VECTOR_DB_TOKEN", "")
    
    # ============================================================================
    # BACKWARD COMPATIBILITY - PINECONE LEGACY CONFIG
    # ============================================================================
    # These are kept for backward compatibility with existing .env files
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "dma-bot-index")
    PINECONE_DIMENSION = 768  # multilingual-e5-base embedding dimension
    PINECONE_METRIC = "cosine"
    PINECONE_BATCH_SIZE = 100  # Batch size for upserts
    
    # ============================================================================
    # EMBEDDING MODEL CONFIGURATION
    # ============================================================================
    EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"  # Correct HuggingFace model name
    EMBEDDING_DIMENSION = 768
    EMBEDDING_DEVICE = "cpu"  # Change to "cuda" if GPU available
    EMBEDDING_BATCH_SIZE = 32
    
    # ============================================================================
    # LANGUAGE DETECTION
    # ============================================================================
    SUPPORTED_LANGUAGES = ["en", "mr", "hi"]  # English, Marathi, Hindi
    DEFAULT_LANGUAGE = "en"
    LANGUAGE_CONFIDENCE_THRESHOLD = 0.7
    
    # ============================================================================
    # CHUNKING CONFIGURATION
    # ============================================================================
    CHUNK_SIZES = {
        "small": 256,
        "medium": 512,
        "large": 768
    }
    DEFAULT_CHUNK_SIZE = "medium"
    CHUNK_OVERLAP = 50  # Token overlap between chunks
    MIN_CHUNK_SIZE = 50  # Minimum tokens for a valid chunk
    MAX_CHUNK_SIZE = 1000  # Maximum tokens for a chunk
    
    # ============================================================================
    # FILE UPLOAD SETTINGS
    # ============================================================================
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {
        "pdf": [".pdf"],
        "excel": [".xlsx", ".xls"],
        "csv": [".csv"],
        "json": [".json"],
        "text": [".txt", ".md"],
        "word": [".docx", ".doc"]
    }
    
    # ============================================================================
    # JOB MANAGEMENT
    # ============================================================================
    JOB_TIMEOUT = 3600  # 1 hour timeout for processing jobs
    JOB_RETRY_LIMIT = 3
    JOB_CLEANUP_AFTER_DAYS = 7  # Delete old job data after 7 days
    
    # ============================================================================
    # PROCESSING SETTINGS
    # ============================================================================
    # Quality thresholds
    MIN_QUALITY_SCORE = 0.5  # Chunks below this are rejected
    
    # Metadata defaults
    DEFAULT_IMPORTANCE = "normal"
    IMPORTANCE_LEVELS = ["critical", "high", "normal", "low"]
    
    # Categories
    CONTENT_CATEGORIES = [
        "government_officials",
        "services_schemes",
        "policies_regulations",
        "contact_information",
        "faq_help",
        "news_announcements",
        "forms_applications",
        "statistical_data",
        "general_information",
        "other"
    ]
    
    # ============================================================================
    # SPECIAL ELEMENTS EXTRACTION
    # ============================================================================
    # Regex patterns for special elements
    URL_PATTERN = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    
    # ============================================================================
    # WEB SCRAPING SETTINGS (For Phase 5)
    # ============================================================================
    SELENIUM_TIMEOUT = 30
    SELENIUM_IMPLICIT_WAIT = 10
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # ============================================================================
    # LOGGING CONFIGURATION
    # ============================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # ============================================================================
    # API SETTINGS
    # ============================================================================
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # ============================================================================
    # CONTENT TYPE MAPPINGS
    # ============================================================================
    CONTENT_STRUCTURE_TYPES = {
        "pdf": [
            "text_document",
            "document_with_tables",
            "mostly_tables",
            "faq_document",
            "scanned_document",
            "form_template",
            "complex_mix"
        ],
        "excel": [
            "standard_table",
            "faq_table",
            "multiple_sheets",
            "directory_list",
            "service_catalog",
            "text_in_cells",
            "complex_layout"
        ],
        "json": [
            "array_of_objects",
            "nested_objects",
            "web_scraping_output",
            "api_response"
        ],
        "text": [
            "narrative_document",
            "structured_markdown",
            "faq_format",
            "directory_format",
            "mixed_content"
        ],
        "url": [
            "article",
            "table_page",
            "directory_listing",
            "faq_page",
            "service_page",
            "interactive_page",
            "form_page",
            "complex_page"
        ]
    }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    @classmethod
    def get_chunk_size(cls, size_name: str = None) -> int:
        """Get chunk size by name"""
        size_name = size_name or cls.DEFAULT_CHUNK_SIZE
        return cls.CHUNK_SIZES.get(size_name, cls.CHUNK_SIZES["medium"])
    
    @classmethod
    def validate_file_extension(cls, filename: str, file_type: str) -> bool:
        """Validate if file extension matches the declared type"""
        ext = Path(filename).suffix.lower()
        allowed = cls.ALLOWED_EXTENSIONS.get(file_type, [])
        return ext in allowed
    
    @classmethod
    def get_file_type_from_extension(cls, filename: str) -> str:
        """Determine file type from extension"""
        ext = Path(filename).suffix.lower()
        for file_type, extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        return "unknown"
    
    @classmethod
    def is_valid_category(cls, category: str) -> bool:
        """Check if category is valid"""
        return category in cls.CONTENT_CATEGORIES
    
    @classmethod
    def is_valid_importance(cls, importance: str) -> bool:
        """Check if importance level is valid"""
        return importance in cls.IMPORTANCE_LEVELS
    
    # ============================================================================
    # VECTOR DATABASE HELPER METHODS
    # ============================================================================
    @classmethod
    def get_vector_db_type(cls) -> str:
        """Get the configured vector database type"""
        return cls.VECTOR_DB_TYPE
    
    @classmethod
    def get_vector_db_config(cls, key: str, default=None):
        """
        Get vector database configuration value.
        Handles backward compatibility with legacy Pinecone config.
        
        Args:
            key: Configuration key (e.g., 'api_key', 'index_name')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Map generic keys to specific config attributes
        key_mapping = {
            'api_key': 'VECTOR_DB_API_KEY',
            'index_name': 'VECTOR_DB_INDEX_NAME',
            'dimension': 'VECTOR_DB_DIMENSION',
            'metric': 'VECTOR_DB_METRIC',
            'batch_size': 'VECTOR_DB_BATCH_SIZE',
            'namespace': 'VECTOR_DB_NAMESPACE',
            'deployment': 'VECTOR_DB_DEPLOYMENT',
            'cloud_provider': 'VECTOR_DB_CLOUD_PROVIDER',
            'region': 'VECTOR_DB_REGION',
            'host': 'VECTOR_DB_HOST',
            'port': 'VECTOR_DB_PORT',
            'grpc_port': 'VECTOR_DB_GRPC_PORT',
            'path': 'VECTOR_DB_PATH',
            'username': 'VECTOR_DB_USERNAME',
            'password': 'VECTOR_DB_PASSWORD',
            'token': 'VECTOR_DB_TOKEN'
        }
        
        attr_name = key_mapping.get(key)
        if not attr_name:
            return default
        
        value = getattr(cls, attr_name, default)
        
        # Backward compatibility: Fall back to Pinecone config if generic config is empty
        if not value and cls.VECTOR_DB_TYPE == 'pinecone':
            pinecone_fallback = {
                'api_key': cls.PINECONE_API_KEY,
                'index_name': cls.PINECONE_INDEX_NAME,
                'dimension': cls.PINECONE_DIMENSION,
                'metric': cls.PINECONE_METRIC,
                'batch_size': cls.PINECONE_BATCH_SIZE,
                'region': cls.PINECONE_ENVIRONMENT
            }
            value = pinecone_fallback.get(key, default)
        
        return value if value else default
    
    @classmethod
    def is_cloud_deployment(cls) -> bool:
        """Check if vector database is deployed in cloud"""
        return cls.VECTOR_DB_DEPLOYMENT == "cloud"
    
    @classmethod
    def is_local_deployment(cls) -> bool:
        """Check if vector database is deployed locally"""
        return cls.VECTOR_DB_DEPLOYMENT == "local"
    
    @classmethod
    def get_vector_db_connection_string(cls) -> str:
        """
        Get connection string for local vector databases.
        
        Returns:
            Connection string (e.g., "http://localhost:6333" for Qdrant)
        """
        if cls.is_cloud_deployment():
            return ""
        
        host = cls.VECTOR_DB_HOST
        port = cls.VECTOR_DB_PORT
        
        # Handle different protocols
        if cls.VECTOR_DB_TYPE in ['qdrant', 'weaviate']:
            return f"http://{host}:{port}"
        elif cls.VECTOR_DB_TYPE == 'milvus':
            return f"{host}:{port}"
        elif cls.VECTOR_DB_TYPE == 'chroma':
            return cls.VECTOR_DB_PATH
        
        return f"http://{host}:{port}"

# Create a singleton instance
config = Config()

# Export for easy importing
__all__ = ['Config', 'config']

