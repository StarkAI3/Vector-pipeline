"""
Embedder for DMA Bot Data Management System
Generates embeddings using multilingual-e5-base model
"""
import torch
import numpy as np
from typing import List, Union, Dict, Any
from sentence_transformers import SentenceTransformer

from ..core.config import config
from ..utils.logger import get_embedder_logger

logger = get_embedder_logger()


class Embedder:
    """Generate embeddings for text chunks"""
    
    def __init__(self):
        """Initialize the embedding model"""
        self.model = None
        self.device = config.EMBEDDING_DEVICE
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL_NAME}")
            self.model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
            
            # Move to appropriate device
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to('cuda')
                logger.info("Model loaded on GPU")
            else:
                self.device = "cpu"
                logger.info("Model loaded on CPU")
            
            logger.info(f"Embedding model loaded successfully (dimension: {config.EMBEDDING_DIMENSION})")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embeddings
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(config.EMBEDDING_DIMENSION)
        
        try:
            # For multilingual-e5 models, prefix with "query: " or "passage: "
            # We use "passage: " for document content
            prefixed_text = f"passage: {text}"
            
            embedding = self.model.encode(
                prefixed_text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed text: {str(e)}")
            return np.zeros(config.EMBEDDING_DIMENSION)
    
    def embed_batch(self, texts: List[str], show_progress: bool = True) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar
            
        Returns:
            List of numpy arrays
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []
        
        try:
            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                logger.warning("No valid texts in batch")
                return [np.zeros(config.EMBEDDING_DIMENSION) for _ in texts]
            
            # Prefix all texts
            prefixed_texts = [f"passage: {text}" for text in valid_texts]
            
            logger.info(f"Embedding batch of {len(valid_texts)} texts...")
            
            embeddings = self.model.encode(
                prefixed_texts,
                batch_size=config.EMBEDDING_BATCH_SIZE,
                convert_to_numpy=True,
                show_progress_bar=show_progress,
                device=self.device
            )
            
            logger.info(f"Successfully embedded {len(embeddings)} texts")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to embed batch: {str(e)}")
            # Return zero vectors as fallback
            return [np.zeros(config.EMBEDDING_DIMENSION) for _ in texts]
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of chunk dictionaries
        
        Args:
            chunks: List of chunk dicts with 'text' and 'metadata' keys
            
        Returns:
            Same list with 'embedding' key added
        """
        if not chunks:
            logger.warning("Empty chunks list provided")
            return []
        
        try:
            # Extract texts
            texts = [chunk.get('text', '') for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.embed_batch(texts, show_progress=len(chunks) > 50)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk['embedding'] = embedding
            
            logger.info(f"Added embeddings to {len(chunks)} chunks")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to embed chunks: {str(e)}")
            return chunks
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query
        Uses "query: " prefix for better retrieval
        
        Args:
            query: Search query text
            
        Returns:
            Numpy array of embeddings
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for embedding")
            return np.zeros(config.EMBEDDING_DIMENSION)
        
        try:
            # For queries, use "query: " prefix
            prefixed_query = f"query: {query}"
            
            embedding = self.model.encode(
                prefixed_query,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            return np.zeros(config.EMBEDDING_DIMENSION)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        return config.EMBEDDING_DIMENSION
    
    def test_embedding(self) -> bool:
        """
        Test if the embedder is working correctly
        
        Returns:
            True if working
        """
        try:
            test_text = "This is a test sentence."
            embedding = self.embed_text(test_text)
            
            # Check embedding properties
            if embedding.shape[0] != config.EMBEDDING_DIMENSION:
                logger.error(f"Embedding dimension mismatch: {embedding.shape[0]} != {config.EMBEDDING_DIMENSION}")
                return False
            
            if np.all(embedding == 0):
                logger.error("Embedding is all zeros")
                return False
            
            logger.info("Embedder test passed")
            return True
            
        except Exception as e:
            logger.error(f"Embedder test failed: {str(e)}")
            return False
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score (0 to 1)
        """
        try:
            # Normalize embeddings
            norm1 = embedding1 / np.linalg.norm(embedding1)
            norm2 = embedding2 / np.linalg.norm(embedding2)
            
            # Calculate cosine similarity
            similarity = np.dot(norm1, norm2)
            
            # Ensure in range [0, 1]
            similarity = float(np.clip(similarity, 0, 1))
            
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0


# Singleton instance
_embedder_instance = None


def get_embedder() -> Embedder:
    """
    Get singleton embedder instance
    
    Returns:
        Embedder instance
    """
    global _embedder_instance
    
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    
    return _embedder_instance


# Export
__all__ = ['Embedder', 'get_embedder']

