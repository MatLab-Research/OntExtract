from datetime import datetime
import json
from app import db

class ExtractedEntity(db.Model):
    """Model for storing extracted entities from text processing"""
    
    __tablename__ = 'extracted_entities'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Entity information
    entity_text = db.Column(db.String(500), nullable=False)  # The actual text that was extracted
    entity_type = db.Column(db.String(100), nullable=False)  # Type like 'PERSON', 'ORG', 'CONCEPT', etc.
    entity_subtype = db.Column(db.String(100))  # More specific type if available
    
    # Context information
    context_before = db.Column(db.String(200))  # Text before the entity
    context_after = db.Column(db.String(200))   # Text after the entity
    sentence = db.Column(db.Text)  # Full sentence containing the entity
    
    # Position information
    start_position = db.Column(db.Integer)  # Character position in source text
    end_position = db.Column(db.Integer)    # End character position
    paragraph_number = db.Column(db.Integer)  # Which paragraph (if available)
    sentence_number = db.Column(db.Integer)   # Which sentence in paragraph
    
    # Confidence and metadata
    confidence_score = db.Column(db.Float)  # Extraction confidence (0.0 to 1.0)
    extraction_method = db.Column(db.String(50))  # 'spacy', 'langextract', 'llm', etc.
    
    # Properties and attributes
    properties = db.Column(db.Text)  # JSON string of additional properties
    
    # Language information
    language = db.Column(db.String(10))  # Language code of the text
    
    # Normalization
    normalized_form = db.Column(db.String(500))  # Normalized/canonical form of entity
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    processing_job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'), nullable=False, index=True)
    text_segment_id = db.Column(db.Integer, db.ForeignKey('text_segments.id'), index=True)
    
    # Relationships
    ontology_mappings = db.relationship('OntologyMapping', backref='extracted_entity', lazy='dynamic', cascade='all, delete-orphan')

    # Template compatibility properties
    @property
    def text(self):
        """Alias for entity_text for template compatibility"""
        return self.entity_text

    @property
    def confidence(self):
        """Alias for confidence_score for template compatibility"""
        return self.confidence_score

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_properties(self, props_dict):
        """Set entity properties from dictionary"""
        if isinstance(props_dict, dict):
            self.properties = json.dumps(props_dict)
        else:
            self.properties = str(props_dict)
    
    def get_properties(self):
        """Get entity properties as dictionary"""
        if self.properties:
            try:
                return json.loads(self.properties)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_display_context(self, max_length=100):
        """Get a display-friendly context string"""
        context = ""
        if self.context_before:
            context += f"...{self.context_before[-50:]}" if len(self.context_before) > 50 else self.context_before
        
        context += f" [{self.entity_text}] "
        
        if self.context_after:
            context += f"{self.context_after[:50]}..." if len(self.context_after) > 50 else self.context_after
        
        return context.strip()
    
    def is_high_confidence(self, threshold=0.8):
        """Check if entity extraction has high confidence"""
        return self.confidence_score and self.confidence_score >= threshold
    
    def get_position_info(self):
        """Get position information as a readable string"""
        if self.start_position is not None and self.end_position is not None:
            length = self.end_position - self.start_position
            return f"Position {self.start_position}-{self.end_position} ({length} chars)"
        return "Position unknown"
    
    def to_dict(self):
        """Convert extracted entity to dictionary for API responses"""
        return {
            'id': self.id,
            'entity_text': self.entity_text,
            'entity_type': self.entity_type,
            'entity_subtype': self.entity_subtype,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'sentence': self.sentence,
            'start_position': self.start_position,
            'end_position': self.end_position,
            'paragraph_number': self.paragraph_number,
            'sentence_number': self.sentence_number,
            'confidence_score': self.confidence_score,
            'extraction_method': self.extraction_method,
            'language': self.language,
            'normalized_form': self.normalized_form,
            'properties': self.get_properties(),
            'display_context': self.get_display_context(),
            'position_info': self.get_position_info(),
            'is_high_confidence': self.is_high_confidence(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processing_job_id': self.processing_job_id,
            'text_segment_id': self.text_segment_id
        }
    
    @classmethod
    def get_entities_by_type(cls, job_id, entity_type=None):
        """Get entities filtered by type for a specific job"""
        query = cls.query.filter_by(processing_job_id=job_id)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        return query.all()
    
    @classmethod
    def get_unique_entity_types(cls, job_id):
        """Get list of unique entity types for a job"""
        types = db.session.query(cls.entity_type)\
            .filter_by(processing_job_id=job_id)\
            .distinct()\
            .all()
        return [t[0] for t in types if t[0]]
    
    def __repr__(self):
        return f'<ExtractedEntity {self.id}: {self.entity_type} - "{self.entity_text[:30]}...">'
