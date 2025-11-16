"""
Utility Functions for Integrated LangExtract Service

Handles serialization, temp file management, and fallback responses.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)


class LangExtractUtils:
    """Utility functions for LangExtract service"""

    def __init__(self):
        """Initialize utilities with temp directory"""
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'langextract_debug')
        os.makedirs(self.temp_dir, exist_ok=True)

    def save_temp_results(self, document_id: int, stage: str, results: Dict[str, Any]) -> str:
        """Save intermediate results to temp file for debugging"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"doc_{document_id}_{stage}_{timestamp}.json"
            filepath = os.path.join(self.temp_dir, filename)

            # Make results serializable
            serializable_results = self.make_serializable(results)

            with open(filepath, 'w') as f:
                json.dump({
                    'document_id': document_id,
                    'stage': stage,
                    'timestamp': timestamp,
                    'results': serializable_results
                }, f, indent=2)

            logger.info(f"Saved {stage} results to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save temp results: {e}")
            return None

    def make_serializable(self, obj):
        """Convert object to JSON-serializable format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self.make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_serializable(v) for v in obj]
        elif hasattr(obj, '__dict__'):
            return {k: self.make_serializable(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
        else:
            try:
                json.dumps(obj)
                return obj
            except:
                return str(obj)

    @staticmethod
    def get_fallback_segmentation_recommendations() -> Dict[str, Any]:
        """Fallback recommendations when LangExtract is unavailable"""
        return {
            'method': 'fallback_recommendations',
            'confidence': 0.3,
            'character_level_positions': False,
            'structural_segments': [],
            'semantic_segments': [],
            'temporal_segments': [],
            'recommended_strategy': {
                'primary': 'paragraph_segmentation',
                'rationale': 'LangExtract unavailable, using basic segmentation',
                'secondary': 'sentence_refinement'
            },
            'integration_suggestions': {
                'combine_with': ['paragraph', 'sentence'],
                'avoid_combining_with': [],
                'optimal_hybrid_approach': 'paragraph + sentence'
            },
            'error': 'LangExtract service not available'
        }
