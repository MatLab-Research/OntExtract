"""
Enhanced Features Module

Advanced features using shared services (embeddings, ontology, LLM).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class EnhancedFeatures:
    """Handles enhanced features using shared services"""

    def __init__(self, embedding_service=None, ontology_service=None, llm_service=None):
        self.embedding_service = embedding_service
        self.ontology_service = ontology_service
        self.llm_service = llm_service
        self.enabled = all([embedding_service, ontology_service, llm_service])

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        if not self.enabled or not self.embedding_service:
            logger.warning("Enhanced features not available, cannot generate embeddings")
            return []

        try:
            return self.embedding_service.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []

    def extract_ontology_entities(self, text: str, ontology_id: str = "engineering-ethics") -> List[Dict[str, Any]]:
        """Extract entities from text using ontology knowledge"""
        if not self.enabled:
            logger.warning("Enhanced features not available")
            return []

        try:
            ontology_entities = self.ontology_service.get_entities(ontology_id)
            entity_types = list(ontology_entities.get("entities", {}).keys())

            if entity_types:
                return self.llm_service.extract_entities(text, entity_types)
            else:
                return self.llm_service.extract_entities(text)

        except Exception as e:
            logger.error(f"Error extracting ontology entities: {e}")
            return []

    def summarize_with_llm(self, text: str, max_length: int = 500) -> str:
        """Generate summary using LLM service"""
        if not self.enabled or not self.llm_service:
            logger.warning("Enhanced features not available, cannot generate LLM summary")
            return text[:max_length] + "..." if len(text) > max_length else text

        try:
            return self.llm_service.summarize_text(text, max_length)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self.enabled or not self.embedding_service:
            # Basic word overlap similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0

            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union) if union else 0.0

        try:
            embedding1 = self.embedding_service.get_embedding(text1)
            embedding2 = self.embedding_service.get_embedding(text2)
            return self.embedding_service.similarity(embedding1, embedding2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
