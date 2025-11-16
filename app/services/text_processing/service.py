"""
Text Processing Service

Main service class that coordinates all text processing operations.
"""

import os
import sys
import logging
from typing import List, Dict, Any

# Add shared services to path
shared_services_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared_services')
if shared_services_path not in sys.path:
    sys.path.insert(0, shared_services_path)

try:
    from shared_services.embedding.embedding_service import EmbeddingService
    from shared_services.embedding.file_processor import FileProcessingService
    from shared_services.ontology.entity_service import OntologyEntityService
    from shared_services.llm.base_service import BaseLLMService
    SHARED_SERVICES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Shared services not available: {e}")
    SHARED_SERVICES_AVAILABLE = False

from .segmentation import TextSegmentation
from .analysis import TextAnalysis
from .processing import DocumentProcessing
from .enhanced_features import EnhancedFeatures

logger = logging.getLogger(__name__)


class TextProcessingService:
    """Enhanced service for text processing, segmentation, and analysis"""

    def __init__(self):
        # Initialize core modules
        self.segmenter = TextSegmentation()
        self.analyzer = TextAnalysis()

        # Initialize shared services if available
        if SHARED_SERVICES_AVAILABLE:
            try:
                embedding_service = EmbeddingService()
                file_processor = FileProcessingService()
                ontology_service = OntologyEntityService()
                llm_service = BaseLLMService()

                self.processor = DocumentProcessing(file_processor)
                self.enhanced = EnhancedFeatures(embedding_service, ontology_service, llm_service)

                self.enhanced_features_enabled = True
                logger.info("Enhanced text processing features enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize shared services: {e}")
                self.processor = DocumentProcessing()
                self.enhanced = EnhancedFeatures()
                self.enhanced_features_enabled = False
        else:
            self.processor = DocumentProcessing()
            self.enhanced = EnhancedFeatures()
            self.enhanced_features_enabled = False

    # Segmentation methods - delegated to TextSegmentation
    def create_initial_segments(self, document):
        """Create basic paragraph-level segments for a document"""
        return self.segmenter.create_initial_segments(document)

    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        return self.segmenter.split_into_paragraphs(text)

    def segment_by_paragraphs(self, document):
        """Create paragraph-level segments for a document"""
        return self.segmenter.segment_by_paragraphs(document)

    def segment_by_sentences(self, document):
        """Create sentence-level segments for a document"""
        return self.segmenter.segment_by_sentences(document)

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        return self.segmenter.split_into_sentences(text)

    def split_into_semantic_chunks(self, text: str) -> List[str]:
        """Split text into semantic chunks"""
        return self.segmenter.split_into_semantic_chunks(text)

    def segment_by_structure(self, document, structure_info: Dict[str, Any]):
        """Create segments based on detected document structure"""
        return self.segmenter.segment_by_structure(document, structure_info)

    # Analysis methods - delegated to TextAnalysis
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        return self.analyzer.extract_keywords(text)

    def calculate_readability_score(self, text: str) -> float:
        """Calculate readability score"""
        return self.analyzer.calculate_readability_score(text)

    def detect_document_structure(self, text: str) -> Dict[str, Any]:
        """Detect document structure"""
        return self.analyzer.detect_document_structure(text)

    # Processing methods - delegated to DocumentProcessing
    def process_file_content(self, file_path: str, file_type: str) -> str:
        """Process file and extract text content"""
        return self.processor.process_file_content(file_path, file_type)

    def process_document(self, document):
        """Process a document"""
        return self.processor.process_document(document)

    def chunk_text_for_processing(self, text: str, chunk_size: int = 1000,
                                  chunk_overlap: int = 200) -> List[str]:
        """Chunk text for processing"""
        return self.processor.chunk_text_for_processing(text, chunk_size, chunk_overlap, self.segmenter)

    # Enhanced features - delegated to EnhancedFeatures
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        return self.enhanced.generate_embeddings(texts)

    def extract_ontology_entities(self, text: str, ontology_id: str = "engineering-ethics") -> List[Dict[str, Any]]:
        """Extract entities using ontology knowledge"""
        return self.enhanced.extract_ontology_entities(text, ontology_id)

    def summarize_with_llm(self, text: str, max_length: int = 500) -> str:
        """Generate summary using LLM"""
        return self.enhanced.summarize_with_llm(text, max_length)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity"""
        return self.enhanced.calculate_similarity(text1, text2)

    # Service status
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            "enhanced_features_enabled": self.enhanced_features_enabled,
            "shared_services_available": SHARED_SERVICES_AVAILABLE
        }

        if self.enhanced_features_enabled and SHARED_SERVICES_AVAILABLE:
            try:
                status.update({
                    "embedding_providers": self.enhanced.embedding_service.get_provider_status() if self.enhanced.embedding_service else {},
                    "llm_providers": self.enhanced.llm_service.get_provider_status() if self.enhanced.llm_service else {},
                    "file_processor_types": self.processor.file_processor.get_supported_types() if self.processor.file_processor else [],
                    "available_ontologies": len(self.enhanced.ontology_service.list_ontologies()) if self.enhanced.ontology_service else 0
                })
            except Exception as e:
                logger.error(f"Error getting service status details: {e}")

        return status
