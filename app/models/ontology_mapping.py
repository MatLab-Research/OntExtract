from datetime import datetime
import json
from app import db

class OntologyMapping(db.Model):
    """Model for mapping extracted entities to ontology concepts"""
    
    __tablename__ = 'ontology_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Ontology information
    ontology_uri = db.Column(db.String(500), nullable=False)  # Full URI of the ontology concept
    concept_label = db.Column(db.String(200), nullable=False)  # Human-readable label
    concept_definition = db.Column(db.Text)  # Definition of the concept
    
    # Hierarchy information
    parent_concepts = db.Column(db.Text)  # JSON array of parent concept URIs
    child_concepts = db.Column(db.Text)   # JSON array of child concept URIs
    related_concepts = db.Column(db.Text)  # JSON array of related concept URIs
    
    # Mapping confidence and provenance
    mapping_confidence = db.Column(db.Float)  # Confidence in this mapping (0.0 to 1.0)
    mapping_method = db.Column(db.String(50))  # How mapping was determined
    mapping_source = db.Column(db.String(100))  # Source ontology name/version
    
    # Semantic properties
    semantic_type = db.Column(db.String(100))  # Semantic type from ontology
    domain = db.Column(db.String(100))  # Domain/field of the concept
    properties = db.Column(db.Text)  # JSON of additional semantic properties
    
    # Validation and verification
    is_verified = db.Column(db.Boolean, default=False)  # Human verified
    verified_by = db.Column(db.String(100))  # Who verified it
    verification_notes = db.Column(db.Text)
    
    # Alternative mappings
    alternative_mappings = db.Column(db.Text)  # JSON array of alternative concept URIs
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
    
    # Foreign keys
    extracted_entity_id = db.Column(db.Integer, db.ForeignKey('extracted_entities.id'), nullable=False, index=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_parent_concepts(self, concepts_list):
        """Set parent concepts from list"""
        if isinstance(concepts_list, list):
            self.parent_concepts = json.dumps(concepts_list)
        else:
            self.parent_concepts = str(concepts_list)
    
    def get_parent_concepts(self):
        """Get parent concepts as list"""
        if self.parent_concepts:
            try:
                return json.loads(self.parent_concepts)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_child_concepts(self, concepts_list):
        """Set child concepts from list"""
        if isinstance(concepts_list, list):
            self.child_concepts = json.dumps(concepts_list)
        else:
            self.child_concepts = str(concepts_list)
    
    def get_child_concepts(self):
        """Get child concepts as list"""
        if self.child_concepts:
            try:
                return json.loads(self.child_concepts)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_related_concepts(self, concepts_list):
        """Set related concepts from list"""
        if isinstance(concepts_list, list):
            self.related_concepts = json.dumps(concepts_list)
        else:
            self.related_concepts = str(concepts_list)
    
    def get_related_concepts(self):
        """Get related concepts as list"""
        if self.related_concepts:
            try:
                return json.loads(self.related_concepts)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_properties(self, props_dict):
        """Set semantic properties from dictionary"""
        if isinstance(props_dict, dict):
            self.properties = json.dumps(props_dict)
        else:
            self.properties = str(props_dict)
    
    def get_properties(self):
        """Get semantic properties as dictionary"""
        if self.properties:
            try:
                return json.loads(self.properties)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_alternative_mappings(self, mappings_list):
        """Set alternative mappings from list"""
        if isinstance(mappings_list, list):
            self.alternative_mappings = json.dumps(mappings_list)
        else:
            self.alternative_mappings = str(mappings_list)
    
    def get_alternative_mappings(self):
        """Get alternative mappings as list"""
        if self.alternative_mappings:
            try:
                return json.loads(self.alternative_mappings)
            except json.JSONDecodeError:
                return []
        return []
    
    def get_short_uri(self):
        """Get shortened version of URI for display"""
        if self.ontology_uri:
            # Try to extract namespace and local name
            if '#' in self.ontology_uri:
                return self.ontology_uri.split('#')[-1]
            elif '/' in self.ontology_uri:
                return self.ontology_uri.split('/')[-1]
        return self.ontology_uri
    
    def is_high_confidence(self, threshold=0.8):
        """Check if mapping has high confidence"""
        return self.mapping_confidence and self.mapping_confidence >= threshold
    
    def verify_mapping(self, verified_by_user, notes=None):
        """Mark mapping as verified"""
        self.is_verified = True
        self.verified_by = verified_by_user
        self.verified_at = datetime.utcnow()
        if notes:
            self.verification_notes = notes
        db.session.commit()
    
    def to_dict(self):
        """Convert ontology mapping to dictionary for API responses"""
        return {
            'id': self.id,
            'ontology_uri': self.ontology_uri,
            'concept_label': self.concept_label,
            'concept_definition': self.concept_definition,
            'parent_concepts': self.get_parent_concepts(),
            'child_concepts': self.get_child_concepts(),
            'related_concepts': self.get_related_concepts(),
            'mapping_confidence': self.mapping_confidence,
            'mapping_method': self.mapping_method,
            'mapping_source': self.mapping_source,
            'semantic_type': self.semantic_type,
            'domain': self.domain,
            'properties': self.get_properties(),
            'is_verified': self.is_verified,
            'verified_by': self.verified_by,
            'verification_notes': self.verification_notes,
            'alternative_mappings': self.get_alternative_mappings(),
            'short_uri': self.get_short_uri(),
            'is_high_confidence': self.is_high_confidence(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'extracted_entity_id': self.extracted_entity_id
        }
    
    @classmethod
    def get_mappings_by_source(cls, entity_id, source=None):
        """Get mappings filtered by source for a specific entity"""
        query = cls.query.filter_by(extracted_entity_id=entity_id)
        if source:
            query = query.filter_by(mapping_source=source)
        return query.all()
    
    @classmethod
    def get_verified_mappings(cls, entity_id):
        """Get only verified mappings for an entity"""
        return cls.query.filter_by(
            extracted_entity_id=entity_id,
            is_verified=True
        ).all()
    
    def __repr__(self):
        return f'<OntologyMapping {self.id}: {self.concept_label} -> {self.get_short_uri()}>'
