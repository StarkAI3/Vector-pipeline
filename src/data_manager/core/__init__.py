"""
Core Module
Configuration and orchestration
"""
from .config import Config, config

# Note: Orchestrator is not imported here to avoid circular imports
# Import directly: from data_manager.core.orchestrator import ProcessingOrchestrator

__all__ = ['Config', 'config']

