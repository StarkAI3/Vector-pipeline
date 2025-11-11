"""
Logging Configuration for DMA Bot Data Management System
Provides comprehensive logging for all components
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from ..core.config import config


class LoggerSetup:
    """Setup and manage logging for the application"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger with the specified name
        
        Args:
            name: Logger name (typically module name)
            log_file: Optional specific log file name
            
        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatters
        formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_filename = log_file or f"{name.replace('.', '_')}.log"
        log_path = config.LOGS_DIR / log_filename
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.MAX_LOG_SIZE,
            backupCount=config.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Store logger
        cls._loggers[name] = logger
        
        return logger
    
    @classmethod
    def setup_component_logger(cls, component_name: str) -> logging.Logger:
        """
        Setup logger for a specific component with its own log file
        
        Args:
            component_name: Name of the component (e.g., 'extractor', 'processor')
            
        Returns:
            Configured logger
        """
        return cls.get_logger(f"data_manager.{component_name}")


# Pre-configured loggers for common components
def get_extractor_logger() -> logging.Logger:
    """Logger for extraction components"""
    return LoggerSetup.get_logger("data_manager.extractor")


def get_processor_logger() -> logging.Logger:
    """Logger for processing components"""
    return LoggerSetup.get_logger("data_manager.processor")


def get_embedder_logger() -> logging.Logger:
    """Logger for embedding components"""
    return LoggerSetup.get_logger("data_manager.embedder")


def get_database_logger() -> logging.Logger:
    """Logger for database operations"""
    return LoggerSetup.get_logger("data_manager.database")


def get_api_logger() -> logging.Logger:
    """Logger for API operations"""
    return LoggerSetup.get_logger("data_manager.api")


def get_job_logger() -> logging.Logger:
    """Logger for job management"""
    return LoggerSetup.get_logger("data_manager.job")


def get_worker_logger() -> logging.Logger:
    """Logger for background workers"""
    return LoggerSetup.get_logger("data_manager.worker")


# Convenience function for general use
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger by name (convenience function)
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return LoggerSetup.get_logger(name)


# Export
__all__ = [
    'LoggerSetup',
    'get_logger',
    'get_extractor_logger',
    'get_processor_logger',
    'get_embedder_logger',
    'get_database_logger',
    'get_api_logger',
    'get_job_logger',
    'get_worker_logger'
]

