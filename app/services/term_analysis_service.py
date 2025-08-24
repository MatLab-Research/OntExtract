"""
Term Analysis Service integrating with shared services for semantic change analysis.

This service provides comprehensive term analysis capabilities by leveraging
the shared services architecture for embedding generation, semantic tracking,
temporal extraction, and historical processing.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from shared_services.embedding.embedding_service import EmbeddingService
from shared_services.preprocessing.semantic_tracker import SemanticEvolutionTracker, SemanticDrift, MeaningCluster
from shared_services.preprocessing.temporal_extractor import TemporalWordUsageExtractor, WordUsageContext
from shared_services.preprocessing.historical_processor import HistoricalDocumentProcessor
from shared_services.preprocessing.provenance_tracker import ProvenanceTracker

from app.models import Term, TermVersion, ContextAnchor, SemanticDriftActivity, AnalysisAgent
from app import db

logger = logging.getLogger(__name__)


@dataclass
class TermAnalysisResult:
    """Results from comprehensive term analysis."""
    term_id: str
    analysis_type: str
    fuzziness_score: float
    confidence_level: str
    context_anchors: List[str]
    semantic_drift: Optional[Dict[str, Any]] = None
    meaning_clusters: List[Dict[str, Any]] = None
    temporal_contexts: List[Dict[str, Any]] = None
    embeddings: Optional[List[float]] = None
    provenance: Optional[Dict[str, Any]] = None


class TermAnalysisService:
    """Service for comprehensive term analysis using shared services."""
    
    def __init__(self, 
                 embedding_service: Optional[EmbeddingService] = None,
                 semantic_tracker: Optional[SemanticEvolutionTracker] = None,
                 temporal_extractor: Optional[TemporalWordUsageExtractor] = None,
                 historical_processor: Optional[HistoricalDocumentProcessor] = None,
                 provenance_tracker: Optional[ProvenanceTracker] = None):
        """
        Initialize with shared services.
        
        Args:
            embedding_service: Service for generating embeddings
            semantic_tracker: Service for tracking semantic changes
            temporal_extractor: Service for extracting temporal word usage
            historical_processor: Service for processing historical texts
            provenance_tracker: Service for tracking provenance
        """
        # Initialize shared services with graceful fallbacks
        try:
            self.embedding_service = embedding_service or EmbeddingService()
        except Exception as e:
            logger.warning(f"EmbeddingService unavailable: {e}")
            self.embedding_service = None
            
        try:
            self.semantic_tracker = semantic_tracker or SemanticEvolutionTracker()
        except Exception as e:
            logger.warning(f"SemanticEvolutionTracker unavailable: {e}")
            self.semantic_tracker = None
            
        try:
            self.temporal_extractor = temporal_extractor or TemporalWordUsageExtractor()
        except Exception as e:
            logger.warning(f"TemporalExtractor unavailable: {e}")
            self.temporal_extractor = None
            
        try:
            self.historical_processor = historical_processor or HistoricalDocumentProcessor()
        except Exception as e:
            logger.warning(f"HistoricalProcessor unavailable: {e}")
            self.historical_processor = None
            
        try:
            self.provenance_tracker = provenance_tracker or ProvenanceTracker()
        except Exception as e:
            logger.warning(f"ProvenanceTracker unavailable: {e}")
            self.provenance_tracker = None
    
    def analyze_term(self, term: Term, corpus_texts: Optional[List[str]] = None) -> TermAnalysisResult:
        """
        Perform comprehensive analysis of a term using all available services.
        
        Args:
            term: The term to analyze
            corpus_texts: Optional corpus texts for temporal analysis
            
        Returns:
            TermAnalysisResult with comprehensive analysis
        """
        logger.info(f"Starting comprehensive analysis for term: {term.term_text}")
        
        # Get current version for analysis
        current_version = term.get_current_version()
        if not current_version:
            raise ValueError(f"Term {term.term_text} has no current version")
        
        result = TermAnalysisResult(
            term_id=str(term.id),
            analysis_type="comprehensive",
            fuzziness_score=0.0,
            confidence_level="medium",
            context_anchors=[]
        )
        
        # 1. Generate embeddings for term and current meaning
        if self.embedding_service and self.embedding_service.is_available():
            try:
                # Create combined text for embedding
                combined_text = f"{term.term_text}. {current_version.meaning_description}"
                if current_version.context_anchor:
                    combined_text += f" Related terms: {', '.join(current_version.context_anchor)}"
                
                result.embeddings = self.embedding_service.get_embedding(combined_text)
                logger.info(f"Generated embeddings for {term.term_text}")
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
        
        # 2. Extract temporal contexts if corpus provided
        if self.temporal_extractor and corpus_texts:
            try:
                temporal_contexts = []
                for text in corpus_texts[:5]:  # Limit for performance
                    contexts = self.temporal_extractor.extract_word_contexts(
                        text=text,
                        target_words=[term.term_text],
                        context_window=10
                    )
                    temporal_contexts.extend([ctx.to_dict() for ctx in contexts.get(term.term_text, [])])
                
                result.temporal_contexts = temporal_contexts[:20]  # Limit results
                logger.info(f"Extracted {len(temporal_contexts)} temporal contexts")
            except Exception as e:
                logger.error(f"Failed to extract temporal contexts: {e}")
        
        # 3. Discover context anchors using semantic analysis
        context_anchors = self._discover_context_anchors(term, current_version)
        result.context_anchors = context_anchors
        
        # 4. Calculate fuzziness score using semantic drift analysis
        fuzziness_score, confidence = self._calculate_fuzziness_score(term, current_version)
        result.fuzziness_score = fuzziness_score
        result.confidence_level = confidence
        
        # 5. Track provenance if service available
        if self.provenance_tracker:
            try:
                provenance = self.provenance_tracker.track_entity_creation(
                    entity_id=str(term.id),
                    entity_type="Term",
                    created_by="TermAnalysisService",
                    source_data={
                        "term_text": term.term_text,
                        "temporal_period": current_version.temporal_period,
                        "analysis_method": "shared_services_integration"
                    }
                )
                result.provenance = provenance
            except Exception as e:
                logger.error(f"Failed to track provenance: {e}")
        
        logger.info(f"Completed comprehensive analysis for {term.term_text}")
        return result
    
    def detect_semantic_drift(self, term: Term, baseline_version: TermVersion, 
                             comparison_version: TermVersion) -> Optional[SemanticDrift]:
        """
        Detect semantic drift between two term versions.
        
        Args:
            term: The term being analyzed
            baseline_version: Earlier version for comparison
            comparison_version: Later version for comparison
            
        Returns:
            SemanticDrift object or None if analysis fails
        """
        if not self.semantic_tracker:
            logger.warning("SemanticEvolutionTracker not available for drift detection")
            return None
        
        try:
            # Prepare contexts for comparison
            baseline_contexts = baseline_version.context_anchor or []
            comparison_contexts = comparison_version.context_anchor or []
            
            # Use semantic tracker to measure drift
            drift = self.semantic_tracker.measure_drift(
                word=term.term_text,
                baseline_contexts=baseline_contexts,
                comparison_contexts=comparison_contexts,
                baseline_period=baseline_version.temporal_period,
                comparison_period=comparison_version.temporal_period
            )
            
            return drift
            
        except Exception as e:
            logger.error(f"Failed to detect semantic drift: {e}")
            return None
    
    def find_meaning_clusters(self, term: Term, corpus_texts: List[str], 
                             temporal_periods: List[str]) -> List[MeaningCluster]:
        """
        Find meaning clusters across different temporal periods.
        
        Args:
            term: The term to analyze
            corpus_texts: Corpus texts for analysis
            temporal_periods: List of temporal periods to analyze
            
        Returns:
            List of MeaningCluster objects
        """
        if not self.semantic_tracker or not self.temporal_extractor:
            logger.warning("Required services not available for cluster analysis")
            return []
        
        clusters = []
        
        try:
            for i, period in enumerate(temporal_periods):
                # Extract contexts for this period
                period_texts = corpus_texts[i:i+1] if i < len(corpus_texts) else []
                
                if period_texts:
                    contexts = self.temporal_extractor.extract_word_contexts(
                        text=period_texts[0],
                        target_words=[term.term_text],
                        context_window=15
                    )
                    
                    word_contexts = contexts.get(term.term_text, [])
                    if word_contexts:
                        # Use semantic tracker to identify clusters
                        cluster = self.semantic_tracker.identify_meaning_cluster(
                            word=term.term_text,
                            period=period,
                            contexts=[ctx.sentence for ctx in word_contexts]
                        )
                        
                        if cluster:
                            clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to find meaning clusters: {e}")
            return []
    
    def _discover_context_anchors(self, term: Term, version: TermVersion) -> List[str]:
        """
        Discover context anchors using embedding similarity.
        
        Args:
            term: The term to analyze
            version: The term version to analyze
            
        Returns:
            List of context anchor terms
        """
        # If already has context anchors, use those
        if version.context_anchor:
            return version.context_anchor[:10]  # Limit to top 10
        
        # Try to discover new anchors using embeddings
        if not self.embedding_service or not self.embedding_service.is_available():
            logger.warning("EmbeddingService not available for context anchor discovery")
            return []
        
        try:
            # Get existing context anchors from database for similarity comparison
            existing_anchors = ContextAnchor.query.limit(100).all()
            if not existing_anchors:
                return []
            
            # Generate embedding for the term's meaning
            term_embedding = self.embedding_service.get_embedding(
                f"{term.term_text}. {version.meaning_description}"
            )
            
            # Compare with existing anchors
            similarities = []
            for anchor in existing_anchors:
                try:
                    anchor_embedding = self.embedding_service.get_embedding(anchor.anchor_term)
                    similarity = self.embedding_service.similarity(term_embedding, anchor_embedding)
                    similarities.append((anchor.anchor_term, similarity))
                except Exception as e:
                    logger.debug(f"Failed to compare with anchor {anchor.anchor_term}: {e}")
                    continue
            
            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [anchor for anchor, sim in similarities[:15] if sim > 0.3]  # Threshold for relevance
            
        except Exception as e:
            logger.error(f"Failed to discover context anchors: {e}")
            return []
    
    def _calculate_fuzziness_score(self, term: Term, version: TermVersion) -> Tuple[float, str]:
        """
        Calculate fuzziness score for a term version.
        
        Args:
            term: The term to analyze
            version: The term version to analyze
            
        Returns:
            Tuple of (fuzziness_score, confidence_level)
        """
        # If already has a manually set score, use it
        if version.fuzziness_score is not None:
            return float(version.fuzziness_score), version.confidence_level or "medium"
        
        # Try to calculate using semantic analysis
        if not self.semantic_tracker:
            # Fallback to simple heuristic based on context anchors
            if version.context_anchor:
                # More context anchors = higher confidence/fuzziness
                anchor_count = len(version.context_anchor)
                fuzziness = min(0.9, anchor_count / 10.0)  # Max 0.9, scale by anchor count
                confidence = "high" if anchor_count >= 5 else "medium" if anchor_count >= 2 else "low"
                return fuzziness, confidence
            else:
                return 0.5, "low"  # Default uncertain score
        
        try:
            # Use semantic tracker for more sophisticated calculation
            # This would ideally compare with other versions or baseline
            versions = term.get_all_versions_ordered()
            if len(versions) > 1:
                # Compare with previous version
                previous_version = versions[-2] if versions[-1] == version else versions[-1]
                drift = self.detect_semantic_drift(term, previous_version, version)
                
                if drift:
                    # Higher drift = lower fuzziness (less retention of original meaning)
                    fuzziness = max(0.1, 1.0 - drift.drift_score)
                    confidence = "high" if abs(drift.drift_score) > 0.3 else "medium"
                    return fuzziness, confidence
            
            # Fallback for single version
            return 0.7, "medium"  # Assume moderate retention for new terms
            
        except Exception as e:
            logger.error(f"Failed to calculate fuzziness score: {e}")
            return 0.5, "low"
    
    def create_semantic_drift_activity(self, term: Term, baseline_version: TermVersion,
                                      comparison_version: TermVersion, 
                                      drift_result: SemanticDrift) -> SemanticDriftActivity:
        """
        Create a semantic drift activity record from analysis results.
        
        Args:
            term: The term being analyzed
            baseline_version: Earlier version
            comparison_version: Later version  
            drift_result: Results from semantic drift analysis
            
        Returns:
            SemanticDriftActivity instance
        """
        # Get or create analysis agent
        agent = AnalysisAgent.query.filter_by(
            name="Shared Services Semantic Evolution Tracker",
            agent_type="SoftwareAgent"
        ).first()
        
        if not agent:
            agent = AnalysisAgent(
                agent_type="SoftwareAgent",
                name="Shared Services Semantic Evolution Tracker",
                description="Semantic drift detection using shared services architecture",
                algorithm_type="SemanticEvolutionTracker",
                version="1.0"
            )
            db.session.add(agent)
            db.session.flush()
        
        # Create activity record
        activity = SemanticDriftActivity(
            activity_type="semantic_drift_detection",
            start_period=baseline_version.temporal_period,
            end_period=comparison_version.temporal_period,
            used_entity=baseline_version.id,
            generated_entity=comparison_version.id,
            was_associated_with=agent.id,
            drift_metrics={
                "drift_score": drift_result.drift_score,
                "meaning_changes": drift_result.meaning_changes,
                "emergent_contexts": drift_result.emergent_contexts,
                "lost_contexts": drift_result.lost_contexts
            },
            detection_algorithm="SemanticEvolutionTracker",
            drift_detected=drift_result.drift_score > 0.3,
            drift_magnitude=drift_result.drift_score,
            drift_type="gradual" if drift_result.drift_score < 0.6 else "major",
            evidence_summary=f"Detected {len(drift_result.meaning_changes)} meaning changes",
            activity_status="completed"
        )
        
        return activity
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all shared services.
        
        Returns:
            Dictionary with service status information
        """
        status = {}
        
        services = [
            ("embedding_service", self.embedding_service),
            ("semantic_tracker", self.semantic_tracker),
            ("temporal_extractor", self.temporal_extractor),
            ("historical_processor", self.historical_processor),
            ("provenance_tracker", self.provenance_tracker)
        ]
        
        for service_name, service in services:
            if service is None:
                status[service_name] = {"available": False, "reason": "Service not initialized"}
            else:
                try:
                    # Check if service has is_available method
                    if hasattr(service, 'is_available'):
                        available = service.is_available()
                    else:
                        available = True  # Assume available if no check method
                    
                    status[service_name] = {
                        "available": available,
                        "class": service.__class__.__name__,
                        "module": service.__class__.__module__
                    }
                except Exception as e:
                    status[service_name] = {
                        "available": False,
                        "error": str(e)
                    }
        
        return status