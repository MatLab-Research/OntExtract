"""
Entity-Level PROV-O Provenance Tracker for historical text analysis.

This module tracks the provenance of extracted entities following the PROV-O
ontology standard, maintaining full audit trails from source to result.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ProvenanceEntity:
    """A PROV-O Entity representing extracted linguistic data."""
    entity_id: str
    entity_type: str  # e.g., 'word_usage', 'collocation', 'semantic_cluster'
    value: Any
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            '@id': self.entity_id,
            '@type': ['prov:Entity', self.entity_type],
            'prov:value': self.value,
            'attributes': self.attributes
        }

@dataclass
class ProvenanceActivity:
    """A PROV-O Activity representing a processing step."""
    activity_id: str
    activity_type: str  # e.g., 'extraction', 'normalization', 'clustering'
    started_at: datetime
    ended_at: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            '@id': self.activity_id,
            '@type': ['prov:Activity', self.activity_type],
            'prov:startedAtTime': self.started_at.isoformat(),
            'prov:endedAtTime': self.ended_at.isoformat() if self.ended_at else None,
            'parameters': self.parameters
        }

@dataclass
class ProvenanceAgent:
    """A PROV-O Agent representing software or human actors."""
    agent_id: str
    agent_type: str  # e.g., 'software', 'algorithm', 'human'
    name: str
    version: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            '@id': self.agent_id,
            '@type': ['prov:Agent', self.agent_type],
            'prov:label': self.name,
            'version': self.version,
            'attributes': self.attributes
        }

@dataclass
class ProvenanceAttribution:
    """Attribution relationship between entity and agent."""
    entity_id: str
    agent_id: str
    role: str  # e.g., 'extractor', 'validator', 'annotator'
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            '@type': 'prov:Attribution',
            'prov:entity': self.entity_id,
            'prov:agent': self.agent_id,
            'prov:hadRole': self.role,
            'confidence': self.confidence
        }

@dataclass
class EntityProvenance:
    """Complete provenance record for an extracted entity."""
    entity: ProvenanceEntity
    generation_activity: ProvenanceActivity
    source_document: Dict[str, Any]
    extraction_method: str
    temporal_context: Dict[str, Any]
    confidence_score: float
    attribution_chain: List[ProvenanceAttribution]
    derivation_path: List[str]  # IDs of entities this was derived from
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to PROV-O compliant dictionary."""
        return {
            '@context': {
                'prov': 'http://www.w3.org/ns/prov#',
                'ont': 'http://ontextract.org/ns#'
            },
            'entity': self.entity.to_dict(),
            'generation': self.generation_activity.to_dict(),
            'source': self.source_document,
            'extraction_method': self.extraction_method,
            'temporal_context': self.temporal_context,
            'confidence_score': self.confidence_score,
            'attributions': [attr.to_dict() for attr in self.attribution_chain],
            'derivation_path': self.derivation_path,
            'metadata': self.metadata
        }

class ProvenanceTracker:
    """
    Tracks entity-level provenance following PROV-O standard for
    historical text analysis and linguistic evolution tracking.
    """
    
    def __init__(self):
        """Initialize the provenance tracker."""
        self.entities = {}
        self.activities = {}
        self.agents = {}
        self.attributions = []
        self.derivations = {}
        
        # Register default agents
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default software agents."""
        self.agents['historical_processor'] = ProvenanceAgent(
            agent_id='agent:historical_processor',
            agent_type='prov:SoftwareAgent',
            name='HistoricalDocumentProcessor',
            version='1.0.0',
            attributes={'module': 'shared_services.preprocessing.historical_processor'}
        )
        
        self.agents['temporal_extractor'] = ProvenanceAgent(
            agent_id='agent:temporal_extractor',
            agent_type='prov:SoftwareAgent',
            name='TemporalWordUsageExtractor',
            version='1.0.0',
            attributes={'module': 'shared_services.preprocessing.temporal_extractor'}
        )
        
        self.agents['semantic_tracker'] = ProvenanceAgent(
            agent_id='agent:semantic_tracker',
            agent_type='prov:SoftwareAgent',
            name='SemanticEvolutionTracker',
            version='1.0.0',
            attributes={'module': 'shared_services.preprocessing.semantic_tracker'}
        )
    
    def track_word_extraction(self, word: str, context: Dict[str, Any], 
                             source_doc: Any, method: str = 'automatic') -> EntityProvenance:
        """
        Track provenance for a word extraction.
        
        Args:
            word: The extracted word
            context: Context information (sentence, position, etc.)
            source_doc: Source document object
            method: Extraction method used
            
        Returns:
            EntityProvenance object with full tracking
        """
        # Create entity
        entity_id = self._generate_entity_id('word', word, context)
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type='ont:WordUsage',
            value=word,
            attributes={
                'sentence': context.get('sentence', ''),
                'position': context.get('position', 0),
                'pos_tag': context.get('pos_tag', ''),
                'semantic_unit': context.get('semantic_unit_id', '')
            }
        )
        
        # Create activity
        activity = ProvenanceActivity(
            activity_id=f"activity:{uuid.uuid4()}",
            activity_type='ont:WordExtraction',
            started_at=datetime.now(),
            ended_at=datetime.now(),
            parameters={
                'method': method,
                'context_window': context.get('context_window', 5)
            }
        )
        
        # Build source document metadata
        source_metadata = self._extract_source_metadata(source_doc)
        
        # Build temporal context
        temporal_context = {
            'period': source_doc.temporal_metadata.period_name if hasattr(source_doc, 'temporal_metadata') else None,
            'year': source_doc.temporal_metadata.year if hasattr(source_doc, 'temporal_metadata') else None,
            'confidence': source_doc.temporal_metadata.confidence if hasattr(source_doc, 'temporal_metadata') else 0.0
        }
        
        # Create attribution
        agent_id = 'agent:temporal_extractor' if method == 'automatic' else 'agent:human_annotator'
        attribution = ProvenanceAttribution(
            entity_id=entity_id,
            agent_id=agent_id,
            role='extractor',
            confidence=context.get('confidence', 0.9)
        )
        
        # Build provenance record
        provenance = EntityProvenance(
            entity=entity,
            generation_activity=activity,
            source_document=source_metadata,
            extraction_method=method,
            temporal_context=temporal_context,
            confidence_score=context.get('confidence', 0.9),
            attribution_chain=[attribution],
            derivation_path=[],
            metadata={
                'extraction_date': datetime.now().isoformat(),
                'word_form': context.get('original_form', word)
            }
        )
        
        # Store in tracker
        self.entities[entity_id] = provenance
        self.activities[activity.activity_id] = activity
        self.attributions.append(attribution)
        
        return provenance
    
    def track_collocation(self, words: Tuple[str, ...], frequency: int,
                         source_entities: List[str], source_doc: Any) -> EntityProvenance:
        """
        Track provenance for a collocation pattern.
        
        Args:
            words: Tuple of words in the collocation
            frequency: Occurrence frequency
            source_entities: IDs of word entities this derives from
            source_doc: Source document
            
        Returns:
            EntityProvenance object
        """
        # Create entity
        entity_id = self._generate_entity_id('collocation', ' '.join(words), {'freq': frequency})
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type='ont:Collocation',
            value=' '.join(words),
            attributes={
                'words': list(words),
                'frequency': frequency,
                'type': f"{len(words)}-gram"
            }
        )
        
        # Create activity
        activity = ProvenanceActivity(
            activity_id=f"activity:{uuid.uuid4()}",
            activity_type='ont:CollocationExtraction',
            started_at=datetime.now(),
            ended_at=datetime.now(),
            parameters={
                'min_frequency': 3,
                'window_size': len(words)
            }
        )
        
        # Build provenance
        provenance = EntityProvenance(
            entity=entity,
            generation_activity=activity,
            source_document=self._extract_source_metadata(source_doc),
            extraction_method='statistical_analysis',
            temporal_context=self._extract_temporal_context(source_doc),
            confidence_score=self._calculate_collocation_confidence(frequency),
            attribution_chain=[
                ProvenanceAttribution(
                    entity_id=entity_id,
                    agent_id='agent:temporal_extractor',
                    role='analyzer',
                    confidence=0.95
                )
            ],
            derivation_path=source_entities,
            metadata={
                'mutual_information': 0.0  # Can be calculated elsewhere
            }
        )
        
        # Track derivation
        self._track_derivation(entity_id, source_entities)
        
        # Store
        self.entities[entity_id] = provenance
        self.activities[activity.activity_id] = activity
        
        return provenance
    
    def track_semantic_cluster(self, cluster_data: Dict[str, Any],
                             source_entities: List[str], source_doc: Any) -> EntityProvenance:
        """
        Track provenance for a semantic cluster.
        
        Args:
            cluster_data: Cluster information
            source_entities: IDs of entities in this cluster
            source_doc: Source document
            
        Returns:
            EntityProvenance object
        """
        # Create entity
        entity_id = cluster_data.get('cluster_id', f"cluster:{uuid.uuid4()}")
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type='ont:SemanticCluster',
            value=cluster_data.get('central_meaning', ''),
            attributes={
                'period': cluster_data.get('period', ''),
                'word_forms': cluster_data.get('word_forms', []),
                'semantic_field': cluster_data.get('semantic_field', ''),
                'size': len(source_entities)
            }
        )
        
        # Create activity
        activity = ProvenanceActivity(
            activity_id=f"activity:{uuid.uuid4()}",
            activity_type='ont:SemanticClustering',
            started_at=datetime.now(),
            ended_at=datetime.now(),
            parameters={
                'algorithm': 'DBSCAN',
                'eps': 0.3,
                'min_samples': 2
            }
        )
        
        # Build provenance
        provenance = EntityProvenance(
            entity=entity,
            generation_activity=activity,
            source_document=self._extract_source_metadata(source_doc),
            extraction_method='clustering',
            temporal_context=self._extract_temporal_context(source_doc),
            confidence_score=cluster_data.get('confidence', 0.8),
            attribution_chain=[
                ProvenanceAttribution(
                    entity_id=entity_id,
                    agent_id='agent:semantic_tracker',
                    role='clusterer',
                    confidence=0.85
                )
            ],
            derivation_path=source_entities,
            metadata={
                'cluster_coherence': cluster_data.get('coherence', 0.0)
            }
        )
        
        # Track derivations
        self._track_derivation(entity_id, source_entities)
        
        # Store
        self.entities[entity_id] = provenance
        self.activities[activity.activity_id] = activity
        
        return provenance
    
    def track_semantic_drift(self, word: str, drift_data: Dict[str, Any],
                           source_entities: List[str]) -> EntityProvenance:
        """
        Track provenance for semantic drift detection.
        
        Args:
            word: The word showing drift
            drift_data: Drift analysis data
            source_entities: IDs of entities compared
            
        Returns:
            EntityProvenance object
        """
        # Create entity
        entity_id = f"drift:{word}_{drift_data.get('baseline_period', '')}_{drift_data.get('comparison_period', '')}"
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type='ont:SemanticDrift',
            value=drift_data.get('drift_score', 0.0),
            attributes={
                'word': word,
                'baseline_period': drift_data.get('baseline_period', ''),
                'comparison_period': drift_data.get('comparison_period', ''),
                'meaning_changes': drift_data.get('meaning_changes', [])
            }
        )
        
        # Create activity
        activity = ProvenanceActivity(
            activity_id=f"activity:{uuid.uuid4()}",
            activity_type='ont:DriftAnalysis',
            started_at=datetime.now(),
            ended_at=datetime.now(),
            parameters={
                'method': 'cosine_distance',
                'threshold': 0.3
            }
        )
        
        # Build provenance
        provenance = EntityProvenance(
            entity=entity,
            generation_activity=activity,
            source_document={
                'type': 'comparative_analysis',
                'periods': [drift_data.get('baseline_period', ''), 
                          drift_data.get('comparison_period', '')]
            },
            extraction_method='semantic_comparison',
            temporal_context={
                'baseline_period': drift_data.get('baseline_period', ''),
                'comparison_period': drift_data.get('comparison_period', ''),
                'temporal_distance': drift_data.get('temporal_distance', 0)
            },
            confidence_score=drift_data.get('confidence', 0.75),
            attribution_chain=[
                ProvenanceAttribution(
                    entity_id=entity_id,
                    agent_id='agent:semantic_tracker',
                    role='analyzer',
                    confidence=0.8
                )
            ],
            derivation_path=source_entities,
            metadata={
                'drift_type': drift_data.get('drift_type', 'gradual')
            }
        )
        
        # Track derivations
        self._track_derivation(entity_id, source_entities)
        
        # Store
        self.entities[entity_id] = provenance
        self.activities[activity.activity_id] = activity
        
        return provenance
    
    def get_entity_lineage(self, entity_id: str) -> Dict[str, Any]:
        """
        Get the complete lineage of an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Dictionary with complete lineage information
        """
        if entity_id not in self.entities:
            return {}
        
        provenance = self.entities[entity_id]
        lineage = {
            'entity': provenance.entity.to_dict(),
            'direct_sources': provenance.derivation_path,
            'generation': provenance.generation_activity.to_dict(),
            'attributions': [attr.to_dict() for attr in provenance.attribution_chain]
        }
        
        # Recursively get ancestor lineage
        ancestors = {}
        for source_id in provenance.derivation_path:
            if source_id in self.entities:
                ancestors[source_id] = self.get_entity_lineage(source_id)
        
        lineage['ancestors'] = ancestors
        
        # Get descendants
        descendants = self._find_descendants(entity_id)
        lineage['descendants'] = descendants
        
        return lineage
    
    def export_provenance_graph(self, format: str = 'json-ld') -> str:
        """
        Export the complete provenance graph.
        
        Args:
            format: Export format ('json-ld', 'turtle', 'rdf-xml')
            
        Returns:
            Serialized provenance graph
        """
        if format == 'json-ld':
            graph = {
                '@context': {
                    'prov': 'http://www.w3.org/ns/prov#',
                    'ont': 'http://ontextract.org/ns#',
                    'xsd': 'http://www.w3.org/2001/XMLSchema#'
                },
                '@graph': []
            }
            
            # Add entities
            for entity_id, provenance in self.entities.items():
                graph['@graph'].append(provenance.entity.to_dict())
                graph['@graph'].append(provenance.generation_activity.to_dict())
            
            # Add agents
            for agent_id, agent in self.agents.items():
                graph['@graph'].append(agent.to_dict())
            
            # Add relationships
            for attribution in self.attributions:
                graph['@graph'].append(attribution.to_dict())
            
            # Add derivations
            for derived_id, source_ids in self.derivations.items():
                for source_id in source_ids:
                    graph['@graph'].append({
                        '@type': 'prov:Derivation',
                        'prov:generatedEntity': derived_id,
                        'prov:usedEntity': source_id
                    })
            
            return json.dumps(graph, indent=2)
        
        else:
            # Other formats would require RDF library integration
            raise NotImplementedError(f"Format {format} not yet implemented")
    
    def calculate_quality_metrics(self, entity_id: str) -> Dict[str, float]:
        """
        Calculate quality metrics for an entity based on its provenance.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Dictionary of quality metrics
        """
        if entity_id not in self.entities:
            return {}
        
        provenance = self.entities[entity_id]
        
        # Calculate composite quality score
        metrics = {
            'confidence': provenance.confidence_score,
            'attribution_confidence': self._calculate_attribution_confidence(provenance),
            'source_reliability': self._calculate_source_reliability(provenance),
            'derivation_quality': self._calculate_derivation_quality(entity_id),
            'temporal_precision': self._calculate_temporal_precision(provenance)
        }
        
        # Overall quality score
        metrics['overall_quality'] = sum(metrics.values()) / len(metrics)
        
        return metrics
    
    def _generate_entity_id(self, entity_type: str, value: str, context: Dict[str, Any]) -> str:
        """Generate a unique entity ID."""
        # Create hash from type, value, and context
        hash_input = f"{entity_type}:{value}:{json.dumps(context, sort_keys=True)}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{entity_type}:{hash_value}"
    
    def _extract_source_metadata(self, source_doc: Any) -> Dict[str, Any]:
        """Extract metadata from source document."""
        metadata = {
            'type': 'document',
            'id': getattr(source_doc, 'id', str(uuid.uuid4()))
        }
        
        if hasattr(source_doc, 'filename'):
            metadata['filename'] = source_doc.filename
        if hasattr(source_doc, 'metadata'):
            metadata['original_metadata'] = source_doc.metadata
        if hasattr(source_doc, 'temporal_metadata'):
            metadata['temporal'] = source_doc.temporal_metadata.to_dict()
        
        return metadata
    
    def _extract_temporal_context(self, source_doc: Any) -> Dict[str, Any]:
        """Extract temporal context from document."""
        context = {}
        
        if hasattr(source_doc, 'temporal_metadata'):
            tm = source_doc.temporal_metadata
            context = {
                'period': tm.period_name,
                'year': tm.year,
                'decade': tm.decade,
                'century': tm.century,
                'confidence': tm.confidence
            }
        
        return context
    
    def _calculate_collocation_confidence(self, frequency: int) -> float:
        """Calculate confidence score for collocation based on frequency."""
        # Simple logarithmic scaling
        import math
        if frequency <= 1:
            return 0.3
        elif frequency <= 3:
            return 0.5
        elif frequency <= 10:
            return 0.7
        else:
            return min(0.95, 0.7 + math.log10(frequency) * 0.1)
    
    def _track_derivation(self, derived_id: str, source_ids: List[str]):
        """Track derivation relationship."""
        if derived_id not in self.derivations:
            self.derivations[derived_id] = []
        self.derivations[derived_id].extend(source_ids)
    
    def _find_descendants(self, entity_id: str) -> List[str]:
        """Find all entities derived from this entity."""
        descendants = []
        for derived_id, sources in self.derivations.items():
            if entity_id in sources:
                descendants.append(derived_id)
                # Recursively find descendants of descendants
                descendants.extend(self._find_descendants(derived_id))
        return list(set(descendants))
    
    def _calculate_attribution_confidence(self, provenance: EntityProvenance) -> float:
        """Calculate average attribution confidence."""
        if not provenance.attribution_chain:
            return 0.0
        return sum(attr.confidence for attr in provenance.attribution_chain) / len(provenance.attribution_chain)
    
    def _calculate_source_reliability(self, provenance: EntityProvenance) -> float:
        """Calculate source document reliability score."""
        # Check temporal metadata confidence
        if 'temporal' in provenance.source_document:
            return provenance.source_document['temporal'].get('confidence', 0.5)
        return 0.5
    
    def _calculate_derivation_quality(self, entity_id: str) -> float:
        """Calculate quality based on derivation sources."""
        if entity_id not in self.entities:
            return 0.0
        
        provenance = self.entities[entity_id]
        if not provenance.derivation_path:
            return 1.0  # No derivation means primary source
        
        # Average quality of source entities
        source_qualities = []
        for source_id in provenance.derivation_path:
            if source_id in self.entities:
                source_qualities.append(self.entities[source_id].confidence_score)
        
        return sum(source_qualities) / len(source_qualities) if source_qualities else 0.5
    
    def _calculate_temporal_precision(self, provenance: EntityProvenance) -> float:
        """Calculate temporal precision score."""
        tc = provenance.temporal_context
        
        if not tc:
            return 0.0
        
        # More specific temporal information = higher precision
        precision = 0.0
        if tc.get('year'):
            precision += 0.4
        if tc.get('period'):
            precision += 0.3
        if tc.get('confidence'):
            precision += tc['confidence'] * 0.3
        
        return min(1.0, precision)
