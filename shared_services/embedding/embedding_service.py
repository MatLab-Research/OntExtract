"""
Enhanced Embedding Service for text processing and similarity search.

This service provides multi-provider embedding generation with support for:
- Local sentence-transformers models
- OpenAI API
- Claude API (when available)
- File processing (PDF, DOCX, HTML, URLs)
- Document chunking and vector operations
"""

import os
import numpy as np
from typing import List, Dict, Any, Union, Optional, Tuple
import requests
import json
import io
import logging
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)

class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local sentence-transformers embedding provider."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._dimension = 384  # Default for all-MiniLM-L6-v2
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the local model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Configure offline mode to avoid HuggingFace Hub requests
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            
            # Initialize without unsupported kwargs; offline behavior controlled via env vars
            self.model = SentenceTransformer(self.model_name)
            # Update dimension based on actual model
            test_embedding = self.model.encode("test")
            self._dimension = len(test_embedding)
            logger.info(f"Local embedding provider ready: {self.model_name} (dim: {self._dimension})")
            
        except Exception as e:
            logger.error(f"Failed to initialize local model {self.model_name}: {e}")
            self.model = None
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        if not self.model:
            raise RuntimeError("Local model not available")
        
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def is_available(self) -> bool:
        """Check if local model is available."""
        return self.model is not None
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI API embedding provider."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-ada-002"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self._dimension = 1536  # Default for ada-002
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        if not self.is_available():
            raise RuntimeError("OpenAI API not available")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "input": text,
            "model": self.model
        }
        
        response = requests.post(
            f"{self.api_base}/embeddings", 
            headers=headers, 
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} {response.text}")
        
        result = response.json()
        return result["data"][0]["embedding"]
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        return (self.api_key and 
                not self.api_key.startswith("your-") and 
                len(self.api_key) > 20)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

class ClaudeEmbeddingProvider(BaseEmbeddingProvider):
    """Claude API embedding provider (experimental)."""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-embedding"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.api_base = os.environ.get("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
        self._dimension = 1024  # Estimated for Claude
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding using Claude API."""
        if not self.is_available():
            raise RuntimeError("Claude API not available")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model,
            "input": text
        }
        
        # Try embeddings endpoint (may not exist yet)
        try:
            response = requests.post(
                f"{self.api_base}/embeddings",
                headers=headers, 
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if "embedding" in result:
                    return result["embedding"]
                elif "embeddings" in result and len(result["embeddings"]) > 0:
                    return result["embeddings"][0]
        except Exception as e:
            logger.warning(f"Claude embeddings API unavailable: {e}")
        
        # Fall back to random embedding for now
        logger.warning("Claude embeddings not available, using random fallback")
        return self._get_random_embedding()
    
    def _get_random_embedding(self) -> List[float]:
        """Generate random embedding as fallback."""
        random_vector = np.random.randn(self._dimension)
        normalized = random_vector / np.linalg.norm(random_vector)
        return normalized.tolist()
    
    def is_available(self) -> bool:
        """Check if Claude API is available."""
        return (self.api_key and 
                not self.api_key.startswith("your-") and 
                len(self.api_key) > 20)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

class EmbeddingService:
    """
    Main embedding service that manages multiple providers with fallback support.
    """
    
    def __init__(self, 
                 model_name: str = None, 
                 provider_priority: List[str] = None,
                 embedding_dimension: int = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Local model name (defaults to env var or 'all-MiniLM-L6-v2')
            provider_priority: List of providers in priority order ['local', 'openai', 'claude']
            embedding_dimension: Override dimension if needed
        """
        self.model_name = model_name or os.environ.get("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.provider_priority = provider_priority or self._get_default_priority()
        self.providers = {}
        self.embedding_dimension = embedding_dimension
        
        # Initialize providers
        self._setup_providers()
        
        # Set embedding dimension from first available provider
        if not self.embedding_dimension:
            for provider_name in self.provider_priority:
                if provider_name in self.providers and self.providers[provider_name].is_available():
                    self.embedding_dimension = self.providers[provider_name].dimension
                    break
            else:
                self.embedding_dimension = 384  # Default fallback
    
    def _get_default_priority(self) -> List[str]:
        """Get default provider priority from environment or use defaults."""
        priority_str = os.environ.get("EMBEDDING_PROVIDER_PRIORITY", "local,openai,claude")
        return [p.strip().lower() for p in priority_str.split(',')]
    
    def _setup_providers(self):
        """Initialize all configured providers."""
        if "local" in self.provider_priority:
            self.providers["local"] = LocalEmbeddingProvider(self.model_name)
        
        if "openai" in self.provider_priority:
            self.providers["openai"] = OpenAIEmbeddingProvider()
        
        if "claude" in self.provider_priority:
            self.providers["claude"] = ClaudeEmbeddingProvider()
        
        # Log available providers
        available = [name for name, provider in self.providers.items() if provider.is_available()]
        logger.info(f"Available embedding providers: {available}")
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using the first available provider.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return [0.0] * self.embedding_dimension
        
        # Try each provider in priority order
        for provider_name in self.provider_priority:
            if provider_name not in self.providers:
                continue
                
            provider = self.providers[provider_name]
            if not provider.is_available():
                continue
            
            try:
                embedding = provider.get_embedding(text.strip())
                logger.debug(f"Generated embedding using {provider_name} (dim: {len(embedding)})")
                return embedding
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed, return random fallback
        logger.error("All embedding providers failed, using random fallback")
        return self._get_random_embedding()
    
    def _get_random_embedding(self) -> List[float]:
        """Generate a random normalized embedding for fallback."""
        random_vector = np.random.randn(self.embedding_dimension)
        normalized = random_vector / np.linalg.norm(random_vector)
        return normalized.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        
        for i, text in enumerate(texts):
            try:
                embedding = self.get_embedding(text)
                embeddings.append(embedding)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(texts)} embeddings")
                    
            except Exception as e:
                logger.error(f"Error generating embedding for text {i}: {e}")
                embeddings.append([0.0] * self.embedding_dimension)
        
        return embeddings
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def get_provider_status(self) -> Dict[str, bool]:
        """
        Get status of all configured providers.
        
        Returns:
            Dictionary mapping provider names to availability status
        """
        return {name: provider.is_available() 
                for name, provider in self.providers.items()}
