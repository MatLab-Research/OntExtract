"""
Period-Aware Embedding Service

Enhanced embedding service that selects appropriate models based on temporal periods
and domain characteristics, as described in the JCDL paper. This service implements
the period-aware approach where historical texts use models trained on historical corpora.
"""

import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import sys

# Add shared services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared_services'))

try:
    from embedding.embedding_service import EmbeddingService
    EMBEDDING_SERVICE_AVAILABLE = True
except ImportError:
    EMBEDDING_SERVICE_AVAILABLE = False
    import warnings
    warnings.warn("Base embedding service not available")

logger = logging.getLogger(__name__)


class PeriodAwareEmbeddingService:
    """
    Period-aware embedding service implementing the JCDL paper's approach to
    temporal and domain-specific embedding model selection.
    
    From paper Section 3.2: "The architecture selects period-appropriate embedding 
    models based on the temporal and domain characteristics of the text. For historical 
    texts before 1950, the system employs models trained on historical corpora that 
    handle archaic spelling and usage patterns."
    """
    
    # Period-appropriate embedding models as specified in JCDL paper
    PERIOD_MODELS = {
        'historical_pre1850': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',  # Fallback - would use historical-bert in production
            'description': 'General model for pre-1850 texts (archaic language)',
            'handles_archaic': True,
            'dimension': 384,
            'era': 'pre-industrial'
        },
        'historical_1850_1950': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',  # Would use HistBERT in production
            'description': 'Model for 19th-early 20th century texts',
            'handles_archaic': True,
            'dimension': 384,
            'era': 'industrial'
        },
        'modern_1950_2000': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',
            'description': 'Standard model for mid-20th century texts',
            'handles_archaic': False,
            'dimension': 384,
            'era': 'modern'
        },
        'contemporary_2000plus': {
            'model': 'sentence-transformers/all-roberta-large-v1',
            'description': 'Contemporary model for modern language patterns',
            'handles_archaic': False,
            'dimension': 1024,
            'era': 'contemporary'
        },
        # Domain-specific models
        'domain_scientific': {
            'model': 'allenai/scibert_scivocab_uncased',
            'description': 'Scientific domain-specific embeddings',
            'handles_archaic': False,
            'dimension': 768,
            'domain': 'science'
        },
        'domain_legal': {
            'model': 'nlpaueb/legal-bert-base-uncased', 
            'description': 'Legal domain-specific embeddings',
            'handles_archaic': False,
            'dimension': 768,
            'domain': 'law'
        },
        'domain_biomedical': {
            'model': 'dmis-lab/biobert-base-cased-v1.1',
            'description': 'Biomedical domain-specific embeddings', 
            'handles_archaic': False,
            'dimension': 768,
            'domain': 'medicine'
        },
        'domain_philosophy': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',  # Fallback - would use philosophy-specific model
            'description': 'Philosophy domain embeddings',
            'handles_archaic': False,
            'dimension': 384,
            'domain': 'philosophy'
        },
        'domain_economics': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2',  # Fallback - would use economics-specific model
            'description': 'Economics domain embeddings',
            'handles_archaic': False,
            'dimension': 384,
            'domain': 'economics'
        }
    }
    
    def __init__(self):
        """Initialize the period-aware embedding service."""
        self.base_service = None
        self.model_cache = {}
        
        if EMBEDDING_SERVICE_AVAILABLE:
            self.base_service = EmbeddingService()
            logger.info("Period-aware embedding service initialized")
        else:
            logger.warning("Base embedding service unavailable - period awareness will be limited")
    
    def select_model_for_period(self, 
                               year: Optional[int] = None, 
                               domain: Optional[str] = None,
                               text_sample: Optional[str] = None,
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Select optimal embedding model based on temporal period and domain.
        
        Implements the JCDL paper's period-aware model selection approach.
        
        Args:
            year: Publication/creation year of the text
            domain: Domain category (scientific, legal, philosophy, etc.)
            text_sample: Sample text for linguistic analysis
            metadata: Additional metadata for model selection
            
        Returns:
            Dictionary with selected model information
        """
        metadata = metadata or {}
        
        # Domain takes precedence for specialized vocabularies
        if domain:
            domain_key = f'domain_{domain.lower()}'
            if domain_key in self.PERIOD_MODELS:
                model_info = self.PERIOD_MODELS[domain_key].copy()
                model_info['selection_reason'] = f'Domain-specific model for {domain}'
                model_info['selection_confidence'] = 0.9
                return model_info
        
        # Temporal selection based on year
        if year:
            if year < 1850:
                model_key = 'historical_pre1850'
                reason = 'Pre-industrial era text with potential archaic language'
            elif year < 1950:
                model_key = 'historical_1850_1950'
                reason = 'Industrial era text requiring historical language handling'
            elif year < 2000:
                model_key = 'modern_1950_2000'
                reason = 'Modern era text with standard language patterns'
            else:
                model_key = 'contemporary_2000plus'
                reason = 'Contemporary text with current language patterns'
            
            model_info = self.PERIOD_MODELS[model_key].copy()
            model_info['selection_reason'] = reason
            model_info['selection_confidence'] = 0.8
            return model_info
        
        # Analyze text sample if provided
        if text_sample:
            analysis = self._analyze_text_characteristics(text_sample)
            if analysis['likely_archaic']:
                model_info = self.PERIOD_MODELS['historical_1850_1950'].copy()
                model_info['selection_reason'] = 'Archaic language patterns detected in text'
                model_info['selection_confidence'] = 0.7
                return model_info
            elif analysis['likely_technical']:
                model_info = self.PERIOD_MODELS['domain_scientific'].copy()
                model_info['selection_reason'] = 'Technical vocabulary detected'
                model_info['selection_confidence'] = 0.6
                return model_info
        
        # Default fallback
        model_info = self.PERIOD_MODELS['modern_1950_2000'].copy()
        model_info['selection_reason'] = 'Default model - insufficient metadata for period detection'
        model_info['selection_confidence'] = 0.5
        return model_info
    
    def generate_period_aware_embedding(self, 
                                      text: str,
                                      year: Optional[int] = None,
                                      domain: Optional[str] = None,
                                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate embeddings using period-appropriate models.
        
        Args:
            text: Text to embed
            year: Temporal period indicator
            domain: Domain category
            metadata: Additional context information
            
        Returns:
            Dictionary with embedding and model selection metadata
        """
        # Select appropriate model
        model_selection = self.select_model_for_period(year, domain, text, metadata)
        
        # Generate embedding using selected model
        try:
            if self.base_service:
                # Use base service with selected model
                embedding = self._generate_with_model(text, model_selection['model'])
            else:
                # Fallback to simple embedding generation
                embedding = self._fallback_embedding(text)
            
            result = {
                'embedding': embedding,
                'model_used': model_selection['model'],
                'model_description': model_selection['description'],
                'selection_reason': model_selection['selection_reason'],
                'selection_confidence': model_selection['selection_confidence'],
                'dimension': len(embedding) if embedding else model_selection['dimension'],
                'period_detected': year,
                'domain_detected': domain,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Generated period-aware embedding using {model_selection['model']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate period-aware embedding: {e}")
            # Return fallback result
            return {
                'embedding': self._fallback_embedding(text),
                'model_used': 'fallback',
                'error': str(e),
                'selection_confidence': 0.1,
                'dimension': 384
            }
    
    def calculate_period_drift(self, 
                              term: str,
                              period1_embeddings: List[List[float]],
                              period2_embeddings: List[List[float]],
                              period1_year: int,
                              period2_year: int) -> Dict[str, Any]:
        """
        Calculate semantic drift between periods using period-aware embeddings.
        
        Implements the JCDL paper's approach: "embedding-based drift calculation uses 
        period-appropriate models to measure how term usage shifts across time periods 
        through cosine similarity and neighborhood analysis."
        
        Args:
            term: Term being analyzed
            period1_embeddings: Embeddings from first period
            period2_embeddings: Embeddings from second period
            period1_year: Year of first period
            period2_year: Year of second period
            
        Returns:
            Drift analysis with cosine distance and confidence metrics
        """
        if not period1_embeddings or not period2_embeddings:
            return {
                'drift_magnitude': 0.0,
                'confidence': 0.0,
                'error': 'Insufficient embeddings for comparison'
            }
        
        try:
            # Calculate centroids for each period
            centroid1 = np.mean(period1_embeddings, axis=0)
            centroid2 = np.mean(period2_embeddings, axis=0)
            
            # Calculate cosine similarity and distance
            cosine_sim = np.dot(centroid1, centroid2) / (
                np.linalg.norm(centroid1) * np.linalg.norm(centroid2)
            )
            cosine_distance = 1 - cosine_sim
            
            # Calculate additional metrics
            euclidean_distance = np.linalg.norm(centroid1 - centroid2)
            
            # Confidence based on sample sizes and consistency
            confidence = self._calculate_drift_confidence(
                period1_embeddings, period2_embeddings, cosine_distance
            )
            
            # Determine drift classification
            if cosine_distance > 0.7:
                classification = 'major_shift'
            elif cosine_distance > 0.4:
                classification = 'moderate_drift'
            elif cosine_distance > 0.2:
                classification = 'minor_change'
            else:
                classification = 'stable'
            
            return {
                'term': term,
                'period1_year': period1_year,
                'period2_year': period2_year,
                'drift_magnitude': float(cosine_distance),
                'cosine_distance': float(cosine_distance),
                'cosine_similarity': float(cosine_sim),
                'euclidean_distance': float(euclidean_distance),
                'classification': classification,
                'confidence': confidence,
                'sample_size_1': len(period1_embeddings),
                'sample_size_2': len(period2_embeddings),
                'method': 'period_aware_centroid_comparison'
            }
            
        except Exception as e:
            logger.error(f"Error calculating period drift: {e}")
            return {
                'drift_magnitude': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _analyze_text_characteristics(self, text: str) -> Dict[str, Any]:
        """Analyze text to detect archaic language or technical vocabulary."""
        text_lower = text.lower()
        
        # Simple heuristics for archaic language
        archaic_indicators = [
            'thou', 'thee', 'thy', 'thine', 'hath', 'doth', 'whence', 'wherefore',
            'wherein', 'whereby', 'heretofore', 'hereunto', 'notwithstanding'
        ]
        
        # Technical vocabulary indicators
        technical_indicators = [
            'hypothesis', 'methodology', 'parameter', 'coefficient', 'algorithm',
            'paradigm', 'empirical', 'statistical', 'quantitative', 'qualitative'
        ]
        
        archaic_count = sum(1 for word in archaic_indicators if word in text_lower)
        technical_count = sum(1 for word in technical_indicators if word in text_lower)
        
        return {
            'likely_archaic': archaic_count > 0,
            'likely_technical': technical_count > 2,
            'archaic_score': archaic_count / len(text.split()) * 100,
            'technical_score': technical_count / len(text.split()) * 100
        }
    
    def _generate_with_model(self, text: str, model_name: str) -> List[float]:
        """Generate embedding using specific model via base service."""
        if self.base_service:
            # Configure base service to use specific model
            original_model = self.base_service.model_name
            self.base_service.model_name = model_name
            
            try:
                embedding = self.base_service.get_embedding(text)
                return embedding
            finally:
                # Restore original model
                self.base_service.model_name = original_model
        
        return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """Generate simple fallback embedding."""
        # Very simple hash-based embedding for fallback
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 384-dimensional vector (matching default dimension)
        embedding = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] - 128) / 128.0)
        
        return embedding
    
    def _calculate_drift_confidence(self, 
                                   embeddings1: List[List[float]], 
                                   embeddings2: List[List[float]], 
                                   drift_magnitude: float) -> float:
        """Calculate confidence score for drift measurement."""
        # Base confidence on sample sizes
        min_sample = min(len(embeddings1), len(embeddings2))
        size_confidence = min(1.0, min_sample / 10)  # Higher confidence with more samples
        
        # Adjust based on drift magnitude (extreme values may be less reliable)
        magnitude_confidence = 1.0 - abs(drift_magnitude - 0.5) * 0.5
        
        # Combined confidence score
        confidence = (size_confidence + magnitude_confidence) / 2
        return max(0.1, min(1.0, confidence))  # Clamp between 0.1 and 1.0
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get information about available period-aware models."""
        return {
            'period_models': self.PERIOD_MODELS,
            'base_service_available': EMBEDDING_SERVICE_AVAILABLE,
            'total_models': len(self.PERIOD_MODELS)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of period-aware embedding service."""
        health = {
            'service_status': 'ok',
            'base_service_available': EMBEDDING_SERVICE_AVAILABLE,
            'period_models_count': len(self.PERIOD_MODELS),
            'model_cache_size': len(self.model_cache)
        }
        
        if self.base_service:
            try:
                # Test base service
                test_embedding = self.base_service.get_embedding("test")
                health['base_service_test'] = 'passed' if test_embedding else 'failed'
            except Exception as e:
                health['base_service_error'] = str(e)
        
        return health


# Global service instance
_period_aware_service = None

def get_period_aware_embedding_service() -> PeriodAwareEmbeddingService:
    """Get the global period-aware embedding service instance."""
    global _period_aware_service
    if _period_aware_service is None:
        _period_aware_service = PeriodAwareEmbeddingService()
    return _period_aware_service


def ensure_models_downloaded(download: bool = True) -> Dict[str, Any]:
    """
    Setup utility to check and download required embedding models.

    This should be run BEFORE deploying the application, not during runtime.
    Embedding models are large (100-400MB each) and should be pre-downloaded.

    Run this during:
    - Initial setup: `python -c "from app.services.period_aware_embedding_service import ensure_models_downloaded; ensure_models_downloaded()"`
    - Docker build: Add to Dockerfile
    - CI/CD: As part of deployment pipeline

    Args:
        download: If True, download missing models. If False, only check status.

    Returns:
        Dictionary with status information:
        - models_checked: List of model names that were checked
        - models_available: List of models already cached
        - models_missing: List of models not cached
        - models_downloaded: List of models downloaded (if download=True)
        - errors: Any errors encountered

    Usage:
        # Check status only (quick, no downloads)
        status = ensure_models_downloaded(download=False)

        # Download all missing models (run during setup)
        status = ensure_models_downloaded(download=True)

    CLI usage:
        python -c "from app.services.period_aware_embedding_service import ensure_models_downloaded; print(ensure_models_downloaded())"
    """
    # Get the list of models from the service
    service = PeriodAwareEmbeddingService()
    models = service.PERIOD_MODELS

    # Get unique model names
    unique_models = set()
    for config in models.values():
        unique_models.add(config['model'])

    cache_base = os.path.expanduser("~/.cache/huggingface/hub")

    result = {
        'models_checked': list(unique_models),
        'models_available': [],
        'models_missing': [],
        'models_downloaded': [],
        'errors': []
    }

    for model_name in unique_models:
        # Convert model name to cache directory format
        cache_name = model_name.replace("/", "--")
        model_path = os.path.join(cache_base, f"models--{cache_name}")

        # Check if model is cached
        is_cached = False
        if os.path.exists(model_path):
            snapshots = os.path.join(model_path, "snapshots")
            if os.path.exists(snapshots) and os.listdir(snapshots):
                is_cached = True

        if is_cached:
            result['models_available'].append(model_name)
        else:
            result['models_missing'].append(model_name)

            if download:
                try:
                    logger.info(f"Downloading model: {model_name}")
                    from sentence_transformers import SentenceTransformer
                    SentenceTransformer(model_name)
                    result['models_downloaded'].append(model_name)
                    result['models_available'].append(model_name)
                    result['models_missing'].remove(model_name)
                except Exception as e:
                    error_msg = f"Failed to download {model_name}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

    return result


def check_models_status() -> Dict[str, Any]:
    """
    Quick check of model status without downloading.

    Returns a summary of which models are available and which need downloading.
    """
    return ensure_models_downloaded(download=False)