"""
Semantic Evolution Tracker for monitoring linguistic meaning changes over time.

This module tracks semantic drift, identifies meaning clusters by period,
detects emergent meanings, and monitors domain migration of words.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class MeaningCluster:
    """A cluster of similar word meanings in a specific time period."""
    cluster_id: str
    period: str
    year: Optional[int]
    central_meaning: str
    example_contexts: List[str]
    word_forms: List[str]
    semantic_field: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'cluster_id': self.cluster_id,
            'period': self.period,
            'year': self.year,
            'central_meaning': self.central_meaning,
            'example_contexts': self.example_contexts[:5],
            'word_forms': self.word_forms,
            'semantic_field': self.semantic_field,
            'confidence': self.confidence
        }

@dataclass
class SemanticDrift:
    """Measures semantic drift of a word over time."""
    word: str
    baseline_period: str
    comparison_period: str
    drift_score: float
    meaning_changes: List[str]
    emergent_contexts: List[str]
    lost_contexts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'word': self.word,
            'baseline_period': self.baseline_period,
            'comparison_period': self.comparison_period,
            'drift_score': self.drift_score,
            'meaning_changes': self.meaning_changes,
            'emergent_contexts': self.emergent_contexts[:5],
            'lost_contexts': self.lost_contexts[:5]
        }

@dataclass
class EmergentMeaning:
    """A new meaning that emerged for a word in a specific period."""
    word: str
    period: str
    year: Optional[int]
    new_meaning: str
    evidence_contexts: List[str]
    frequency: int
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'word': self.word,
            'period': self.period,
            'year': self.year,
            'new_meaning': self.new_meaning,
            'evidence_contexts': self.evidence_contexts[:5],
            'frequency': self.frequency,
            'confidence': self.confidence
        }

@dataclass
class DomainMigration:
    """Tracks movement of words between semantic domains."""
    word: str
    source_domain: str
    target_domain: str
    period: str
    migration_strength: float
    examples: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'word': self.word,
            'source_domain': self.source_domain,
            'target_domain': self.target_domain,
            'period': self.period,
            'migration_strength': self.migration_strength,
            'examples': self.examples[:5]
        }

@dataclass
class SemanticEvolution:
    """Complete semantic evolution analysis results."""
    word: str
    time_periods: List[str]
    meaning_clusters: List[MeaningCluster]
    semantic_drift_metrics: List[SemanticDrift]
    emergent_meanings: List[EmergentMeaning]
    domain_migrations: List[DomainMigration]
    evolution_timeline: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'word': self.word,
            'time_periods': self.time_periods,
            'meaning_clusters': [mc.to_dict() for mc in self.meaning_clusters],
            'semantic_drift_metrics': [sd.to_dict() for sd in self.semantic_drift_metrics],
            'emergent_meanings': [em.to_dict() for em in self.emergent_meanings],
            'domain_migrations': [dm.to_dict() for dm in self.domain_migrations],
            'evolution_timeline': self.evolution_timeline,
            'metadata': self.metadata
        }

class SemanticEvolutionTracker:
    """
    Tracks semantic evolution of words across different time periods.
    """
    
    # Thresholds for semantic analysis
    DRIFT_THRESHOLD = 0.3  # Minimum cosine distance for semantic drift
    EMERGENCE_THRESHOLD = 0.5  # Minimum novelty score for emergent meaning
    MIGRATION_THRESHOLD = 0.4  # Minimum score for domain migration
    
    def __init__(self, embedding_service=None):
        """
        Initialize the tracker.
        
        Args:
            embedding_service: Optional embedding service for vector representations
        """
        self.embedding_service = embedding_service
        self.period_data = defaultdict(dict)
        self.word_evolution = defaultdict(list)
    
    def track_evolution(self, word: str, temporal_usages: List[Any]) -> SemanticEvolution:
        """
        Track semantic evolution of a word across time periods.
        
        Args:
            word: The word to track
            temporal_usages: List of TemporalWordUsage objects for different periods
            
        Returns:
            SemanticEvolution object with analysis results
        """
        # Sort usages by time
        temporal_usages = sorted(temporal_usages, key=lambda x: x.year or 0)
        
        # Extract time periods
        time_periods = [usage.period for usage in temporal_usages]
        
        # Cluster meanings per period
        meaning_clusters = self._cluster_meanings(word, temporal_usages)
        
        # Calculate semantic drift between periods
        drift_metrics = self._calculate_semantic_drift(word, temporal_usages)
        
        # Detect emergent meanings
        emergent_meanings = self._detect_emergent_meanings(word, temporal_usages)
        
        # Track domain migrations
        domain_migrations = self._track_domain_migrations(word, temporal_usages)
        
        # Build evolution timeline
        evolution_timeline = self._build_evolution_timeline(
            word, temporal_usages, meaning_clusters, emergent_meanings
        )
        
        # Build metadata
        metadata = {
            'analysis_date': datetime.now().isoformat(),
            'periods_analyzed': len(time_periods),
            'total_contexts': sum(len(usage.word_contexts.get(word, [])) 
                                for usage in temporal_usages),
            'drift_detected': len(drift_metrics) > 0,
            'emergent_meanings_found': len(emergent_meanings) > 0
        }
        
        return SemanticEvolution(
            word=word,
            time_periods=time_periods,
            meaning_clusters=meaning_clusters,
            semantic_drift_metrics=drift_metrics,
            emergent_meanings=emergent_meanings,
            domain_migrations=domain_migrations,
            evolution_timeline=evolution_timeline,
            metadata=metadata
        )
    
    def _cluster_meanings(self, word: str, temporal_usages: List[Any]) -> List[MeaningCluster]:
        """Cluster word meanings within each time period."""
        clusters = []
        
        for usage in temporal_usages:
            if word not in usage.word_contexts:
                continue
            
            contexts = usage.word_contexts[word]
            if len(contexts) < 5:  # Need minimum contexts for clustering
                continue
            
            # Extract features from contexts
            context_features = self._extract_context_features(contexts)
            
            # Cluster contexts using DBSCAN
            if len(context_features) > 1:
                clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine')
                labels = clustering.fit_predict(context_features)
                
                # Create meaning clusters
                for cluster_label in set(labels):
                    if cluster_label == -1:  # Skip noise points
                        continue
                    
                    cluster_contexts = [contexts[i] for i, l in enumerate(labels) if l == cluster_label]
                    
                    cluster = MeaningCluster(
                        cluster_id=f"{word}_{usage.period}_{cluster_label}",
                        period=usage.period,
                        year=usage.year,
                        central_meaning=self._extract_central_meaning(cluster_contexts),
                        example_contexts=[ctx.sentence for ctx in cluster_contexts[:3]],
                        word_forms=list(set(ctx.word for ctx in cluster_contexts)),
                        semantic_field=self._determine_semantic_field(cluster_contexts, usage),
                        confidence=len(cluster_contexts) / len(contexts)
                    )
                    clusters.append(cluster)
        
        return clusters
    
    def _calculate_semantic_drift(self, word: str, temporal_usages: List[Any]) -> List[SemanticDrift]:
        """Calculate semantic drift between consecutive time periods."""
        drift_metrics = []
        
        for i in range(len(temporal_usages) - 1):
            baseline = temporal_usages[i]
            comparison = temporal_usages[i + 1]
            
            if word not in baseline.word_contexts or word not in comparison.word_contexts:
                continue
            
            baseline_contexts = baseline.word_contexts[word]
            comparison_contexts = comparison.word_contexts[word]
            
            # Calculate drift score
            drift_score = self._calculate_drift_score(baseline_contexts, comparison_contexts)
            
            if drift_score > self.DRIFT_THRESHOLD:
                # Identify meaning changes
                meaning_changes = self._identify_meaning_changes(
                    baseline_contexts, comparison_contexts
                )
                
                # Find emergent and lost contexts
                emergent = self._find_novel_contexts(comparison_contexts, baseline_contexts)
                lost = self._find_novel_contexts(baseline_contexts, comparison_contexts)
                
                drift = SemanticDrift(
                    word=word,
                    baseline_period=baseline.period,
                    comparison_period=comparison.period,
                    drift_score=drift_score,
                    meaning_changes=meaning_changes,
                    emergent_contexts=emergent,
                    lost_contexts=lost
                )
                drift_metrics.append(drift)
        
        return drift_metrics
    
    def _detect_emergent_meanings(self, word: str, temporal_usages: List[Any]) -> List[EmergentMeaning]:
        """Detect new meanings that emerge over time."""
        emergent_meanings = []
        
        # Track cumulative contexts
        cumulative_contexts = []
        
        for usage in temporal_usages:
            if word not in usage.word_contexts:
                continue
            
            current_contexts = usage.word_contexts[word]
            
            # Find novel contexts compared to cumulative history
            if cumulative_contexts:
                novel_contexts = self._find_truly_novel_contexts(
                    current_contexts, cumulative_contexts
                )
                
                if novel_contexts:
                    # Cluster novel contexts to identify coherent new meanings
                    novel_clusters = self._cluster_novel_contexts(novel_contexts)
                    
                    for cluster in novel_clusters:
                        emergent = EmergentMeaning(
                            word=word,
                            period=usage.period,
                            year=usage.year,
                            new_meaning=self._extract_central_meaning(cluster),
                            evidence_contexts=[ctx.sentence for ctx in cluster[:3]],
                            frequency=len(cluster),
                            confidence=self._calculate_emergence_confidence(cluster, current_contexts)
                        )
                        emergent_meanings.append(emergent)
            
            # Add to cumulative contexts
            cumulative_contexts.extend(current_contexts)
        
        return emergent_meanings
    
    def _track_domain_migrations(self, word: str, temporal_usages: List[Any]) -> List[DomainMigration]:
        """Track movement of words between semantic domains."""
        migrations = []
        
        # Extract domain distributions per period
        domain_timeline = {}
        for usage in temporal_usages:
            if word not in usage.semantic_fields:
                continue
            
            fields = usage.semantic_fields[word]
            domain_dist = defaultdict(float)
            for field in fields:
                domain_dist[field.name] += field.confidence
            
            domain_timeline[usage.period] = domain_dist
        
        # Detect migrations between consecutive periods
        periods = list(domain_timeline.keys())
        for i in range(len(periods) - 1):
            source_period = periods[i]
            target_period = periods[i + 1]
            
            source_domains = domain_timeline[source_period]
            target_domains = domain_timeline[target_period]
            
            # Find domain shifts
            for source_domain in source_domains:
                for target_domain in target_domains:
                    if source_domain != target_domain:
                        migration_strength = self._calculate_migration_strength(
                            source_domains[source_domain],
                            target_domains[target_domain]
                        )
                        
                        if migration_strength > self.MIGRATION_THRESHOLD:
                            # Find example contexts
                            examples = self._find_migration_examples(
                                word, temporal_usages[i+1], source_domain, target_domain
                            )
                            
                            migration = DomainMigration(
                                word=word,
                                source_domain=source_domain,
                                target_domain=target_domain,
                                period=target_period,
                                migration_strength=migration_strength,
                                examples=examples
                            )
                            migrations.append(migration)
        
        return migrations
    
    def _build_evolution_timeline(self, word: str, temporal_usages: List[Any],
                                 meaning_clusters: List[MeaningCluster],
                                 emergent_meanings: List[EmergentMeaning]) -> Dict[str, Any]:
        """Build a timeline of semantic evolution."""
        timeline = {}
        
        for usage in temporal_usages:
            period_data = {
                'period': usage.period,
                'year': usage.year,
                'frequency': usage.frequency_distribution.get(word, 0),
                'meanings': [],
                'dominant_pos': None,
                'dominant_field': None
            }
            
            # Add meaning clusters for this period
            period_clusters = [mc for mc in meaning_clusters if mc.period == usage.period]
            period_data['meanings'] = [mc.central_meaning for mc in period_clusters]
            
            # Add emergent meanings
            period_emergent = [em for em in emergent_meanings if em.period == usage.period]
            period_data['new_meanings'] = [em.new_meaning for em in period_emergent]
            
            # Dominant POS tag
            if word in usage.syntactic_patterns:
                pos_dist = usage.syntactic_patterns[word]
                if pos_dist:
                    period_data['dominant_pos'] = max(pos_dist, key=pos_dist.get)
            
            # Dominant semantic field
            if word in usage.semantic_fields:
                fields = usage.semantic_fields[word]
                if fields:
                    period_data['dominant_field'] = max(fields, key=lambda f: f.confidence).name
            
            timeline[usage.period] = period_data
        
        return timeline
    
    def _extract_context_features(self, contexts: List[Any]) -> np.ndarray:
        """Extract feature vectors from word contexts."""
        features = []
        
        for ctx in contexts:
            # Simple feature extraction (can be enhanced with embeddings)
            feature = []
            
            # POS tag feature
            pos_map = {'NN': 0, 'VB': 1, 'JJ': 2, 'RB': 3}
            pos_value = pos_map.get(ctx.pos_tag[:2], 4)
            feature.append(pos_value)
            
            # Context word features
            left_words = set(ctx.left_context)
            right_words = set(ctx.right_context)
            
            # Simple bag of words features (limited for performance)
            common_words = ['the', 'a', 'of', 'to', 'in', 'and', 'is', 'was', 'for', 'with']
            for word in common_words:
                feature.append(1 if word in left_words else 0)
                feature.append(1 if word in right_words else 0)
            
            features.append(feature)
        
        return np.array(features)
    
    def _extract_central_meaning(self, contexts: List[Any]) -> str:
        """Extract a central meaning description from a cluster of contexts."""
        # Find most common collocations
        collocations = Counter()
        for ctx in contexts:
            for word in ctx.left_context + ctx.right_context:
                if word.isalpha() and len(word) > 3:
                    collocations[word] += 1
        
        # Build meaning description from top collocations
        top_words = [word for word, _ in collocations.most_common(3)]
        if top_words:
            return f"associated with: {', '.join(top_words)}"
        return "general usage"
    
    def _determine_semantic_field(self, contexts: List[Any], usage: Any) -> Optional[str]:
        """Determine the semantic field for a cluster of contexts."""
        word = contexts[0].word if contexts else None
        if word and word in usage.semantic_fields:
            fields = usage.semantic_fields[word]
            if fields:
                return max(fields, key=lambda f: f.confidence).name
        return None
    
    def _calculate_drift_score(self, baseline_contexts: List[Any], 
                              comparison_contexts: List[Any]) -> float:
        """Calculate semantic drift score between two sets of contexts."""
        # Extract features
        baseline_features = self._extract_context_features(baseline_contexts)
        comparison_features = self._extract_context_features(comparison_contexts)
        
        # Calculate centroid distance
        if len(baseline_features) > 0 and len(comparison_features) > 0:
            baseline_centroid = np.mean(baseline_features, axis=0)
            comparison_centroid = np.mean(comparison_features, axis=0)
            
            # Cosine distance
            similarity = cosine_similarity(
                baseline_centroid.reshape(1, -1), 
                comparison_centroid.reshape(1, -1)
            )[0][0]
            return float(1 - similarity)
        
        return 0.0
    
    def _identify_meaning_changes(self, baseline_contexts: List[Any],
                                 comparison_contexts: List[Any]) -> List[str]:
        """Identify specific meaning changes between periods."""
        changes = []
        
        # Compare POS distributions
        baseline_pos = Counter(ctx.pos_tag[:2] for ctx in baseline_contexts)
        comparison_pos = Counter(ctx.pos_tag[:2] for ctx in comparison_contexts)
        
        # Check for major POS shifts
        baseline_main = max(baseline_pos, key=lambda x: baseline_pos[x]) if baseline_pos else None
        comparison_main = max(comparison_pos, key=lambda x: comparison_pos[x]) if comparison_pos else None
        
        if baseline_main != comparison_main:
            changes.append(f"Primary usage shifted from {baseline_main} to {comparison_main}")
        
        # Check for context changes
        baseline_context_words = set()
        comparison_context_words = set()
        
        for ctx in baseline_contexts:
            baseline_context_words.update(ctx.left_context + ctx.right_context)
        for ctx in comparison_contexts:
            comparison_context_words.update(ctx.left_context + ctx.right_context)
        
        # Find significant new associations
        new_associations = comparison_context_words - baseline_context_words
        lost_associations = baseline_context_words - comparison_context_words
        
        if len(new_associations) > 10:
            changes.append(f"Gained {len(new_associations)} new contextual associations")
        if len(lost_associations) > 10:
            changes.append(f"Lost {len(lost_associations)} previous associations")
        
        return changes
    
    def _find_novel_contexts(self, contexts_a: List[Any], contexts_b: List[Any]) -> List[str]:
        """Find contexts in A that are novel compared to B."""
        novel = []
        
        # Build context signature for B
        b_signatures = set()
        for ctx in contexts_b:
            signature = tuple(ctx.left_context[-2:] + [ctx.word] + ctx.right_context[:2])
            b_signatures.add(signature)
        
        # Find novel contexts in A
        for ctx in contexts_a:
            signature = tuple(ctx.left_context[-2:] + [ctx.word] + ctx.right_context[:2])
            if signature not in b_signatures:
                novel.append(ctx.sentence[:100])
        
        return novel[:5]  # Limit to top 5
    
    def _find_truly_novel_contexts(self, current: List[Any], historical: List[Any]) -> List[Any]:
        """Find contexts that are truly novel compared to historical usage."""
        novel = []
        
        # Build historical signatures
        historical_sigs = set()
        for ctx in historical:
            sig = (ctx.pos_tag, tuple(sorted(ctx.left_context + ctx.right_context)))
            historical_sigs.add(sig)
        
        # Find novel
        for ctx in current:
            sig = (ctx.pos_tag, tuple(sorted(ctx.left_context + ctx.right_context)))
            if sig not in historical_sigs:
                novel.append(ctx)
        
        return novel
    
    def _cluster_novel_contexts(self, contexts: List[Any]) -> List[List[Any]]:
        """Cluster novel contexts to identify coherent new meanings."""
        if len(contexts) < 2:
            return [contexts] if contexts else []
        
        # Extract features
        features = self._extract_context_features(contexts)
        
        # Cluster
        clustering = DBSCAN(eps=0.3, min_samples=1, metric='cosine')
        labels = clustering.fit_predict(features)
        
        # Group by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[label].append(contexts[i])
        
        return list(clusters.values())
    
    def _calculate_emergence_confidence(self, cluster: List[Any], all_contexts: List[Any]) -> float:
        """Calculate confidence score for an emergent meaning."""
        # Ratio of cluster size to total contexts
        size_ratio = len(cluster) / len(all_contexts) if all_contexts else 0
        
        # Coherence of the cluster (simplified)
        if len(cluster) > 1:
            features = self._extract_context_features(cluster)
            centroid = np.mean(features, axis=0)
            distances = [cosine_similarity(f.reshape(1, -1), centroid.reshape(1, -1))[0][0] for f in features]
            coherence = float(np.mean(distances))
        else:
            coherence = 0.5
        
        return (size_ratio + coherence) / 2
    
    def _calculate_migration_strength(self, source_confidence: float, 
                                     target_confidence: float) -> float:
        """Calculate strength of domain migration."""
        # Simple ratio-based calculation
        if source_confidence > 0:
            return target_confidence / (source_confidence + target_confidence)
        return 0.0
    
    def _find_migration_examples(self, word: str, usage: Any, 
                                source_domain: str, target_domain: str) -> List[str]:
        """Find example sentences showing domain migration."""
        examples = []
        
        if word in usage.word_contexts:
            contexts = usage.word_contexts[word]
            # Simple heuristic: return first few contexts
            examples = [ctx.sentence[:100] for ctx in contexts[:3]]
        
        return examples
