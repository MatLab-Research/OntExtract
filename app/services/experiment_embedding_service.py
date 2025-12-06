"""
Experiment Embedding Service

Simple embedding service for experiment processing that handles both local
and OpenAI embeddings for the experiment-centric processing architecture.
"""

import os

# Set offline mode for HuggingFace Hub BEFORE any imports
# This prevents network calls when models are already cached locally
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ExperimentEmbeddingService:
    """Simple embedding service for experiment processing"""

    def __init__(self):
        self.openai_client = None
        self.local_model = None
        self._model_cache = {}  # Cache for period-specific models

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

        # Initialize local model (offline mode set at module level)
        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._model_cache['all-MiniLM-L6-v2'] = self.local_model
            logger.info("Local sentence transformer model loaded (offline mode)")
        except ImportError:
            logger.warning("sentence-transformers package not available")

    def generate_embeddings(self, text: str, method: str = 'local', year: int = None) -> Dict[str, Any]:
        """
        Generate embeddings for the given text using the specified method.

        Args:
            text: Text to embed
            method: 'local', 'openai', or 'period_aware'
            year: Optional document year for period-aware embedding

        Returns:
            Dict containing vector, dimensions, and metadata
        """
        if method == 'local':
            return self._generate_local_embeddings(text)
        elif method == 'openai':
            return self._generate_openai_embeddings(text)
        elif method == 'period_aware':
            return self._generate_period_aware_embeddings(text, year)
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

    def _generate_period_aware_embeddings(self, text: str, year: int = None) -> Dict[str, Any]:
        """
        Generate period-aware embeddings using period-specific model selection.

        Uses PeriodAwareEmbeddingService to select the appropriate model based on
        the document's historical period:
        - Pre-1850: Historical model for archaic language (all-mpnet-base-v2, 768 dims)
        - 1850-1950: Industrial era model (all-mpnet-base-v2, 768 dims)
        - 1950-2000: Modern model (all-MiniLM-L6-v2, 384 dims)
        - 2000+: Contemporary model (all-mpnet-base-v2, 768 dims)

        Models are cached after first load for efficient subsequent embeddings.
        """
        try:
            from app.services.period_aware_embedding_service import get_period_aware_embedding_service

            # Get the period-aware service for model selection
            period_service = get_period_aware_embedding_service()

            # Select the appropriate model based on year
            model_info = period_service.select_model_for_period(year=year)

            # Determine period category
            if year:
                if year < 1850:
                    period_category = 'historical_pre1850'
                elif year < 1950:
                    period_category = 'historical_1850_1950'
                elif year < 2000:
                    period_category = 'modern_1950_2000'
                else:
                    period_category = 'contemporary_2000plus'
            else:
                period_category = 'unknown'

            # Get the selected model name and info
            selected_model = model_info.get('model', 'sentence-transformers/all-MiniLM-L6-v2')
            model_description = model_info.get('description', '')
            expected_dimension = model_info.get('dimension', 384)
            handles_archaic = model_info.get('handles_archaic', False)
            era = model_info.get('era', 'unknown')

            # Try to use the period-specific model
            try:
                from sentence_transformers import SentenceTransformer

                # Check if we need a different model than the default
                model_name_short = selected_model.replace('sentence-transformers/', '')

                if model_name_short != 'all-MiniLM-L6-v2' and self.local_model:
                    # Check if model is already cached
                    if model_name_short in self._model_cache:
                        period_model = self._model_cache[model_name_short]
                        logger.debug(f"Using cached model: {model_name_short}")
                    else:
                        # Load and cache the period-specific model
                        logger.info(f"Loading and caching period-specific model: {selected_model}")
                        period_model = SentenceTransformer(selected_model)
                        self._model_cache[model_name_short] = period_model
                    embedding = period_model.encode(text)
                    actual_model = model_name_short
                else:
                    # Use the default local model
                    if not self.local_model:
                        raise RuntimeError("Local embedding model not available")
                    embedding = self.local_model.encode(text)
                    actual_model = 'all-MiniLM-L6-v2'

                vector = embedding.tolist()

                return {
                    'vector': vector,
                    'dimensions': len(vector),
                    'method': 'period_aware',
                    'model': actual_model,
                    'model_full': selected_model,
                    'model_description': model_description,
                    'expected_dimension': expected_dimension,
                    'handles_archaic': handles_archaic,
                    'era': era,
                    'period_category': period_category,
                    'document_year': year,
                    'selection_reason': model_info.get('selection_reason', ''),
                    'selection_confidence': model_info.get('selection_confidence', 0.5),
                    'text_length': len(text),
                    'success': True
                }

            except Exception as model_error:
                # Fall back to local model if period-specific model fails
                logger.warning(f"Could not load period-specific model {selected_model}: {model_error}")
                logger.info("Falling back to default local model")

                if not self.local_model:
                    raise RuntimeError("Local embedding model not available for period-aware embeddings")

                embedding = self.local_model.encode(text)
                vector = embedding.tolist()

                return {
                    'vector': vector,
                    'dimensions': len(vector),
                    'method': 'period_aware',
                    'model': 'all-MiniLM-L6-v2',
                    'model_full': 'sentence-transformers/all-MiniLM-L6-v2',
                    'model_description': f'Fallback model (intended: {model_description})',
                    'intended_model': selected_model,
                    'expected_dimension': expected_dimension,
                    'handles_archaic': handles_archaic,
                    'era': era,
                    'period_category': period_category,
                    'document_year': year,
                    'selection_reason': model_info.get('selection_reason', '') + ' (using fallback)',
                    'selection_confidence': model_info.get('selection_confidence', 0.5) * 0.8,  # Lower confidence for fallback
                    'text_length': len(text),
                    'fallback_used': True,
                    'success': True
                }

        except Exception as e:
            logger.error(f"Error generating period-aware embeddings: {str(e)}")
            raise

    def is_method_available(self, method: str) -> bool:
        """Check if a specific embedding method is available"""
        if method == 'local':
            return self.local_model is not None
        elif method == 'openai':
            return self.openai_client is not None
        elif method == 'period_aware':
            # Period-aware uses local model under the hood
            return self.local_model is not None
        else:
            return False

    def get_available_methods(self) -> List[str]:
        """Get list of available embedding methods"""
        methods = []
        if self.local_model:
            methods.append('local')
            methods.append('period_aware')  # Period-aware uses local model
        if self.openai_client:
            methods.append('openai')
        return methods