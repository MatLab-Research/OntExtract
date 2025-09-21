"""
Experiment Embedding Service

Simple embedding service for experiment processing that handles both local
and OpenAI embeddings for the experiment-centric processing architecture.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ExperimentEmbeddingService:
    """Simple embedding service for experiment processing"""

    def __init__(self):
        self.openai_client = None
        self.local_model = None

        # Initialize OpenAI client if API key is available
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found")
        except ImportError:
            logger.warning("OpenAI package not available")

        # Initialize local model
        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Local sentence transformer model loaded")
        except ImportError:
            logger.warning("sentence-transformers package not available")

    def generate_embeddings(self, text: str, method: str = 'local') -> Dict[str, Any]:
        """
        Generate embeddings for the given text using the specified method.

        Args:
            text: Text to embed
            method: 'local' or 'openai'

        Returns:
            Dict containing vector, dimensions, and metadata
        """
        if method == 'local':
            return self._generate_local_embeddings(text)
        elif method == 'openai':
            return self._generate_openai_embeddings(text)
        else:
            raise ValueError(f"Unknown embedding method: {method}")

    def _generate_local_embeddings(self, text: str) -> Dict[str, Any]:
        """Generate embeddings using local sentence transformer model"""
        if not self.local_model:
            raise RuntimeError("Local embedding model not available")

        try:
            # Generate embedding
            embedding = self.local_model.encode(text)

            # Convert to list for JSON serialization
            vector = embedding.tolist()

            return {
                'vector': vector,
                'dimensions': len(vector),
                'method': 'local',
                'model': 'all-MiniLM-L6-v2',
                'text_length': len(text),
                'success': True
            }

        except Exception as e:
            logger.error(f"Error generating local embeddings: {str(e)}")
            raise

    def _generate_openai_embeddings(self, text: str) -> Dict[str, Any]:
        """Generate embeddings using OpenAI API"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available - check API key")

        try:
            # Use OpenAI's text-embedding-3-large model
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                encoding_format="float"
            )

            # Extract the embedding vector
            embedding = response.data[0].embedding

            return {
                'vector': embedding,
                'dimensions': len(embedding),
                'method': 'openai',
                'model': 'text-embedding-3-large',
                'text_length': len(text),
                'tokens_used': response.usage.total_tokens,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {str(e)}")
            raise

    def is_method_available(self, method: str) -> bool:
        """Check if a specific embedding method is available"""
        if method == 'local':
            return self.local_model is not None
        elif method == 'openai':
            return self.openai_client is not None
        else:
            return False

    def get_available_methods(self) -> List[str]:
        """Get list of available embedding methods"""
        methods = []
        if self.local_model:
            methods.append('local')
        if self.openai_client:
            methods.append('openai')
        return methods